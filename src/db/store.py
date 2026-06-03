"""Persistência local em SQLite.

Armazena snapshots de listas (para diff) e leads processados (para histórico
e re-scoring).
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
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

CREATE TABLE IF NOT EXISTS lead_playbooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    playbook_id TEXT NOT NULL,
    playbook_nome TEXT,
    categoria TEXT,
    ordem INTEGER DEFAULT 99,
    justificativa TEXT,
    sinal_detectado TEXT,
    status TEXT DEFAULT 'sugerido',             -- sugerido | em_execucao | concluido | abandonado
    criado_em TEXT NOT NULL,
    atualizado_em TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    UNIQUE(lead_id, playbook_id)
);
CREATE INDEX IF NOT EXISTS idx_pb_lead ON lead_playbooks(lead_id);
CREATE INDEX IF NOT EXISTS idx_pb_status ON lead_playbooks(status);

CREATE TABLE IF NOT EXISTS sdr_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    sdr_email TEXT NOT NULL,
    tipo TEXT NOT NULL,                         -- toque_enviado | resposta_recebida | reuniao_agendada | qualificado | descartado
    canal TEXT,                                 -- linkedin | email | sms | whatsapp | voz
    playbook_id TEXT,
    outcome TEXT,                               -- positivo | neutro | negativo | objecao | sem_resposta
    notas TEXT,
    criado_em TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
CREATE INDEX IF NOT EXISTS idx_act_lead ON sdr_activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_act_sdr ON sdr_activities(sdr_email, criado_em);

CREATE TABLE IF NOT EXISTS atividades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER,                            -- cliente-alvo (FK leads)
    titulo TEXT,
    natureza TEXT DEFAULT 'evento',             -- evento | tarefa | lembrete
    tipo TEXT,                                  -- ligacao | videochamada | email | visita | almoco | personalizado
    inicio_em TEXT,                             -- ISO8601 (dia + hora)
    duracao_min INTEGER,
    dia_inteiro INTEGER DEFAULT 0,
    repeticao TEXT DEFAULT 'nenhuma',           -- nenhuma | diaria | semanal | mensal
    temperatura TEXT,                           -- muito_quente | quente | frio | muito_frio
    pipeline TEXT DEFAULT 'potencial_cliente',  -- potencial_cliente | leads | oportunidades | pos_venda
    responsavel TEXT,                           -- e-mail do SDR
    contato_nome TEXT,
    descricao TEXT,
    tags TEXT,                                  -- JSON array
    status TEXT DEFAULT 'a_fazer',              -- a_fazer | executada | atrasada | reagendada | cancelada
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
CREATE INDEX IF NOT EXISTS idx_atv_lead ON atividades(lead_id);
CREATE INDEX IF NOT EXISTS idx_atv_inicio ON atividades(inicio_em);
CREATE INDEX IF NOT EXISTS idx_atv_pipeline ON atividades(pipeline);
CREATE INDEX IF NOT EXISTS idx_atv_status ON atividades(status);
CREATE INDEX IF NOT EXISTS idx_atv_responsavel ON atividades(responsavel);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    nome TEXT,
    criado_em TEXT NOT NULL,
    expira_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_email ON sessions(email);

-- Colunas adicionais em leads (atribuição + status SDR)
"""

# Migrations idempotentes para colunas adicionais (ALTER TABLE)
LEAD_MIGRATIONS = [
    ("telefone", "TEXT"),
    ("pipeline_status", "TEXT"),   # em_andamento | congelado | ganho | perdido (timeline de vendas)
    ("sdr_assigned", "TEXT"),
    ("sdr_assigned_at", "TEXT"),
    ("sdr_status", "TEXT DEFAULT 'a_contatar'"),  # a_contatar | contatado | respondeu | qualificado | descartado | reuniao_agendada
    ("sdr_status_at", "TEXT"),
]

# Migrations idempotentes em outbound_messages (status: rascunho|aprovado|enviado|respondido|rejeitado|falhou)
OUTBOUND_MIGRATIONS = [
    ("erro", "TEXT"),
    ("respondido_em", "TEXT"),
]


class Store:
    """Wrapper SQLite simples e direto."""

    def __init__(self, db_path: Path | str = Path("data/solve_scraper.db")):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA busy_timeout=5000")  # espera locks em vez de falhar (multiusuário)
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _init_schema(self) -> None:
        with self.conn() as c:
            c.execute("PRAGMA journal_mode=WAL")  # leituras concorrentes durante escrita
            c.executescript(SCHEMA)
            # Migrations idempotentes para colunas adicionais
            existing = {r["name"] for r in c.execute("PRAGMA table_info(leads)").fetchall()}
            for col, ddl in LEAD_MIGRATIONS:
                if col not in existing:
                    c.execute(f"ALTER TABLE leads ADD COLUMN {col} {ddl}")
            existing_ob = {r["name"] for r in c.execute("PRAGMA table_info(outbound_messages)").fetchall()}
            for col, ddl in OUTBOUND_MIGRATIONS:
                if col not in existing_ob:
                    c.execute(f"ALTER TABLE outbound_messages ADD COLUMN {col} {ddl}")

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
            "telefone": lead.get("telefone"),
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

    def update_lead_fields(self, lead_id: int, fields: dict[str, Any]) -> bool:
        """Atualiza campos pontuais de um lead por id (whitelist)."""
        allowed = {"pipeline_status", "sdr_status", "sdr_status_at"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return False
        sets["atualizado_em"] = datetime.now().isoformat()
        clause = ", ".join(f"{k}=?" for k in sets)
        with self.conn() as c:
            cur = c.execute(
                f"UPDATE leads SET {clause} WHERE id=?", (*sets.values(), lead_id)
            )
            return cur.rowcount > 0

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

    def cockpit(self, dia_de: str, dia_ate: str) -> dict[str, Any]:
        """Painel operacional do vendedor ("Meu dia"): o que fazer agora."""
        PIPE = ["potencial_cliente", "leads", "oportunidades", "pos_venda"]
        with self.conn() as c:
            def scalar(q: str, p: tuple = ()) -> int:
                return c.execute(q, p).fetchone()[0] or 0

            hoje = scalar(
                "SELECT COUNT(*) FROM atividades WHERE inicio_em>=? AND inicio_em<?",
                (dia_de, dia_ate),
            )
            atrasadas = scalar(
                "SELECT COUNT(*) FROM atividades WHERE inicio_em<? AND status IN ('a_fazer','reagendada')",
                (dia_de,),
            )
            aguardando = scalar("SELECT COUNT(*) FROM outbound_messages WHERE status='enviado'")
            respondidos = scalar("SELECT COUNT(*) FROM outbound_messages WHERE status='respondido'")
            enviados = scalar("SELECT COUNT(*) FROM outbound_messages WHERE status IN ('enviado','respondido')")
            quentes = scalar(
                "SELECT COUNT(*) FROM leads WHERE COALESCE(score_icp,0)>=70 AND COALESCE(sdr_status,'a_contatar')='a_contatar'"
            )
            funil_raw = {
                r["pipeline"]: r["n"]
                for r in c.execute("SELECT pipeline, COUNT(*) AS n FROM atividades GROUP BY pipeline").fetchall()
            }
            funil = {k: funil_raw.get(k, 0) for k in PIPE}

            def rows(q: str, p: tuple = ()) -> list[dict]:
                return [dict(r) for r in c.execute(q, p).fetchall()]

            hoje_list = rows(
                """SELECT a.id, a.titulo, a.tipo, a.inicio_em, a.temperatura, a.pipeline,
                          l.empresa AS cliente
                   FROM atividades a LEFT JOIN leads l ON a.lead_id=l.id
                   WHERE a.inicio_em>=? AND a.inicio_em<? ORDER BY a.inicio_em LIMIT 30""",
                (dia_de, dia_ate),
            )
            atrasadas_list = rows(
                """SELECT a.id, a.titulo, a.tipo, a.inicio_em, l.empresa AS cliente
                   FROM atividades a LEFT JOIN leads l ON a.lead_id=l.id
                   WHERE a.inicio_em<? AND a.status IN ('a_fazer','reagendada')
                   ORDER BY a.inicio_em DESC LIMIT 20""",
                (dia_de,),
            )
            quentes_list = rows(
                """SELECT id, empresa, vertical, score_icp, decisor_nome, decisor_cargo, email_provavel
                   FROM leads WHERE COALESCE(score_icp,0)>=70 AND COALESCE(sdr_status,'a_contatar')='a_contatar'
                   ORDER BY score_icp DESC LIMIT 20"""
            )
            aguardando_list = rows(
                """SELECT m.id, m.canal, m.enviado_em, l.empresa AS cliente
                   FROM outbound_messages m LEFT JOIN leads l ON m.lead_id=l.id
                   WHERE m.status='enviado' ORDER BY m.enviado_em DESC LIMIT 20"""
            )
            respostas_list = rows(
                """SELECT m.id, m.canal, m.respondido_em, l.empresa AS cliente
                   FROM outbound_messages m LEFT JOIN leads l ON m.lead_id=l.id
                   WHERE m.status='respondido' ORDER BY m.respondido_em DESC LIMIT 20"""
            )

        taxa = round(100 * respondidos / enviados, 1) if enviados else 0.0
        return {
            "hoje": hoje, "atrasadas": atrasadas, "aguardando_resposta": aguardando,
            "respondidos": respondidos, "enviados": enviados, "taxa_resposta": taxa,
            "quentes_a_contatar": quentes, "funil": funil,
            "hoje_list": hoje_list, "atrasadas_list": atrasadas_list,
            "quentes_list": quentes_list, "aguardando_list": aguardando_list,
            "respostas_list": respostas_list,
        }

    def reminders(self, dia_de: str, dia_ate: str, dias_followup: int = 3) -> dict[str, Any]:
        """Lembretes acionáveis ("o que cobrar agora") a partir dos dados existentes."""
        corte_fu = (datetime.now() - timedelta(days=dias_followup)).isoformat()
        itens: list[dict] = []
        with self.conn() as c:
            def rows(q: str, p: tuple = ()) -> list[dict]:
                return [dict(r) for r in c.execute(q, p).fetchall()]

            for a in rows(
                """SELECT a.id, a.titulo, l.empresa FROM atividades a LEFT JOIN leads l ON a.lead_id=l.id
                   WHERE a.inicio_em<? AND a.status IN ('a_fazer','reagendada') ORDER BY a.inicio_em DESC LIMIT 30""",
                (dia_de,),
            ):
                itens.append({"tipo": "atrasada", "titulo": a["titulo"] or "Atividade", "sub": a["empresa"] or "—", "acao": "oportunidades", "atividade_id": a["id"]})
            for a in rows(
                """SELECT a.id, a.titulo, l.empresa FROM atividades a LEFT JOIN leads l ON a.lead_id=l.id
                   WHERE a.inicio_em>=? AND a.inicio_em<? AND a.status IN ('a_fazer','reagendada') ORDER BY a.inicio_em LIMIT 30""",
                (dia_de, dia_ate),
            ):
                itens.append({"tipo": "hoje", "titulo": a["titulo"] or "Atividade", "sub": a["empresa"] or "—", "acao": "oportunidades", "atividade_id": a["id"]})
            for m in rows(
                """SELECT m.lead_id, l.empresa FROM outbound_messages m LEFT JOIN leads l ON m.lead_id=l.id
                   WHERE m.status='enviado' AND COALESCE(m.enviado_em,'')<? ORDER BY m.enviado_em LIMIT 30""",
                (corte_fu,),
            ):
                itens.append({"tipo": "sem_resposta", "titulo": "Sem resposta — faça follow-up", "sub": m["empresa"] or "—", "acao": "outbound", "lead_id": m["lead_id"]})
            for m in rows(
                """SELECT m.lead_id, l.empresa FROM outbound_messages m LEFT JOIN leads l ON m.lead_id=l.id
                   WHERE m.status='respondido' ORDER BY m.respondido_em DESC LIMIT 20"""
            ):
                itens.append({"tipo": "resposta", "titulo": "Respondeu — agende reunião", "sub": m["empresa"] or "—", "acao": "oportunidades", "lead_id": m["lead_id"]})
            for q in rows(
                """SELECT id, empresa FROM leads WHERE COALESCE(score_icp,0)>=70
                   AND COALESCE(sdr_status,'a_contatar')='a_contatar' ORDER BY score_icp DESC LIMIT 30"""
            ):
                itens.append({"tipo": "quente_sem_contato", "titulo": "Lead quente sem contato", "sub": q["empresa"] or "—", "acao": "leads", "lead_id": q["id"]})
        return {"count": len(itens), "itens": itens}

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

    def outbound_message(self, msg_id: int) -> dict | None:
        with self.conn() as c:
            row = c.execute(
                """SELECT m.*, l.empresa AS lead_empresa, l.email_provavel AS lead_email,
                          l.email_validado AS lead_email_validado, l.decisor_nome AS lead_decisor
                   FROM outbound_messages m LEFT JOIN leads l ON m.lead_id = l.id
                   WHERE m.id = ?""",
                (msg_id,),
            ).fetchone()
            return dict(row) if row else None

    def outbound_sibling(self, lead_id: int, canal: str) -> dict | None:
        """Outra mensagem do mesmo lead num canal específico (ex.: assunto do e-mail)."""
        with self.conn() as c:
            row = c.execute(
                "SELECT * FROM outbound_messages WHERE lead_id=? AND canal=? ORDER BY id DESC LIMIT 1",
                (lead_id, canal),
            ).fetchone()
            return dict(row) if row else None

    def all_outbound(self, status: str | None = None, limit: int = 200) -> list[dict]:
        sql = [
            """SELECT m.*, l.empresa AS lead_empresa, l.email_provavel AS lead_email,
                      l.email_validado AS lead_email_validado, l.vertical AS vertical,
                      l.score_icp AS score_icp, l.decisor_nome AS decisor_nome,
                      l.decisor_cargo AS decisor_cargo
               FROM outbound_messages m LEFT JOIN leads l ON m.lead_id = l.id WHERE 1=1"""
        ]
        params: list[Any] = []
        if status:
            sql.append(" AND m.status = ?")
            params.append(status)
        sql.append(" ORDER BY m.gerado_em DESC LIMIT ?")
        params.append(limit)
        with self.conn() as c:
            return [dict(r) for r in c.execute("".join(sql), params).fetchall()]

    def update_outbound_status(
        self,
        msg_id: int,
        status: str,
        *,
        enviado_em: str | None = None,
        respondido_em: str | None = None,
        erro: str | None = None,
    ) -> bool:
        sets: dict[str, Any] = {"status": status, "erro": erro}
        if enviado_em is not None:
            sets["enviado_em"] = enviado_em
        if respondido_em is not None:
            sets["respondido_em"] = respondido_em
        clause = ", ".join(f"{k}=?" for k in sets)
        with self.conn() as c:
            cur = c.execute(
                f"UPDATE outbound_messages SET {clause} WHERE id=?",
                (*sets.values(), msg_id),
            )
            return cur.rowcount > 0

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

    # ====== Sessions (auth) ======

    def create_session(self, email: str, nome: str | None = None, dias: int = 30) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now()
        with self.conn() as c:
            c.execute(
                "INSERT INTO sessions (token, email, nome, criado_em, expira_em) VALUES (?,?,?,?,?)",
                (token, email, nome, now.isoformat(), (now + timedelta(days=dias)).isoformat()),
            )
        return token

    def get_session(self, token: str | None) -> dict | None:
        if not token:
            return None
        with self.conn() as c:
            row = c.execute("SELECT * FROM sessions WHERE token=?", (token,)).fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("expira_em") and d["expira_em"] < datetime.now().isoformat():
            self.delete_session(token)
            return None
        return d

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self.conn() as c:
            c.execute("DELETE FROM sessions WHERE token=?", (token,))

    # ====== Atividades (vendas / oportunidades) ======

    def create_atividade(self, data: dict[str, Any]) -> int:
        """Cria uma atividade de venda vinculada (opcionalmente) a um lead."""
        now = datetime.now().isoformat()
        tags = data.get("tags")
        if isinstance(tags, (list, dict)):
            tags = json.dumps(tags, ensure_ascii=False)
        cols = {
            "lead_id": data.get("lead_id"),
            "titulo": data.get("titulo"),
            "natureza": data.get("natureza") or "evento",
            "tipo": data.get("tipo"),
            "inicio_em": data.get("inicio_em"),
            "duracao_min": data.get("duracao_min"),
            "dia_inteiro": int(bool(data.get("dia_inteiro"))),
            "repeticao": data.get("repeticao") or "nenhuma",
            "temperatura": data.get("temperatura"),
            "pipeline": data.get("pipeline") or "potencial_cliente",
            "responsavel": data.get("responsavel"),
            "contato_nome": data.get("contato_nome"),
            "descricao": data.get("descricao"),
            "tags": tags,
            "status": data.get("status") or "a_fazer",
            "criado_em": now,
            "atualizado_em": now,
        }
        with self.conn() as c:
            keys = ",".join(cols.keys())
            placeholders = ",".join("?" * len(cols))
            cur = c.execute(
                f"INSERT INTO atividades ({keys}) VALUES ({placeholders})",
                tuple(cols.values()),
            )
            return cur.lastrowid

    def get_atividade(self, atividade_id: int) -> dict | None:
        with self.conn() as c:
            row = c.execute(
                """SELECT a.*, l.empresa AS cliente_empresa, l.decisor_nome AS cliente_decisor,
                          l.vertical AS cliente_vertical, l.site AS cliente_site
                   FROM atividades a LEFT JOIN leads l ON a.lead_id = l.id
                   WHERE a.id = ?""",
                (atividade_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_atividades(
        self,
        responsavel: str | None = None,
        tipo: str | None = None,
        temperatura: str | None = None,
        pipeline: str | None = None,
        status: str | None = None,
        lead_id: int | None = None,
        inicio_de: str | None = None,
        inicio_ate: str | None = None,
        limit: int = 500,
        order: str = "asc",
    ) -> list[dict]:
        sql = [
            """SELECT a.*, l.empresa AS cliente_empresa, l.decisor_nome AS cliente_decisor,
                      l.vertical AS cliente_vertical, l.pipeline_status AS cliente_status
               FROM atividades a LEFT JOIN leads l ON a.lead_id = l.id WHERE 1=1"""
        ]
        params: list[Any] = []
        for col, val in (
            ("a.responsavel", responsavel),
            ("a.tipo", tipo),
            ("a.temperatura", temperatura),
            ("a.pipeline", pipeline),
            ("a.status", status),
            ("a.lead_id", lead_id),
        ):
            if val is not None and val != "":
                sql.append(f" AND {col} = ?")
                params.append(val)
        if inicio_de:
            sql.append(" AND a.inicio_em >= ?")
            params.append(inicio_de)
        if inicio_ate:
            sql.append(" AND a.inicio_em < ?")
            params.append(inicio_ate)
        direction = "DESC" if str(order).lower() == "desc" else "ASC"
        sql.append(f" ORDER BY COALESCE(a.inicio_em, a.criado_em) {direction} LIMIT ?")
        params.append(limit)
        with self.conn() as c:
            return [dict(r) for r in c.execute("".join(sql), params).fetchall()]

    def update_atividade(self, atividade_id: int, fields: dict[str, Any]) -> bool:
        allowed = {
            "lead_id", "titulo", "natureza", "tipo", "inicio_em", "duracao_min",
            "dia_inteiro", "repeticao", "temperatura", "pipeline", "responsavel",
            "contato_nome", "descricao", "tags", "status",
        }
        sets = {k: v for k, v in fields.items() if k in allowed}
        if "tags" in sets and isinstance(sets["tags"], (list, dict)):
            sets["tags"] = json.dumps(sets["tags"], ensure_ascii=False)
        if "dia_inteiro" in sets:
            sets["dia_inteiro"] = int(bool(sets["dia_inteiro"]))
        if not sets:
            return False
        sets["atualizado_em"] = datetime.now().isoformat()
        clause = ", ".join(f"{k}=?" for k in sets)
        with self.conn() as c:
            cur = c.execute(
                f"UPDATE atividades SET {clause} WHERE id=?",
                (*sets.values(), atividade_id),
            )
            return cur.rowcount > 0


def _fingerprint(lead: dict) -> str:
    """Identidade única do lead."""
    import hashlib
    cnpj = (lead.get("cnpj") or "").replace(".", "").replace("/", "").replace("-", "")
    empresa = (lead.get("empresa") or "").lower().strip()
    site = (lead.get("site") or "").lower().strip().replace("https://", "").replace("http://", "").rstrip("/")
    key = f"{cnpj}|{empresa}|{site}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]
