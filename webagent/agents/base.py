from __future__ import annotations

from ..jobs import Job
from ..llm import LLM


class Agent:
    """Tüm ajanların ortak temeli: isim, rol, LLM ve ortak kara tahta (job)."""

    name = "Agent"
    role = ""

    def __init__(self, job: Job, llm: LLM | None):
        self.job = job
        self.llm = llm

    def log(self, message: str, level: str = "info") -> None:
        self.job.log(self.name, message, level)

    @property
    def lang(self) -> str:
        return self.job.request.language

    def system_prompt(self, extra: str = "") -> str:
        return (
            f"Sen bir web ajansının çoklu ajan ekibinde '{self.name}' rolündesin: {self.role}\n"
            f"Hedef sektör: {self.job.request.sector}. Hedef pazar: {self.job.request.location}. "
            f"Üretilen tüm kullanıcıya dönük metinlerin dili: {self.lang}.\n"
            "Rakip sitelerden metin, marka adı veya görsel kopyalama; yalnızca modül/özellik "
            "yapısından ilham al ve özgün içerik üret.\n" + extra
        )
