"""Testes do ControlStore (multi-tenant) — offline, sem rede."""

from __future__ import annotations

import os
import tempfile

from src.workspaces.control import ControlStore


def _control() -> ControlStore:
    d = tempfile.mkdtemp()
    # default data db separado por teste (isola do data/ real)
    return ControlStore(db_path=os.path.join(d, "control.db"),
                         default_data_db=os.path.join(d, "ws_1.db"))


def test_seed_default_cpaas():
    cs = _control()
    ws1 = cs.get_workspace(1)
    assert ws1 and ws1["nome"] == "Solvefy CPaaS"
    assert ws1["cor"] == "cpaas"
    assert ws1["db_path"].endswith("ws_1.db")
    assert len(cs.list_workspaces()) == 1


def test_create_workspace_isolado():
    cs = _control()
    ws = cs.create_workspace(
        "Acme Cobrança",
        produto="Régua de cobrança",
        site="https://acme.com",
        descricao="Fintech de cobrança",
        icp="IPs e PMEs reguladas",
        cor="conversation",
        anamnese={"resumo": "ok"},
        owner_email="dono@acme.com",
        membros=[{"email": "ed@acme.com", "role": "editor"}, {"email": "le@acme.com", "role": "leitor"}],
    )
    assert ws["id"] == 2
    assert ws["slug"] == "acme-cobranca"
    assert ws["cor"] == "conversation"
    assert ws["db_path"].endswith("ws_2.db")
    # owner vira admin (active) + 2 convidados (invited)
    membros = cs.list_members(2)
    roles = {m["email"]: (m["role"], m["status"]) for m in membros}
    assert roles["dono@acme.com"] == ("admin", "active")
    assert roles["ed@acme.com"] == ("editor", "invited")
    assert roles["le@acme.com"] == ("leitor", "invited")


def test_get_data_store_isolamento_fisico():
    cs = _control()
    cs.create_workspace("Acme", owner_email="d@a.com")
    s1 = cs.get_data_store(1)
    s2 = cs.get_data_store(2)
    # bancos diferentes
    assert str(s1.db_path) != str(s2.db_path)
    # lead criado no ws2 não aparece no ws1
    s2.upsert_lead({"vertical": "betting", "empresa": "SóNoWs2", "fingerprint": "fp-ws2"})
    assert len(s1.all_leads(limit=50)) == 0
    assert any(l["empresa"] == "SóNoWs2" for l in s2.all_leads(limit=50))


def test_role_of():
    cs = _control()
    cs.create_workspace("X", owner_email="dono@x.com", membros=[{"email": "ed@x.com", "role": "editor"}])
    assert cs.role_of(2, "dono@x.com") == "admin"
    cs.add_member(2, "ed@x.com", "editor", status="active")
    assert cs.role_of(2, "ed@x.com") == "editor"
    assert cs.role_of(2, "ninguem@x.com") is None


def test_cor_invalida_cai_para_cpaas():
    cs = _control()
    ws = cs.create_workspace("Y", cor="roxo-maluco", owner_email="d@y.com")
    assert ws["cor"] == "cpaas"
