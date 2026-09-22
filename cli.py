"""Komut satırından çalıştırma.

Örnek:
  python cli.py "diş kliniği" --location İstanbul --urls https://rakip1.com https://rakip2.com
"""
import argparse
import sys
from pathlib import Path

from webagent.jobs import JobRequest, new_job
from webagent.orchestrator import Orchestrator


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Rakip analizi yapıp benzer bir site üretir.")
    p.add_argument("sector")
    p.add_argument("--location", default="Türkiye")
    p.add_argument("--language", default="tr")
    p.add_argument("--urls", nargs="*", default=[], help="Bilinen rakip URL'leri")
    p.add_argument("--max", type=int, default=5, help="Rakip sayısı")
    p.add_argument("--brand", default="")
    p.add_argument("--notes", default="")
    a = p.parse_args()

    job = new_job(JobRequest(sector=a.sector, language=a.language, location=a.location,
                             competitor_urls=a.urls, max_competitors=a.max, brand_name=a.brand, notes=a.notes))

    original_log = job.log

    def log_and_print(agent, message, level="info"):
        original_log(agent, message, level)
        print(f"[{level:5}] {agent}: {message}", flush=True)

    job.log = log_and_print
    Orchestrator(job).run()

    if job.status == "done":
        creds = job.artifacts.get("admin_credentials", {})
        print(f"\nSite hazır: {job.output_dir}")
        if (Path(job.output_dir) / "artisan").exists():
            print(f"Başlatmak için:  \"{Path(job.output_dir) / 'run.bat'}\"   (ya da platformda ▶ Siteyi Başlat)")
        else:
            print(f"Başlatmak için:  cd \"{job.output_dir}\" && python -m uvicorn app:app --port 8100")
        print(f"Site: http://127.0.0.1:8100   Admin: http://127.0.0.1:8100/admin  ({creds.get('user')} / {creds.get('password')})")
    else:
        print(f"\nBaşarısız: {job.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
