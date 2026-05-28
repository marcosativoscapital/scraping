"""Agendador de jobs recorrentes (monitor + rescore)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from threading import Thread

from .monitor import run_monitor
from .rescore import run_rescore

logger = logging.getLogger(__name__)


class Scheduler:
    """Scheduler simples baseado em loop com intervalos."""

    def __init__(self):
        self._stop = False
        self._thread: Thread | None = None
        self._last_monitor: dict[str, datetime] = {}
        self._last_rescore: datetime | None = None

    def start(
        self,
        monitor_interval_hours: int = 6,
        rescore_interval_hours: int = 24,
        verticais_monitor: list[str] | None = None,
    ) -> None:
        """Inicia o scheduler em thread separada."""
        verticais_monitor = verticais_monitor or ["betting", "pagamentos"]
        self._stop = False

        def _loop():
            while not self._stop:
                try:
                    now = datetime.now()
                    # Monitor por vertical
                    for v in verticais_monitor:
                        last = self._last_monitor.get(v)
                        if not last or (now - last) >= timedelta(hours=monitor_interval_hours):
                            logger.info("Scheduler: rodando monitor %s", v)
                            try:
                                run_monitor(v)
                            except Exception as e:
                                logger.exception("Monitor %s falhou: %s", v, e)
                            self._last_monitor[v] = now
                    # Re-score
                    if not self._last_rescore or (now - self._last_rescore) >= timedelta(hours=rescore_interval_hours):
                        logger.info("Scheduler: rodando rescore")
                        try:
                            run_rescore()
                        except Exception as e:
                            logger.exception("Rescore falhou: %s", e)
                        self._last_rescore = now
                except Exception as e:
                    logger.exception("Scheduler tick falhou: %s", e)

                # Tick a cada 60s
                for _ in range(60):
                    if self._stop:
                        break
                    time.sleep(1)

        self._thread = Thread(target=_loop, daemon=True, name="solve-scheduler")
        self._thread.start()
        logger.info("Scheduler iniciado.")

    def stop(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler parado.")

    def status(self) -> dict:
        return {
            "ativo": self._thread is not None and self._thread.is_alive(),
            "last_monitor": {k: v.isoformat() for k, v in self._last_monitor.items()},
            "last_rescore": self._last_rescore.isoformat() if self._last_rescore else None,
        }
