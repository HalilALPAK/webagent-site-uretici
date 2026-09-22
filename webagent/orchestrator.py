"""Orkestratör: ajan topluluğunu sırayla ve paralel olarak çalıştırır.

Akış:
  1. aşama: Keşif ─▶ [Tarayıcı ▶ Analist] × N (paralel) ─▶ Stratejist ─▶ Mimar ─▶ Tasarım (DESIGN.md)
            ─▶ İçerik × varlık (paralel) ─▶ Görsel adayları   → kullanıcı görselleri seçer
  2. aşama: Görseller ─▶ İnşa (Laravel) ─▶ QA
"""
from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from .agents.analyst import AnalystAgent
from .agents.architect import ArchitectAgent
from .agents.builder import BuilderAgent
from .agents.content import ContentAgent
from .agents.crawler import CrawlerAgent, crawl_to_dict
from .agents.designer import DesignerAgent
from .agents.images import ImageAgent
from .agents.legacy import LegacyAgent
from .agents.laravel_builder import LaravelBuilderAgent
from .agents.qa import QAAgent
from .agents.reporter import ReportAgent, facts
from .agents.reviser import ReviserAgent
from .agents.scout import ScoutAgent
from .agents.strategist import StrategistAgent, feature_matrix
from .config import JOBS_DIR, STACK
from .jobs import SECRETS, Job
from .llm import LLM, make_llm
from .schemas import Competitor, LegacyInfo, Site, SiteAnalysis

ORCH = "Orkestratör"


class Orchestrator:
    def __init__(self, job: Job, llm: LLM | None = None, workers: int = 4):
        self.job = job
        self.llm = llm
        self.workers = workers

    # ============================================================ 1. aşama: analiz → içerik → görsel adayları
    def run_analysis(self) -> bool:
        """Rakip analizinden içerik üretimine kadar çalışır, görsel seçimini bekler. Başarıda True."""
        job = self.job
        job.status = "running"
        job.log(ORCH, f"Görev başladı: '{job.request.brand_name or job.request.sector}' için site üretimi.")
        try:
            self.llm = self.llm or make_llm(job.request.ai_backend)

            # 0) Kullanıcının mevcut sitesi (varsa): gerçek bilgiler ve görseller devralınır
            legacy, own_images = None, []
            if job.request.own_site.strip():
                job.set_stage("Mevcut siteniz")
                legacy, own_images = LegacyAgent(job, self.llm).run(job.request.own_site.strip())
                if legacy:
                    job.put("legacy", legacy.model_dump())
                    job.put("legacy_images", own_images)
                    req = job.request  # boş bırakılan iletişim bilgilerini eski siteden tamamla
                    req.contact_phone = req.contact_phone or legacy.phone
                    req.contact_email = req.contact_email or legacy.email
                    req.address = req.address or legacy.address

            # 1) Keşif
            job.set_stage("Rakip keşfi")
            competitors = ScoutAgent(job, self.llm).run()
            if not competitors:
                raise RuntimeError("Hiç rakip bulunamadı; lütfen rakip URL'si girin.")
            job.put("competitors", [c.model_dump() for c in competitors])

            # 2) Tarama + analiz (her rakip paralel)
            job.set_stage("Rakip taraması ve analizi")
            with ThreadPoolExecutor(self.workers) as pool:
                results = list(pool.map(self._crawl_and_analyze, competitors))
            analyses = [a for a in results if a is not None]
            if not analyses:
                raise RuntimeError("Hiçbir rakip site taranamadı/analiz edilemedi.")
            job.put("analyses", [a.model_dump() for a in analyses])

            # 3) Strateji
            job.set_stage("Strateji")
            strategist = StrategistAgent(job, self.llm)
            try:
                strategist.normalize(analyses)
            except Exception as e:  # normalizasyon opsiyonel; başarısızsa ham anahtarlarla devam
                strategist.log(f"Modül normalizasyonu atlandı: {e}", "warn")
            matrix = feature_matrix(analyses)
            job.put("feature_matrix", matrix)
            strategy = strategist.run(analyses, matrix)
            job.put("strategy", strategy.model_dump())

            # 4) Mimari + tasarım
            job.set_stage("Mimari tasarım")
            legacy_text = LegacyAgent.as_prompt(legacy)
            spec = ArchitectAgent(job, self.llm).run(strategy, analyses, legacy_text)
            job.set_stage("Tasarım")
            site = DesignerAgent(job, self.llm).run(spec, strategy)
            job.put("spec", site.model_dump())

            # 5) İçerik (her varlık paralel)
            job.set_stage("İçerik üretimi")
            content = ContentAgent(job, self.llm)
            seed: dict[str, list[dict]] = {}
            with ThreadPoolExecutor(self.workers) as pool:
                futures = {e.name: pool.submit(self._safe_seed, content, site, e, legacy_text)
                           for e in site.entities}
                for name, fut in futures.items():
                    seed[name] = fut.result()
            job.put("seed", seed)

            # 6) Görsel adayları (kullanıcının kendi görselleri önce önerilir)
            job.set_stage("Görsel önerileri")
            images = ImageAgent(job, None).find_candidates(site, seed, own_images=own_images)
            job.put("images", images)

            # 7) Plan raporu → kullanıcı okur, sonra görsellere geçer
            job.set_stage("Plan raporu")
            db = {**job.request.db}
            data = facts(site, seed, images, db, legacy)
            report = ReportAgent(job, self.llm).run(site, strategy, data, legacy)
            job.put("report", {"report": report.model_dump(), "facts": data})
            job.status = "awaiting_review"
            job.set_stage("Plan onayı")
            job.log(ORCH, "Plan raporu hazır. Okuyup onayladığınızda görsel seçimine geçilecek.", "ok")
            return True
        except Exception as e:
            self._fail(e)
            return False

    # ============================================================ 2. aşama: görseller → inşa → QA
    def run_build(self) -> None:
        job = self.job
        job.status = "building"
        job.error = ""
        try:
            site = Site(**job.artifacts["spec"])
            seed = job.artifacts["seed"]
            job.set_stage("Görseller")
            files, credits = ImageAgent(job, None).materialize(job.artifacts["images"], JOBS_DIR / job.id / "images")

            revision = job.artifacts.get("revision") or {}
            if revision.get("pending"):
                job.set_stage("Güncelleme")
                target = Path(job.output_dir)
                diff = LaravelBuilderAgent(job, None).revise(site, target, seed, files, credits)
                job.put("revision", {**revision, "pending": False, "diff": diff})
                job.set_stage("Test")
                qa = QAAgent(job, None).run(target)
                job.put("qa", qa.model_dump())
                job.status = "done"
                job.set_stage("Tamamlandı")
                job.log(ORCH, "Site güncellendi.", "ok" if qa.passed else "warn")
                return

            job.set_stage("İnşa")
            db = {**job.request.db, **SECRETS.get(job.id, {})}
            if STACK == "laravel":
                out = LaravelBuilderAgent(job, None).run(site, seed, files, credits, db)
            else:
                out = BuilderAgent(job, None).run(site, seed)
            job.output_dir = str(out)

            job.set_stage("Test")
            qa = QAAgent(job, None).run(out)
            job.put("qa", qa.model_dump())

            job.status = "done"
            job.set_stage("Tamamlandı")
            job.log(ORCH, "Site hazır. 'Siteyi başlat' ile açabilirsiniz.", "ok" if qa.passed else "warn")
        except Exception as e:
            self._fail(e)

    # ============================================================ revizyon: "şunu değiştir"
    def run_revision(self, instruction: str) -> None:
        """Yayındaki siteyi kullanıcının isteğine göre günceller (veri korunur)."""
        job = self.job
        job.status = "running"
        job.error = ""
        job.set_stage("Revizyon")
        job.log(ORCH, f"Değişiklik isteği: {instruction}")
        try:
            self.llm = self.llm or make_llm(job.request.ai_backend)
            target = Path(job.output_dir)
            current = json.loads((target / "site.json").read_text(encoding="utf-8"))
            site, summary = ReviserAgent(job, self.llm).run(current, instruction)

            # yalnızca yeni eklenen tablolar için içerik üret
            old_names = {e["name"] for e in current["entities"]}
            new_entities = [e for e in site.entities if e.name not in old_names]
            seed_new: dict[str, list[dict]] = {}
            if new_entities:
                job.set_stage("Yeni içerik")
                content = ContentAgent(job, self.llm)
                with ThreadPoolExecutor(self.workers) as pool:
                    futures = {e.name: pool.submit(self._safe_seed, content, site, e) for e in new_entities}
                    seed_new = {name: fut.result() for name, fut in futures.items()}

            job.put("spec", site.model_dump())
            job.put("seed", seed_new)
            job.put("revision", {"instruction": instruction, "summary": summary, "pending": True})

            # yeni görsel yuvaları varsa kullanıcı yine seçsin
            hero_missing = not current.get("theme", {}).get("hero_image") and site.theme.hero_variant != "centered"
            images = ImageAgent(job, None).find_candidates(site, seed_new, include_hero=hero_missing)
            if images["groups"]:
                job.put("images", images)
                job.status = "awaiting_images"
                job.set_stage("Görsel seçimi")
                job.log(ORCH, "Yeni görseller için seçim bekleniyor.", "ok")
            else:
                job.put("images", {"groups": [], "choices": {}})
                self.run_build()
        except Exception as e:
            self._fail(e)

    def run(self) -> None:
        """Komut satırı/testler için: analiz + önerilen görsellerle doğrudan inşa."""
        if self.run_analysis():
            self.run_build()

    def _fail(self, e: Exception) -> None:
        job = self.job
        job.status = "failed"
        job.error = f"{type(e).__name__}: {e}"
        if "authentication" in str(e).lower():
            job.error = "Claude API kimlik bilgisi bulunamadı. API anahtarını kontrol edin ya da Claude Code'u seçin."
        job.log(ORCH, job.error, "error")
        job.put("traceback", traceback.format_exc())

    # ------------------------------------------------------------ alt görevler
    def _crawl_and_analyze(self, competitor: Competitor) -> SiteAnalysis | None:
        crawl = CrawlerAgent(self.job, None).run(competitor.url)
        with self.job._lock:
            self.job.artifacts.setdefault("crawls", []).append(crawl_to_dict(crawl))
        if not crawl.ok:
            return None
        try:
            return AnalystAgent(self.job, self.llm).run(crawl, competitor.name)
        except Exception as e:
            self.job.log(AnalystAgent.name, f"{competitor.url} analiz edilemedi: {e}", "warn")
            return None

    def _safe_seed(self, agent: ContentAgent, spec, entity, legacy: str = "") -> list[dict]:
        try:
            return agent.run(spec, entity, legacy=legacy)
        except Exception as e:
            agent.log(f"{entity.name} için içerik üretilemedi: {e}", "warn")
            return []


def start_in_background(job: Job, phase: str = "analysis", instruction: str = "") -> threading.Thread:
    """phase: analysis (görsel seçimine kadar) | build (seçimlerden sonra) | revision | all."""
    orch = Orchestrator(job)
    target = {"analysis": orch.run_analysis, "build": orch.run_build, "all": orch.run,
              "revision": lambda: orch.run_revision(instruction)}[phase]
    t = threading.Thread(target=target, daemon=True, name=f"job-{job.id}-{phase}")
    t.start()
    return t
