"""QA Ajanı: üretilen siteyi izole bir süreçte ayağa kaldırıp tüm rotaları test eder."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from ..config import php_bin
from ..schemas import QAResult
from .base import Agent


class QAAgent(Agent):
    name = "QA Ajanı"
    role = "Üretilen sitenin public sayfalarını, API'sini ve admin panelini test etmek."

    def run(self, site_dir: Path) -> QAResult:
        result = self._laravel(site_dir) if (site_dir / "artisan").exists() else self._python(site_dir)
        for err in result.errors[:15]:
            self.log(err[:600], "error")
        self.log(
            f"{len(result.checks)} kontrol geçti, {len(result.errors)} hata.",
            "ok" if result.passed else "error",
        )
        return result

    def _laravel(self, site_dir: Path) -> QAResult:
        """PHPUnit (tests/Feature/SiteSmokeTest.php) çalıştırır, JUnit raporunu okur."""
        report = site_dir / "storage" / "qa-junit.xml"
        report.unlink(missing_ok=True)
        proc = subprocess.run(
            [php_bin(), "artisan", "test", "--log-junit", str(report)],
            cwd=site_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        if not report.exists():
            return QAResult(passed=False, errors=[(proc.stdout + proc.stderr)[-3000:] or "Test raporu oluşmadı"])

        checks, errors = [], []
        for case in ET.parse(report).getroot().iter("testcase"):
            name = case.get("name", "")
            m = re.search(r'with data set "(.+?)"', name)
            label = f"{case.get('name', '').split(' with')[0].removeprefix('test_').replace('_', ' ')}"
            label += f" [{m.group(1)}]" if m else ""
            problem = case.find("failure") if case.find("failure") is not None else case.find("error")
            if problem is None:
                checks.append(label)
            else:
                errors.append(f"{label}: {(problem.text or problem.get('message', ''))[:500]}")
        return QAResult(passed=not errors and proc.returncode == 0, checks=checks, errors=errors)

    @staticmethod
    def _python(site_dir: Path) -> QAResult:
        proc = subprocess.run(
            [sys.executable, "tests/smoke_test.py", "--json"],
            cwd=site_dir, capture_output=True, text=True, timeout=300, encoding="utf-8",
        )
        try:
            return QAResult(**json.loads(proc.stdout.strip().splitlines()[-1]))
        except (json.JSONDecodeError, IndexError, TypeError):
            return QAResult(passed=False, errors=[proc.stderr[-3000:] or proc.stdout[-3000:] or "Test çıktısı okunamadı"])
