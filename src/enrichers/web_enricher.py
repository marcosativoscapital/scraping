"""Enriquecimento de leads via Gemini + Google Search grounding.

Para cada lead, pesquisa no Google decisores reais (LinkedIn), e-mails,
telefones, gatilhos (funding, vagas), vendor de comunicação atual e
oportunidades específicas.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from google import genai
from google.genai import types

from ..db.store import Store

logger = logging.getLogger(__name__)


SYSTEM_ENRICHER = """Você é um SDR sênior pesquisando empresas brasileiras pra prospecção CPaaS.

A partir do nome da empresa, você usa Google Search para encontrar:

1. DECISORES (até 4 nomes reais):
   - CEO / Sócio / Founder
   - CTO / Head Engineering / VP Tech
   - Head Marketing / CMO / Growth
   - Compliance Officer / CFO / COO (se IP regulada ou financeira)
   - Pra cada um: nome completo, cargo, URL do LinkedIn (se público)

2. CONTATOS INSTITUCIONAIS:
   - E-mail comercial / contato (sem inventar)
   - Telefone (se público no site)

3. GATILHOS RECENTES (últimos 12 meses):
   - Funding rounds (Série A/B/C)
   - Lançamento de produto/novo canal
   - Vagas abertas em platform engineering / mensageria
   - Notícias relevantes (regulação, expansão)

4. VENDOR ATUAL DE COMUNICAÇÃO (se identificável):
   - Twilio / Infobip / Zenvia / Take Blip / Pontaltech / Mensageria?
   - Indícios (job posting, blog, case study, integration docs)

5. OPORTUNIDADE ESPECÍFICA:
   - 1 frase resumindo a oportunidade real de Solvefy CPaaS aqui

REGRAS:
- NUNCA invente nome, e-mail, telefone ou LinkedIn URL
- Se não achar com confiança, retorne null
- Cite fontes nas notas (URL da pesquisa)
- Português brasileiro"""


def get_client_with_search() -> genai.Client:
    """Cliente Gemini configurado com Google Search grounding."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não definida")
    return genai.Client(api_key=api_key)


def enrich_lead_via_web(lead: dict[str, Any]) -> dict[str, Any]:
    """Pesquisa web + LinkedIn para enriquecer um lead.

    Retorna dict com chaves:
      - decisores: [{nome, cargo, linkedin_url}]
      - email_decisor, telefone_decisor (se identificados)
      - gatilhos_recentes: [str]
      - vendor_atual: str | None
      - vendor_evidencia: str
      - oportunidade_resumida: str
      - fontes: [str]
    """
    empresa = lead.get("empresa") or lead.get("razao_social", "")
    vertical = lead.get("vertical", "")
    site = lead.get("site") or ""

    if not empresa:
        return {"erro": "sem nome de empresa"}

    schema = """{
  "decisores": [
    {
      "nome": "Nome Completo",
      "cargo": "Cargo exato",
      "linkedin_url": "https://linkedin.com/in/... ou null",
      "email": "se identificou ou null",
      "fonte": "URL da fonte"
    }
  ],
  "email_institucional": "ou null",
  "telefone_institucional": "ou null",
  "gatilhos_recentes": ["lista de eventos relevantes"],
  "vendor_comunicacao_atual": "Twilio|Zenvia|Infobip|Take Blip|outros|null",
  "vendor_evidencia": "como descobriu (cite fonte)",
  "oportunidade_resumida": "1 frase explicando a oportunidade",
  "porte_aparente": "pequena|media|grande|enterprise",
  "tech_stack_mensageria": ["ferramentas identificadas"],
  "fontes": ["URLs consultadas"]
}"""

    prompt = f"""Pesquise no Google sobre a empresa brasileira: {empresa}
Vertical: {vertical}
Site (se conhecido): {site}

Busque informações sobre decisores (CEO, CTO, Head Marketing, Compliance Officer),
gatilhos recentes (funding, vagas, lançamentos), vendor de comunicação atual e
oportunidade específica para o Solvefy CPaaS.

Responda APENAS com JSON válido conforme schema:
{schema}

Use Google Search ativamente. Não invente — null se não achou."""

    client = get_client_with_search()
    try:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            system_instruction=SYSTEM_ENRICHER,
            temperature=0.0,
            max_output_tokens=4096,
        )
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config=config,
        )
        text = (response.text or "").strip()
        # Remove cercas markdown se houver
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:].strip()
            text = text.rstrip("`").strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("JSON malformado de Gemini: %s\nTexto: %s", e, text[:500])
        return {"erro": f"json_decode: {e}", "raw": text[:800]}
    except Exception as e:
        logger.exception("Falha no enrichment web: %s", e)
        return {"erro": str(e)}


def enrich_and_save(lead_id: int, store: Store | None = None) -> dict[str, Any]:
    """Enriquece um lead e salva no DB."""
    store = store or Store()
    with store.conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        return {"erro": f"lead {lead_id} não encontrado"}

    lead = dict(row)
    enrichment = enrich_lead_via_web(lead)

    # Persiste no payload completo do lead
    if "erro" not in enrichment:
        decisores = enrichment.get("decisores", [])
        primeiro = decisores[0] if decisores else {}
        updates = {
            "decisor_nome": primeiro.get("nome"),
            "decisor_cargo": primeiro.get("cargo"),
            "decisor_linkedin": primeiro.get("linkedin_url"),
            "email_provavel": primeiro.get("email") or lead.get("email_provavel") or enrichment.get("email_institucional"),
            "telefone": lead.get("telefone") or enrichment.get("telefone_institucional"),
            "observacoes": enrichment.get("oportunidade_resumida"),
        }
        with store.conn() as c:
            sets = ", ".join(f"{k}=?" for k, v in updates.items() if v)
            vals = [v for v in updates.values() if v]
            if sets:
                c.execute(f"UPDATE leads SET {sets} WHERE id=?", (*vals, lead_id))
            # Salva enrichment completo no payload_json
            payload = lead.get("payload_json") or "{}"
            payload_d = json.loads(payload) if isinstance(payload, str) else (payload or {})
            payload_d["web_enrichment"] = enrichment
            c.execute(
                "UPDATE leads SET payload_json=? WHERE id=?",
                (json.dumps(payload_d, ensure_ascii=False, default=str), lead_id),
            )
        store.log_event("web_enrichment", {"lead_id": lead_id, "empresa": lead.get("empresa")})

    return enrichment


def enrich_top_n(n: int = 50, min_score: int = 60, store: Store | None = None) -> dict[str, Any]:
    """Enriquece os top N leads do DB."""
    store = store or Store()
    leads = store.all_leads(min_score=min_score, limit=n)
    results = {"enriquecidos": 0, "erros": 0, "detalhes": []}
    for lead in leads:
        try:
            e = enrich_and_save(lead["id"], store=store)
            results["detalhes"].append({
                "id": lead["id"],
                "empresa": lead["empresa"],
                "score": lead.get("score_icp"),
                "decisores": len(e.get("decisores", [])) if "decisores" in e else 0,
                "vendor": e.get("vendor_comunicacao_atual"),
                "erro": e.get("erro"),
            })
            if "erro" not in e:
                results["enriquecidos"] += 1
            else:
                results["erros"] += 1
        except Exception as ex:
            logger.exception("Falha no lead %s: %s", lead.get("empresa"), ex)
            results["erros"] += 1
    return results
