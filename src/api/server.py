"""Servidor FastAPI — backend do dashboard + integração com extensão Chrome."""

from __future__ import annotations

import csv
import io
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..claude_agent.classifier import classify_company
from ..claude_agent.client import GeminiClient
from ..claude_agent.personalize import generate_trigger
from ..claude_agent.scorer import score_lead
from ..db.store import Store
from ..enrichers.brasil_api import enrich_with_cnpj
from ..integrations.intercom import push_lead_to_intercom
from ..jobs.monitor import run_monitor
from ..jobs.rescore import run_rescore
from ..jobs.scheduler import Scheduler
from ..outbound.orchestrator import generate_and_store
from ..output.csv_writer import write_leads_csv
from ..pipeline import run_pipeline
from ..scrapers.linkedin import parse_linkedin_payload

load_dotenv()
logger = logging.getLogger(__name__)

API_TOKEN = os.environ.get("API_TOKEN", "change-me-in-production")
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8765"))

STATIC_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "static"

app = FastAPI(
    title="Solve Scraper API",
    description="Backend do dashboard e extensão Chrome de prospecção da Solvefy.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "http://localhost:*", "http://127.0.0.1:*"],
    allow_origin_regex=r"^(chrome-extension://.*|https?://(localhost|127\.0\.0\.1)(:\d+)?)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== STATE ======
JOBS: dict[str, dict[str, Any]] = {}
STORE = Store()
SCHED = Scheduler()


# ====== AUTH ======
def _auth(token: str | None) -> None:
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")


# ====== MODELS ======
class LinkedInPayload(BaseModel):
    source: str
    url: str
    items: list[dict[str, Any]]


class ScrapeRequest(BaseModel):
    vertical: str = Field(...)
    limit: Optional[int] = None
    enrich_email: bool = False


# ====== DASHBOARD ======
if STATIC_DIR.exists():
    app.mount("/dashboard", StaticFiles(directory=str(STATIC_DIR), html=True), name="dashboard")


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Solve Scraper API",
        "version": "0.2.0",
        "jobs_ativos": len([j for j in JOBS.values() if j["status"] == "rodando"]),
        "dashboard": "/dashboard/",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ====== STATS / LEADS / EVENTS (dashboard) ======
@app.get("/stats")
def stats(x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    return STORE.stats()


@app.get("/db/leads")
def db_leads(
    vertical: str | None = Query(default=None),
    min_score: int = Query(default=0),
    limit: int = Query(default=200, le=2000),
    x_api_token: str | None = Header(default=None),
):
    _auth(x_api_token)
    leads = STORE.all_leads(vertical=vertical, min_score=min_score, limit=limit)
    return {"leads": leads, "count": len(leads)}


@app.get("/db/leads/{lead_id}")
def db_lead_detail(lead_id: int, x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    with STORE.conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Lead não encontrado")
        outbound = c.execute(
            "SELECT * FROM outbound_messages WHERE lead_id=? ORDER BY canal", (lead_id,)
        ).fetchall()
    return {"lead": dict(row), "outbound": [dict(o) for o in outbound]}


@app.get("/db/export.csv")
def db_export_csv(
    vertical: str | None = Query(default=None),
    min_score: int = Query(default=0),
    x_api_token: str | None = Header(default=None),
):
    _auth(x_api_token)
    leads = STORE.all_leads(vertical=vertical, min_score=min_score, limit=10000)
    if not leads:
        raise HTTPException(404, "Sem leads para exportar")

    buf = io.StringIO()
    cols = [
        "vertical", "empresa", "cnpj", "razao_social", "site", "decisor_nome",
        "decisor_cargo", "decisor_linkedin", "email_provavel", "porte_estimado",
        "score_icp", "recomendacao", "gatilho_personalizado", "observacoes",
        "fonte", "criado_em", "atualizado_em",
    ]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(leads)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads_{vertical or 'all'}.csv"},
    )


@app.get("/events")
def events(limit: int = Query(default=50), x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    return {"events": STORE.recent_events(limit=limit)}


# ====== LINKEDIN INGEST ======
@app.post("/linkedin/ingest")
def ingest_linkedin(payload: LinkedInPayload, x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    leads_raw = parse_linkedin_payload(payload.model_dump())
    client = GeminiClient()
    processed = []

    for lead in leads_raw:
        try:
            cls = classify_company(client, lead)
            lead.update(
                {
                    "vertical": cls.get("vertical"),
                    "segmento": cls.get("segmento"),
                    "porte_estimado": cls.get("porte_estimado"),
                }
            )
            sc = score_lead(client, lead)
            lead["score_icp"] = sc.get("score")
            lead["recomendacao"] = sc.get("recomendacao")
            if (lead.get("score_icp") or 0) >= 50:
                lead["gatilho_personalizado"] = generate_trigger(client, lead)
            if lead.get("cnpj"):
                lead = enrich_with_cnpj(lead)
            lead["data_coleta"] = datetime.now().isoformat(timespec="seconds")
            STORE.upsert_lead(lead)
            STORE.log_event("novo_lead", {"empresa": lead.get("empresa"), "fonte": "linkedin"})
            processed.append(lead)
        except Exception as e:
            logger.exception("Falha em lead %s: %s", lead.get("empresa"), e)

    if processed:
        path = write_leads_csv(processed, vertical_tag="linkedin")
        return {
            "ok": True,
            "leads_processados": len(processed),
            "csv": str(path),
            "leads": processed,
        }
    return {"ok": True, "leads_processados": 0, "leads": []}


# ====== SCRAPE JOB ======
@app.post("/scrape")
def trigger_scrape(req: ScrapeRequest, x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    job_id = str(uuid4())
    JOBS[job_id] = {
        "id": job_id,
        "status": "rodando",
        "vertical": req.vertical,
        "criado_em": datetime.now().isoformat(),
        "concluido_em": None,
        "leads": 0,
        "erro": None,
        "csv_path": None,
    }

    def _runner():
        try:
            leads = run_pipeline(
                vertical=req.vertical,
                limit=req.limit,
                enrich_email=req.enrich_email,
            )
            # Persiste no DB
            for lead in leads:
                STORE.upsert_lead(lead)
            STORE.log_event("scrape_completo", {"vertical": req.vertical, "leads": len(leads)})
            path = write_leads_csv(leads, vertical_tag=req.vertical) if leads else None
            JOBS[job_id].update(
                {
                    "status": "concluido",
                    "concluido_em": datetime.now().isoformat(),
                    "leads": len(leads),
                    "csv_path": str(path) if path else None,
                }
            )
        except Exception as e:
            logger.exception("Job %s falhou", job_id)
            JOBS[job_id].update(
                {
                    "status": "erro",
                    "erro": str(e),
                    "concluido_em": datetime.now().isoformat(),
                }
            )

    threading.Thread(target=_runner, daemon=True).start()
    return {"job_id": job_id, "status": "rodando"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str, x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    if job_id not in JOBS:
        raise HTTPException(404, "Job não encontrado")
    return JOBS[job_id]


@app.get("/jobs")
def list_jobs(x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    return list(JOBS.values())


@app.get("/outputs")
def list_outputs(x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    output_dir = Path("data/output")
    if not output_dir.exists():
        return []
    files = sorted(
        [
            {
                "arquivo": f.name,
                "caminho": str(f),
                "tamanho": f.stat().st_size,
                "modificado": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
            for f in output_dir.glob("*.csv")
        ],
        key=lambda x: x["modificado"],
        reverse=True,
    )
    return files


# ====== MONITOR ======
@app.post("/monitor/{vertical}")
def monitor(vertical: str, x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    try:
        return run_monitor(vertical, store=STORE)
    except Exception as e:
        logger.exception("Monitor falhou: %s", e)
        raise HTTPException(500, str(e))


# ====== RE-SCORE ======
@app.post("/rescore")
def rescore(
    days_since: int = Query(default=7),
    max_score: int = Query(default=70),
    x_api_token: str | None = Header(default=None),
):
    _auth(x_api_token)
    try:
        return run_rescore(days_since=days_since, max_score=max_score, store=STORE)
    except Exception as e:
        logger.exception("Rescore falhou: %s", e)
        raise HTTPException(500, str(e))


# ====== SCHEDULER ======
@app.post("/scheduler/start")
def sched_start(x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    SCHED.start()
    return SCHED.status()


@app.post("/scheduler/stop")
def sched_stop(x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    SCHED.stop()
    return SCHED.status()


@app.get("/scheduler/status")
def sched_status(x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    return SCHED.status()


# ====== OUTBOUND ======
@app.post("/outbound/generate/{lead_id}")
def outbound_generate(lead_id: int, x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    with STORE.conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Lead não encontrado")
    lead = dict(row)
    try:
        messages = generate_and_store(lead_id, lead, store=STORE)
        return {"ok": True, "empresa": lead.get("empresa"), "messages": messages}
    except Exception as e:
        logger.exception("Geração de outbound falhou: %s", e)
        raise HTTPException(500, str(e))


# ====== INTERCOM ======
@app.post("/intercom/push/{lead_id}")
def intercom_push(lead_id: int, x_api_token: str | None = Header(default=None)):
    _auth(x_api_token)
    with STORE.conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Lead não encontrado")
    result = push_lead_to_intercom(dict(row))
    STORE.log_event("intercom_push", {"lead_id": lead_id, "result": result})
    return result


@app.post("/intercom/push_batch")
def intercom_push_batch(
    min_score: int = Query(default=70),
    x_api_token: str | None = Header(default=None),
):
    _auth(x_api_token)
    leads = STORE.all_leads(min_score=min_score, limit=500)
    from ..integrations.intercom import push_batch
    result = push_batch(leads)
    STORE.log_event("intercom_batch", result)
    return result


def start():
    """Entry point: python -m src.api.server"""
    import uvicorn

    uvicorn.run(
        "src.api.server:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    start()
