"""Claude sarmalayıcıları: yapılandırılmış çıktı ve web araması.

İki arka uç var: Claude API (anahtar ile) ve yerel Claude Code oturumu (`claude -p`).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from .config import MODEL

T = TypeVar("T", bound=BaseModel)

# Opus 5 güvenlik sınıflandırıcıları bir isteği reddederse sunucu tarafında
# Anthropic'in önerdiği modele otomatik geçilir.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    pass


class SearchHit(BaseModel):
    url: str
    title: str


class LLM:
    def __init__(self, model: str = MODEL):
        self.model = model
        self.client = anthropic.Anthropic(max_retries=4)

    def structured(
        self,
        system: str,
        prompt: str,
        output: type[T],
        effort: str = "medium",
        max_tokens: int = 16000,
    ) -> T:
        """Pydantic şemasına uyan, doğrulanmış bir nesne döndürür."""
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            output_format=output,
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise LLMError("Model isteği reddetti.")
        if response.stop_reason == "max_tokens":
            raise LLMError("Yanıt max_tokens sınırında kesildi.")
        if response.parsed_output is None:
            raise LLMError("Yapılandırılmış çıktı ayrıştırılamadı.")
        return response.parsed_output

    def web_search(self, prompt: str, max_uses: int = 6) -> tuple[str, list[SearchHit]]:
        """Sunucu taraflı web_search aracıyla araştırma yapar.

        Modelin metin özetini ve bulunan tüm sonuç URL'lerini döndürür.
        """
        tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}]
        messages: list[dict] = [{"role": "user", "content": prompt}]
        hits: dict[str, SearchHit] = {}
        text_parts: list[str] = []

        for _ in range(5):  # pause_turn devamları için üst sınır
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                messages=messages,
                tools=tools,
                thinking={"type": "adaptive"},
                output_config={"effort": "medium"},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "web_search_tool_result":
                    # Başarıda content bir liste, hatada tek bir hata nesnesidir.
                    if isinstance(block.content, list):
                        for r in block.content:
                            if getattr(r, "type", "") == "web_search_result":
                                hits.setdefault(r.url, SearchHit(url=r.url, title=r.title or ""))
            if response.stop_reason == "refusal":
                raise LLMError("Model web araması isteğini reddetti.")
            if response.stop_reason != "pause_turn":
                break
            messages = [messages[0], {"role": "assistant", "content": response.content}]

        return "\n".join(text_parts), list(hits.values())


# ====================================================================== Claude Code arka ucu

def find_claude_cli() -> str | None:
    """PATH'teki `claude` ya da VS Code eklentisiyle gelen claude.exe."""
    env = os.environ.get("CLAUDE_CLI_PATH")
    if env and Path(env).exists():
        return env
    found = shutil.which("claude")
    if found:
        return found
    ext_dir = Path.home() / ".vscode" / "extensions"
    candidates = sorted(ext_dir.glob("anthropic.claude-code-*/resources/native-binary/claude*"), reverse=True)
    return str(candidates[0]) if candidates else None


class _SearchResults(BaseModel):
    summary: str
    results: list[SearchHit]


class ClaudeCodeLLM:
    """API anahtarı yerine bilgisayardaki Claude Code oturumunu kullanır (`claude -p`)."""

    def __init__(self, cli: str, model: str = MODEL):
        self.cli = cli
        self.model = model

    def _run(self, system: str, prompt: str, schema: dict, tools: str = "", effort: str = "medium") -> dict:
        cmd = [
            self.cli, "-p", "--output-format", "json", "--model", self.model, "--effort", effort,
            "--system-prompt", system, "--json-schema", json.dumps(schema, ensure_ascii=False),
            "--tools", tools, "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
        ]
        if tools:
            cmd += ["--allowedTools", tools]
        # Proje dosyalarını (CLAUDE.md vb.) yüklememesi için geçici klasörde çalıştır; prompt stdin'den.
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
            cwd=tempfile.gettempdir(), timeout=900, creationflags=0x08000000 if os.name == "nt" else 0,
        )
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise LLMError(f"Claude Code çıktısı okunamadı: {(proc.stderr or proc.stdout)[-800:]}")
        if data.get("is_error") or data.get("structured_output") is None:
            raise LLMError(f"Claude Code hatası: {str(data.get('result') or data.get('api_error_status'))[:800]}")
        return data["structured_output"]

    def structured(self, system: str, prompt: str, output: type[T], effort: str = "medium",
                   max_tokens: int = 16000) -> T:
        data = self._run(system, prompt, output.model_json_schema(), effort=effort)
        return output.model_validate(data)

    def web_search(self, prompt: str, max_uses: int = 6) -> tuple[str, list[SearchHit]]:
        res = self._run(
            "Web araştırmacısısın. WebSearch aracını kullan; bulduğun sonuçların gerçek URL'lerini listele.",
            prompt, _SearchResults.model_json_schema(), tools="WebSearch",
        )
        parsed = _SearchResults.model_validate(res)
        return parsed.summary, parsed.results


def make_llm(backend: str = "auto") -> LLM | ClaudeCodeLLM:
    """backend: api | claude-code | auto. auto: API anahtarı varsa API, yoksa Claude Code oturumu."""
    backend = backend if backend != "auto" else os.environ.get("WEBAGENT_BACKEND", "auto")
    if backend == "api" or (backend == "auto" and os.environ.get("ANTHROPIC_API_KEY")):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("API seçildi ama ANTHROPIC_API_KEY girilmedi.")
        return LLM()
    cli = find_claude_cli()
    if not cli:
        raise LLMError("Claude Code (claude) bulunamadı. Claude Code'u kurup giriş yapın ya da API anahtarı girin.")
    return ClaudeCodeLLM(cli)
