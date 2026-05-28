"""Scraper base — Playwright + retries + delays + persistência de raw HTML."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base de todos os scrapers."""

    vertical: str = ""
    nome: str = ""
    fonte_url: str = ""

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0",
        delay_ms: int = 2000,
        max_retries: int = 3,
        headless: bool = True,
        raw_dir: Path = Path("data/raw"),
    ):
        self.user_agent = user_agent
        self.delay_ms = delay_ms
        self.max_retries = max_retries
        self.headless = headless
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_html(self, url: str, wait_for: str | None = None) -> str:
        """Baixa HTML renderizado via Playwright."""
        for attempt in range(self.max_retries):
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=self.headless)
                    context = browser.new_context(user_agent=self.user_agent)
                    page = context.new_page()
                    page.goto(url, timeout=30000)
                    if wait_for:
                        page.wait_for_selector(wait_for, timeout=15000)
                    else:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    html = page.content()
                    browser.close()
                    return html
            except Exception as e:
                logger.warning("Tentativa %d falhou para %s: %s", attempt + 1, url, e)
                time.sleep(self.delay_ms / 1000 * (attempt + 1))
        raise RuntimeError(f"Não consegui baixar {url} após {self.max_retries} tentativas")

    def save_raw(self, content: str, filename: str) -> Path:
        """Salva HTML/conteúdo bruto para auditoria."""
        path = self.raw_dir / f"{self.vertical}_{filename}"
        path.write_text(content, encoding="utf-8")
        return path

    @abstractmethod
    def scrape(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Implementação específica de cada scraper. Retorna lista de empresas raw."""
        ...
