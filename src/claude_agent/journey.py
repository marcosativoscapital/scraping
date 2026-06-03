"""Gera a 'jornada de contato ideal' de um lead via Gemini — cadência multicanal CPaaS.

Saída estruturada: como falar (persona/tom/ângulo/gatilho/evitar), ordem de canais e
passo a passo (D+0, D+2…) com objetivo, ação e exemplo por toque.
"""

from __future__ import annotations

from typing import Any

from .client import GeminiClient
from .personalize import SYSTEM_PERSONALIZER

# Campos do lead que ajudam a personalizar a jornada
_LEAD_FIELDS = (
    "empresa", "razao_social", "vertical", "porte_estimado", "site",
    "decisor_nome", "decisor_cargo", "score_icp", "recomendacao",
    "gatilho_personalizado", "observacoes", "telefone", "email_provavel",
)

JOURNEY_SCHEMA = """{
  "resumo": "1 frase explicando a estratégia desta jornada para a empresa",
  "como_falar": {
    "persona": "Marketing|Tech|Ops/CFO",
    "tom": "como a abordagem deve soar",
    "angulo": "ângulo/dor central a explorar",
    "gatilho": "gatilho real ou contexto a citar",
    "evitar": "o que NÃO fazer com essa empresa"
  },
  "canais": ["linkedin", "email", "whatsapp", "ligacao"],
  "passos": [
    {"dia": "D+0", "canal": "linkedin", "objetivo": "objetivo do toque", "acao": "o que fazer", "exemplo": "abertura/linha de exemplo curta"}
  ],
  "objecao_provavel": "a objeção mais provável dessa empresa",
  "resposta_objecao": "como contornar"
}"""


def generate_journey(client: GeminiClient, lead: dict[str, Any]) -> dict[str, Any]:
    """Gera a jornada de contato ideal (multicanal) para um lead."""
    info = "\n".join(f"- {k}: {lead[k]}" for k in _LEAD_FIELDS if lead.get(k))

    prompt = f"""Monte a JORNADA DE CONTATO IDEAL (cadência multicanal de prospecção outbound)
para abordar esta empresa e convertê-la em reunião para o Solvefy CPaaS:

{info}

Regras:
- 4 a 6 passos ao longo de ~2 semanas.
- Escolha a MELHOR ordem de canais (LinkedIn, e-mail, WhatsApp, ligação, SMS) para a
  persona/porte desta empresa.
- Cada passo: dia relativo (D+0, D+2…), canal, objetivo, ação concreta e um exemplo curto.
- Defina COMO FALAR (persona dominante, tom, ângulo/dor, gatilho a citar, o que evitar).
- Aponte a objeção mais provável e como contornar.
- Específico para a vertical e o porte. Português brasileiro, peer-to-peer, sem buzzword."""

    data = client.extract_json(prompt, system=SYSTEM_PERSONALIZER, schema_hint=JOURNEY_SCHEMA)
    return _validate(data)


def _s(v: Any, n: int) -> str:
    return str(v if v is not None else "")[:n]


def _validate(d: Any) -> dict[str, Any]:
    """Coerção defensiva pós-LLM (mesmo espírito de scorer/classifier)."""
    if not isinstance(d, dict):
        return {"erro": "resposta inválida do modelo"}

    cf = d.get("como_falar") if isinstance(d.get("como_falar"), dict) else {}

    canais_raw = d.get("canais") if isinstance(d.get("canais"), list) else []
    canais = [_s(c, 20).lower().strip() for c in canais_raw if c][:6]

    passos_raw = d.get("passos") if isinstance(d.get("passos"), list) else []
    passos = []
    for p in passos_raw[:8]:
        if not isinstance(p, dict):
            continue
        passos.append({
            "dia": _s(p.get("dia"), 12),
            "canal": _s(p.get("canal"), 20).lower().strip(),
            "objetivo": _s(p.get("objetivo"), 200),
            "acao": _s(p.get("acao"), 400),
            "exemplo": _s(p.get("exemplo"), 400),
        })

    return {
        "resumo": _s(d.get("resumo"), 300),
        "como_falar": {
            "persona": _s(cf.get("persona"), 40),
            "tom": _s(cf.get("tom"), 200),
            "angulo": _s(cf.get("angulo"), 200),
            "gatilho": _s(cf.get("gatilho"), 200),
            "evitar": _s(cf.get("evitar"), 200),
        },
        "canais": canais,
        "passos": passos,
        "objecao_provavel": _s(d.get("objecao_provavel"), 200),
        "resposta_objecao": _s(d.get("resposta_objecao"), 300),
    }
