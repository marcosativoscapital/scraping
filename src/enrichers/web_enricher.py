"""Enriquecimento de leads via Gemini + Google Search grounding.

Para cada lead, pesquisa no Google decisores reais (LinkedIn), e-mails,
telefones, gatilhos (funding, vagas), vendor de comunicação atual e
oportunidades específicas.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from google import genai
from google.genai import types

from ..db.store import Store
from .email_validator import validate_email

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


SYSTEM_DECISORES = """Você é um SDR sênior fazendo people-research B2B.
Use Google Search (e perfis de LinkedIn públicos) para encontrar o MÁXIMO de pessoas-chave da
empresa informada: sócios/founders, C-level (CEO, CTO, CFO, COO, CMO), diretores, heads e gerentes
das áreas de Marketing/Growth, Tecnologia/Engenharia, Produto, Operações, Comercial e
Compliance/Risco.

Para cada pessoa: nome completo, cargo, área e a URL do LinkedIn (se pública) + a fonte (URL).
NUNCA invente nome ou URL de LinkedIn. Se não confirmar com confiança, não inclua. Português brasileiro."""


def find_decisores_via_web(lead: dict[str, Any], limit: int = 12) -> dict[str, Any]:
    """Pesquisa na web/LinkedIn o máximo de pessoas-chave (decisores) da empresa."""
    empresa = lead.get("empresa") or lead.get("razao_social", "")
    site = lead.get("site") or ""
    if not empresa:
        return {"erro": "sem nome de empresa", "decisores": []}

    schema = """{
  "decisores": [
    {"nome": "Nome Completo", "cargo": "Cargo", "area": "Marketing|Tecnologia|Produto|Operações|Comercial|Compliance|Executivo",
     "linkedin_url": "https://linkedin.com/in/... ou null", "fonte": "URL da fonte"}
  ],
  "fontes": ["URLs consultadas"]
}"""

    prompt = f"""Pesquise no Google e no LinkedIn as PESSOAS-CHAVE (decisores e influenciadores) da
empresa brasileira: {empresa}
Site (se conhecido): {site}

Traga o máximo possível (até {limit}) de pessoas REAIS, priorizando quem decide ou influencia a
compra de software/comunicação. Responda APENAS com JSON válido conforme o schema:
{schema}

Use Google Search ativamente. Não invente — omita quem não confirmar."""

    client = get_client_with_search()
    last_err: str | None = None
    text = ""
    for attempt in range(3):
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=SYSTEM_DECISORES,
                temperature=0.0,
                max_output_tokens=8192,
            )
            response = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt,
                config=config,
            )
            text = (response.text or "").strip()
            if not text:
                last_err = "resposta vazia (rate limit do google_search?)"
                time.sleep(8 * (attempt + 1))
                continue
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:].strip()
                text = text.rstrip("`").strip()
            else:
                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    text = m.group(0)
            data = json.loads(text, strict=False)
            out: list[dict[str, Any]] = []
            for d in (data.get("decisores") or [])[:limit]:
                if not isinstance(d, dict) or not d.get("nome"):
                    continue
                li = d.get("linkedin_url")
                out.append({
                    "nome": str(d.get("nome"))[:120],
                    "cargo": str(d.get("cargo") or "")[:120],
                    "area": str(d.get("area") or "")[:40],
                    "linkedin_url": li if (isinstance(li, str) and li.startswith("http")) else None,
                    "fonte": str(d.get("fonte") or "")[:300],
                })
            return {"decisores": out, "fontes": data.get("fontes") or []}
        except json.JSONDecodeError as e:
            last_err = f"json_decode: {e}"
            logger.warning("find_decisores tentativa %d: %s", attempt + 1, e)
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            logger.warning("find_decisores tentativa %d: %s", attempt + 1, e)
            time.sleep(5 * (attempt + 1))

    return {"erro": last_err, "decisores": []}


def find_and_save_decisores(lead_id: int, store: "Store | None" = None, limit: int = 12) -> dict[str, Any]:
    """Busca decisores na web e salva a lista em payload_json['decisores_extra']."""
    store = store or Store()
    with store.conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        return {"erro": f"lead {lead_id} não encontrado", "decisores": []}
    lead = dict(row)
    res = find_decisores_via_web(lead, limit=limit)
    decisores = res.get("decisores") or []
    if decisores:
        with store.conn() as c:
            payload = lead.get("payload_json") or "{}"
            pd = json.loads(payload) if isinstance(payload, str) else (payload or {})
            pd["decisores_extra"] = decisores
            c.execute(
                "UPDATE leads SET payload_json=? WHERE id=?",
                (json.dumps(pd, ensure_ascii=False, default=str), lead_id),
            )
        store.log_event("decisores_busca", {"lead_id": lead_id, "n": len(decisores)})
    return res


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
    last_err: str | None = None
    text = ""

    # Retry com backoff — Google Search grounding tem rate limit
    for attempt in range(3):
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=SYSTEM_ENRICHER,
                temperature=0.0,
                max_output_tokens=8192,
                # Sem response_mime_type — incompatível com google_search
            )
            response = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt,
                config=config,
            )
            text = (response.text or "").strip()

            if not text:
                last_err = "resposta vazia (possível rate limit do google_search)"
                logger.warning("Tentativa %d: %s", attempt + 1, last_err)
                time.sleep(8 * (attempt + 1))
                continue

            # Extrai JSON do texto (pode vir com markdown ou texto explicativo)
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:].strip()
                text = text.rstrip("`").strip()
            else:
                # Procura primeiro { ... } válido
                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    text = m.group(0)

            # strict=False tolera caracteres de controle literais (\n, tabs)
            # que o Gemini às vezes injeta dentro de strings JSON.
            return json.loads(text, strict=False)

        except json.JSONDecodeError as e:
            last_err = f"json_decode: {e}"
            logger.warning("Tentativa %d falhou parsing: %s · texto: %s", attempt + 1, e, text[:300])
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            logger.warning("Tentativa %d falhou: %s", attempt + 1, e)
            time.sleep(5 * (attempt + 1))

    return {"erro": last_err, "raw": text[:500] if text else ""}


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
        email = (
            primeiro.get("email")
            or lead.get("email_provavel")
            or enrichment.get("email_institucional")
        )
        updates = {
            "decisor_nome": primeiro.get("nome"),
            "decisor_cargo": primeiro.get("cargo"),
            "decisor_linkedin": primeiro.get("linkedin_url"),
            "email_provavel": email,
            "telefone": lead.get("telefone") or enrichment.get("telefone_institucional"),
            "observacoes": enrichment.get("oportunidade_resumida"),
        }
        # Valida e-mail (MX) quando houver — preenche email_validado (0/1)
        if email:
            updates["email_validado"] = int(validate_email(email)["mx_ok"])

        with store.conn() as c:
            # Persiste só campos com valor (não sobrescreve com None/"").
            # email_validado=0 é significativo e NÃO deve ser descartado.
            sets_items = [(k, v) for k, v in updates.items() if v is not None and v != ""]
            sets = ", ".join(f"{k}=?" for k, _ in sets_items)
            vals = [v for _, v in sets_items]
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


def enrich_top_n(
    n: int = 50,
    min_score: int = 60,
    store: Store | None = None,
    delay_seconds: float = 4.0,
    vertical: str | None = None,
) -> dict[str, Any]:
    """Enriquece os top N leads do DB com delay entre chamadas (anti rate-limit)."""
    store = store or Store()
    leads = store.all_leads(vertical=vertical, min_score=min_score, limit=n)
    results = {"enriquecidos": 0, "erros": 0, "detalhes": []}

    for i, lead in enumerate(leads):
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
                logger.info("[%d/%d] %s · %d decisores · vendor: %s",
                            i + 1, len(leads), lead["empresa"][:40],
                            len(e.get("decisores", [])), e.get("vendor_comunicacao_atual") or "—")
            else:
                results["erros"] += 1
        except Exception as ex:
            logger.exception("Falha no lead %s: %s", lead.get("empresa"), ex)
            results["erros"] += 1

        # Delay anti rate-limit do google_search
        if i < len(leads) - 1:
            time.sleep(delay_seconds)

    return results


def validate_existing_emails(store: Store | None = None, limit: int = 10000) -> dict[str, Any]:
    """Backfill: valida (MX) e-mails já gravados que estão sem email_validado.

    Cobre leads que foram coletados antes da validação automática no enrichment.
    Determinístico e gratuito (só DNS) — não chama Gemini.
    """
    store = store or Store()
    with store.conn() as c:
        rows = c.execute(
            "SELECT id, email_provavel FROM leads "
            "WHERE email_provavel IS NOT NULL AND email_provavel != '' "
            "AND email_validado IS NULL LIMIT ?",
            (limit,),
        ).fetchall()

    mx_ok = 0
    for r in rows:
        valido = int(validate_email(r["email_provavel"])["mx_ok"])
        mx_ok += valido
        with store.conn() as c:
            c.execute("UPDATE leads SET email_validado=? WHERE id=?", (valido, r["id"]))

    logger.info("Validação de e-mails: %d processados, %d com MX ok", len(rows), mx_ok)
    return {"processados": len(rows), "mx_ok": mx_ok, "total_candidatos": len(rows)}
