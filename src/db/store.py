"""Persistência local em SQLite.

Armazena snapshots de listas (para diff) e leads processados (para histórico
e re-scoring).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vertical TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coletado_em TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_vertical ON snapshots(vertical, coletado_em);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT UNIQUE NOT NULL,           -- hash de cnpj|empresa|site
    vertical TEXT NOT NULL,
    empresa TEXT,
    cnpj TEXT,
    site TEXT,
    razao_social TEXT,
    decisor_nome TEXT,
    decisor_cargo TEXT,
    decisor_linkedin TEXT,
    email_provavel TEXT,
    email_validado INTEGER,
    porte_estimado TEXT,
    score_icp INTEGER,
    recomendacao TEXT,
    gatilho_personalizado TEXT,
    observacoes TEXT,
    fonte TEXT,
    payload_json TEXT,                          -- objeto completo
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    score_atualizado_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_leads_vertical ON leads(vertical);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score_icp DESC);
CREATE INDEX IF NOT EXISTS idx_leads_recomendacao ON leads(recomendacao);

CREATE TABLE IF NOT EXISTS outbound_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    canal TEXT NOT NULL,                        -- sms | email | linkedin
    mensagem TEXT NOT NULL,
    gerado_em TEXT NOT NULL,
    enviado_em TEXT,
    status TEXT DEFAULT 'rascunho',             -- rascunho | aprovado | enviado | rejeitado
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
CREATE INDEX IF NOT EXISTS idx_msg_lead ON outbound_messages(lead_id);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,                         -- novo_lead | nova_bet | nova_ip | rescore | outbound | intercom_push
    payload_json TEXT,
    criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_tipo ON events(tipo, criado_em);
"""


class Store:
    """Wrapper SQLite simples e direto."""

    def __init__(self, db_path: Path | str = Path("data/solve_scraper.db")):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _init_schema(self) -> None:
        with self.conn() as c:
            c.executescript(SCHEMA)

    # ====== Snapshots ======

    def save_snapshot(self, vertical: str, fonte: str, payload: list[dict]) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO snapshots (vertical, fonte, coletado_em, payload_json) VALUES (?, ?, ?, ?)",
                (vertical, fonte, datetime.now().isoformat(), json.dumps(payload, ensure_ascii=False)),
            )
            return cur.lastrowid

    def last_snapshot(self, vertical: str) -> list[dict] | None:
        with self.conn() as c:
            row = c.execute(
                "SELECT payload_json FROM snapshots WHERE vertical=? ORDER BY coletado_em DESC LIMIT 1",
                (vertical,),
            ).fetchone()
            if not row:
                return None
            return json.loads(row["payload_json"])

    # ====== Leads ======

    def upsert_lead(self, lead: dict[str, Any]) -> int:
        """Insere ou atualiza um lead pelo fingerprint."""
        fp = _fingerprint(lead)
        now = datetime.now().isoformat()
        cols = {
            "fingerprint": fp,
            "vertical": lead.get("vertical"),
            "empresa": lead.get("empresa"),
            "cnpj": lead.get("cnpj"),
            "site": lead.get("site"),
            "razao_social": lead.get("razao_social"),
            "decisor_nome": lead.get("decisor_nome"),
            "decisor_cargo": lead.get("decisor_cargo"),
            "decisor_linkedin": lead.get("decisor_linkedin"),
            "email_provavel": lead.get("email_provavel"),
            "email_validado": int(bool(lead.get("email_validado"))) if lead.get("email_validado") is not None else None,
            "porte_estimado": lead.get("porte_estimado"),
            "score_icp": lead.get("score_icp"),
            "recomendacao": lead.get("recomendacao"),
            "gatilho_personalizado": lead.get("gatilho_personalizado"),
            "observacoes": lead.get("observacoes") or lead.get("classificacao_obs"),
            "fonte": lead.get("fonte"),
            "payload_json": json.dumps(lead, ensure_ascii=False, default=str),
            "atualizado_em": now,
            "score_atualizado_em": now if lead.get("score_icp") is not None else None,
        }

        with self.conn() as c:
            existing = c.execute("SELECT id FROM leads WHERE fingerprint=?", (fp,)).fetchone()
            if existing:
                set_clause = ", ".join(f"{k}=?" for k in cols)
                c.execute(
                    f"UPDATE leads SET {set_clause} WHERE id=?",
                    (*cols.values(), existing["id"]),
                )
                return existing["id"]
            cols["criado_em"] = now
            keys = ",".join(cols.keys())
            placeholders = ",".join("?" * len(cols))
            cur = c.execute(f"INSERT INTO leads ({keys}) VALUES ({placeholders})", tuple(cols.values()))
            return cur.lastrowid

    def upsert_leads(self, leads: Iterable[dict]) -> int:
        count = 0
        for lead in leads:
            self.upsert_lead(lead)
            count += 1
        return count

    def all_leads(
        self,
        vertical: str | None = None,
        min_score: int | None = None,
        limit: int = 500,
    ) -> list[dict]:
        sql = "SELECT * FROM leads WHERE 1=1"
        params: list[Any] = []
        if vertical and vertical != "all":
            sql += " AND vertical=?"
            params.append(vertical)
        if min_score is not None:
            sql += " AND score_icp >= ?"
            params.append(min_score)
        sql += " ORDER BY COALESCE(score_icp, 0) DESC, criado_em DESC LIMIT ?"
        params.append(limit)
        with self.conn() as c:
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    def leads_for_rescore(self, days_since: int = 7, max_score: int = 70) -> list[dict]:
        """Leads que precisam ser re-pontuados (score entre 40 e max_score, sem update há N dias)."""
        cutoff = datetime.now().timestamp() - days_since * 86400
        with self.conn() as c:
            rows = c.execute(
                """SELECT * FROM leads
                   WHERE COALESCE(score_icp, 0) BETWEEN 40 AND ?
                   AND (score_atualizado_em IS NULL
                        OR julianday('now') - julianday(score_atualizado_em) >= ?)
                   ORDER BY score_icp DESC""",
                (max_score, days_since),
            ).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        with self.conn() as c:
            total = c.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
            por_vertical = {
                r["vertical"]: r["n"]
                for r in c.execute(
                    "SELECT vertical, COUNT(*) AS n FROM leads GROUP BY vertical"
                ).fetchall()
            }
            por_rec = {
                r["recomendacao"]: r["n"]
                for r in c.execute(
                    "SELECT recomendacao, COUNT(*) AS n FROM leads GROUP BY recomendacao"
                ).fetchall()
            }
            score_buckets = c.execute(
                """SELECT
                    SUM(CASE WHEN score_icp >= 80 THEN 1 ELSE 0 END) AS q80,
                    SUM(CASE WHEN score_icp BETWEEN 60 AND 79 THEN 1 ELSE 0 END) AS q60,
                    SUM(CASE WHEN score_icp BETWEEN 40 AND 59 THEN 1 ELSE 0 END) AS q40,
                    SUM(CASE WHEN score_icp < 40 OR score_icp IS NULL THEN 1 ELSE 0 END) AS q0
                FROM leads"""
            ).fetchone()
            ultimos = c.execute(
                "SELECT vertical, empresa, score_icp, criado_em FROM leads ORDER BY criado_em DESC LIMIT 10"
            ).fetchall()
            return {
                "total": total,
                "por_vertical": por_vertical,
                "por_recomendacao": por_rec,
                "score_buckets": dict(score_buckets) if score_buckets else {},
                "ultimos": [dict(r) for r in ultimos],
            }

    # ====== Outbound ======

    def save_outbound(self, lead_id: int, canal: str, mensagem: str) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO outbound_messages (lead_id, canal, mensagem, gerado_em) VALUES (?, ?, ?, ?)",
                (lead_id, canal, mensagem, datetime.now().isoformat()),
            )
            return cur.lastrowid

    def outbound_for_lead(self, lead_id: int) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM outbound_messages WHERE lead_id=? ORDER BY canal", (lead_id,)
            ).fetchall()]

    # ====== Events ======

    def log_event(self, tipo: str, payload: dict | None = None) -> None:
        with self.conn() as c:
            c.execute(
                "INSERT INTO events (tipo, payload_json, criado_em) VALUES (?, ?, ?)",
                (tipo, json.dumps(payload or {}, ensure_ascii=False, default=str), datetime.now().isoformat()),
            )

    def recent_events(self, limit: int = 50) -> list[dict]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT * FROM events ORDER BY criado_em DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]


def _fingerprint(lead: dict) -> str:
    """Identidade única do lead."""
    import hashlib
    cnpj = (lead.get("cnpj") or "").replace(".", "").replace("/", "").replace("-", "")
    empresa = (lead.get("empresa") or "").lower().strip()
    site = (lead.get("site") or "").lower().strip().replace("https://", "").replace("http://", "").rstrip("/")
    key = f"{cnpj}|{empresa}|{site}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]
