"""Testes do core de vendas: sessões, outbound, cockpit e validação pós-LLM.

Tudo offline — sem Gemini, sem rede (o client é dublado).
"""

from __future__ import annotations

import os
import tempfile

from src.claude_agent import classifier, scorer
from src.db.store import Store


def _store() -> Store:
    return Store(db_path=os.path.join(tempfile.mkdtemp(), "t.db"))


def test_session_lifecycle():
    s = _store()
    tok = s.create_session("a@b.com", "Ana")
    assert s.get_session(tok)["email"] == "a@b.com"
    assert s.get_session(None) is None
    assert s.get_session("inexistente") is None
    s.delete_session(tok)
    assert s.get_session(tok) is None


def test_outbound_status_flow():
    s = _store()
    lid = s.upsert_lead({"vertical": "betting", "empresa": "X", "email_provavel": "x@y.com", "email_validado": True})
    mid = s.save_outbound(lid, "email_body", "corpo")
    assert s.outbound_message(mid)["status"] == "rascunho"
    s.update_outbound_status(mid, "aprovado")
    assert s.outbound_message(mid)["status"] == "aprovado"
    s.update_outbound_status(mid, "enviado", enviado_em="2026-01-01T00:00:00")
    m = s.outbound_message(mid)
    assert m["status"] == "enviado" and m["enviado_em"]
    assert len(s.all_outbound(status="enviado")) == 1
    assert s.outbound_message(mid)["lead_empresa"] == "X"


def test_cockpit_shape():
    s = _store()
    s.upsert_lead({"vertical": "pagamentos", "empresa": "Hot", "score_icp": 85, "sdr_status": "a_contatar"})
    c = s.cockpit("2026-01-01T00:00:00", "2026-01-02T00:00:00")
    assert c["quentes_a_contatar"] >= 1
    assert set(c["funil"].keys()) == {"potencial_cliente", "leads", "oportunidades", "pos_venda"}
    assert isinstance(c["taxa_resposta"], (int, float))


def test_update_lead_fields_whitelist():
    s = _store()
    lid = s.upsert_lead({"vertical": "betting", "empresa": "X"})
    assert s.update_lead_fields(lid, {"pipeline_status": "ganho", "campo_proibido": "x"}) is True
    assert s.update_lead_fields(lid, {"campo_proibido": "x"}) is False  # nada permitido → não atualiza


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload

    def extract_json(self, *args, **kwargs):
        return self._payload


def test_scorer_clamp_e_recomendacao():
    assert scorer.score_lead(_FakeClient({"score": 150}), {})["score"] == 100
    assert scorer.score_lead(_FakeClient({"score": -3}), {})["score"] == 0
    assert scorer.score_lead(_FakeClient({"score": "abc"}), {})["score"] == 0
    r = scorer.score_lead(_FakeClient({"score": 90, "recomendacao": "xpto"}), {})
    assert r["recomendacao"] == "ativar_outbound"


def test_classifier_enum():
    c = classifier.classify_company(_FakeClient({"vertical": "lixo", "porte_estimado": "gigante"}), {})
    assert "vertical" not in c and "porte_estimado" not in c
    c2 = classifier.classify_company(_FakeClient({"vertical": "betting", "porte_estimado": "media"}), {})
    assert c2["vertical"] == "betting" and c2["porte_estimado"] == "media"
