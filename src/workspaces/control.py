"""Controle central de workspaces (multi-tenant).

Cada workspace tem seu PRÓPRIO banco de dados (`data/ws_<id>.db`) com o schema normal
do `Store` — isolamento físico, sem `workspace_id` espalhado nas tabelas. Este módulo
guarda só o registro de workspaces + membros num banco-controle (`data/control.db`) e
resolve o `Store` certo por workspace.

O workspace #1 ("Solvefy CPaaS") aponta para o banco atual (`data/solve_scraper.db`),
então tudo que já existe vira o primeiro workspace automaticamente.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from ..db.store import Store

# Banco de dados atual = workspace #1 (CPaaS). Mantém os dados existentes.
DEFAULT_DATA_DB = "data/solve_scraper.db"
ROLES = ("admin", "editor", "leitor")
# Cores = sub-marcas Solvefy (classe .brand-* no front). Mantém tudo on-brand.
CORES = ("solvefy", "admin", "crm", "ads", "marketing", "conversation", "cpaas", "cloud", "agents", "clila")

CONTROL_SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT UNIQUE,
    nome          TEXT NOT NULL,
    produto       TEXT,
    site          TEXT,
    descricao     TEXT,
    icp           TEXT,
    cor           TEXT NOT NULL DEFAULT 'cpaas',
    anamnese_json TEXT,
    owner_email   TEXT,
    db_path       TEXT NOT NULL,
    criado_em     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workspace_members (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    email        TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'leitor',
    status       TEXT NOT NULL DEFAULT 'active',
    criado_em    TEXT NOT NULL,
    UNIQUE(workspace_id, email)
);
CREATE INDEX IF NOT EXISTS idx_members_ws ON workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS idx_members_email ON workspace_members(email);
"""


def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")  # ç→c, ã→a
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "workspace"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ControlStore:
    """Registro de workspaces + resolução do Store de dados por workspace."""

    def __init__(self, db_path: Path | str = "data/control.db", default_data_db: str = DEFAULT_DATA_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_data_db = default_data_db
        self._stores: dict[int, Store] = {}  # cache id -> Store
        self._init_schema()
        self.seed_default()

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA busy_timeout=5000")
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _init_schema(self) -> None:
        with self.conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(CONTROL_SCHEMA)

    # ====== Seed do workspace #1 (CPaaS) ======
    def seed_default(self) -> None:
        if self.get_workspace(1):
            return
        with self.conn() as c:
            c.execute(
                """INSERT INTO workspaces (id, slug, nome, produto, site, descricao, cor, db_path, criado_em)
                   VALUES (1, 'cpaas', 'Solvefy CPaaS',
                           'Solvefy CPaaS — infraestrutura de comunicação omnichannel (SMS, WhatsApp, RCS, Voz, E-mail)',
                           'https://solvefy.com.br',
                           'Plataforma CPaaS brasileira: 5 canais em 1 API, faturamento em BRL, suporte PT-BR.',
                           'cpaas', ?, ?)""",
                (self.default_data_db, _now()),
            )

    # ====== Workspaces ======
    def list_workspaces(self, email: str | None = None) -> list[dict]:
        with self.conn() as c:
            if email:
                rows = c.execute(
                    """SELECT w.* FROM workspaces w
                       WHERE w.id = 1
                          OR w.owner_email = ?
                          OR EXISTS (SELECT 1 FROM workspace_members m
                                     WHERE m.workspace_id = w.id AND m.email = ? AND m.status='active')
                       ORDER BY w.id""",
                    (email, email),
                ).fetchall()
            else:
                rows = c.execute("SELECT * FROM workspaces ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    def get_workspace(self, ws_id: int) -> dict | None:
        with self.conn() as c:
            row = c.execute("SELECT * FROM workspaces WHERE id=?", (int(ws_id),)).fetchone()
            return dict(row) if row else None

    def create_workspace(
        self,
        nome: str,
        *,
        produto: str | None = None,
        site: str | None = None,
        descricao: str | None = None,
        icp: str | None = None,
        cor: str = "cpaas",
        anamnese: dict | None = None,
        owner_email: str | None = None,
        membros: list[dict] | None = None,
    ) -> dict:
        cor = cor if cor in CORES else "cpaas"
        slug = self._unique_slug(_slugify(nome))
        with self.conn() as c:
            cur = c.execute(
                """INSERT INTO workspaces (slug, nome, produto, site, descricao, icp, cor, anamnese_json, owner_email, db_path, criado_em)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (slug, nome, produto, site, descricao, icp, cor,
                 json.dumps(anamnese, ensure_ascii=False) if anamnese else None,
                 owner_email, "", _now()),
            )
            ws_id = cur.lastrowid
            # db do workspace fica ao lado do control.db (testes em tmpdir não poluem data/ real)
            db_path = str(self.db_path.parent / f"ws_{ws_id}.db")
            c.execute("UPDATE workspaces SET db_path=? WHERE id=?", (db_path, ws_id))

        # Cria o banco de dados (vazio) do novo workspace com o schema normal
        Store(db_path=db_path)

        # Dono + convidados
        if owner_email:
            self.add_member(ws_id, owner_email, "admin", status="active")
        for m in (membros or []):
            em = (m.get("email") or "").strip()
            if em:
                self.add_member(ws_id, em, m.get("role", "leitor"), status="invited")

        return self.get_workspace(ws_id)

    def _unique_slug(self, base: str) -> str:
        with self.conn() as c:
            taken = {r["slug"] for r in c.execute("SELECT slug FROM workspaces").fetchall()}
        if base not in taken:
            return base
        i = 2
        while f"{base}-{i}" in taken:
            i += 1
        return f"{base}-{i}"

    # ====== Membros ======
    def add_member(self, ws_id: int, email: str, role: str = "leitor", status: str = "active") -> None:
        role = role if role in ROLES else "leitor"
        with self.conn() as c:
            c.execute(
                """INSERT INTO workspace_members (workspace_id, email, role, status, criado_em)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(workspace_id, email) DO UPDATE SET role=excluded.role, status=excluded.status""",
                (int(ws_id), email.strip().lower(), role, status, _now()),
            )

    def list_members(self, ws_id: int) -> list[dict]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT id, email, role, status, criado_em FROM workspace_members WHERE workspace_id=? ORDER BY id",
                (int(ws_id),),
            ).fetchall()
            return [dict(r) for r in rows]

    def role_of(self, ws_id: int, email: str | None) -> str | None:
        if not email:
            return None
        ws = self.get_workspace(ws_id)
        if ws and ws.get("owner_email") and ws["owner_email"].lower() == email.lower():
            return "admin"
        with self.conn() as c:
            row = c.execute(
                "SELECT role FROM workspace_members WHERE workspace_id=? AND email=? AND status='active'",
                (int(ws_id), email.strip().lower()),
            ).fetchone()
            return row["role"] if row else None

    # ====== Resolução do Store de dados ======
    def get_data_store(self, ws_id: int | str | None) -> Store:
        """Retorna o Store do workspace (cacheado). Fallback para #1 se inválido."""
        try:
            ws_id = int(ws_id) if ws_id is not None else 1
        except (ValueError, TypeError):
            ws_id = 1
        ws = self.get_workspace(ws_id) or self.get_workspace(1)
        wid = ws["id"]
        if wid not in self._stores:
            self._stores[wid] = Store(db_path=ws["db_path"])
        return self._stores[wid]
