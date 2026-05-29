"""Carrega e organiza a biblioteca de playbooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config_playbooks.yaml")


@dataclass
class Playbook:
    id: str
    nome: str
    categoria: str
    gatilho: str
    sinais_para_aplicar: list[str]
    decisor_primario: str
    decisor_secundario: str
    dor_alvo: str
    mensagem_central: str
    sequencia: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "categoria": self.categoria,
            "gatilho": self.gatilho,
            "sinais_para_aplicar": self.sinais_para_aplicar,
            "decisor_primario": self.decisor_primario,
            "decisor_secundario": self.decisor_secundario,
            "dor_alvo": self.dor_alvo,
            "mensagem_central": self.mensagem_central,
            "sequencia": self.sequencia,
        }

    def summary_for_llm(self) -> str:
        """Resumo curto para o selector Gemini economizar tokens."""
        return (
            f"[{self.id}] {self.nome} ({self.categoria})\n"
            f"  Gatilho: {self.gatilho}\n"
            f"  Sinais: {'; '.join(self.sinais_para_aplicar[:3])}\n"
            f"  Decisor primário: {self.decisor_primario}\n"
            f"  Dor: {self.dor_alvo}"
        )


@dataclass
class Objecao:
    id: str
    titulo: str
    resposta: str


class PlaybookLibrary:
    """Biblioteca singleton de playbooks + objeções."""

    def __init__(self, playbooks: list[Playbook], objecoes: list[Objecao]):
        self.playbooks = playbooks
        self.by_id: dict[str, Playbook] = {p.id: p for p in playbooks}
        self.objecoes = objecoes
        self.objecoes_by_id: dict[str, Objecao] = {o.id: o for o in objecoes}

    def all(self) -> list[Playbook]:
        return list(self.playbooks)

    def get(self, playbook_id: str) -> Playbook | None:
        return self.by_id.get(playbook_id)

    def for_categoria(self, categoria: str) -> list[Playbook]:
        return [p for p in self.playbooks if p.categoria == categoria]

    def for_vertical(self, vertical: str) -> list[Playbook]:
        """Playbooks específicos da vertical + universais."""
        result = []
        for p in self.playbooks:
            if p.categoria.startswith("vertical_"):
                if p.categoria == f"vertical_{vertical}":
                    result.append(p)
            else:
                result.append(p)
        return result

    def summary_for_llm(self) -> str:
        return "\n\n".join(p.summary_for_llm() for p in self.playbooks)


def load_playbooks(path: Path | str = DEFAULT_CONFIG_PATH) -> PlaybookLibrary:
    """Carrega playbooks e objeções do YAML."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config de playbooks não encontrado: {p}")

    data = yaml.safe_load(p.read_text(encoding="utf-8"))

    playbooks = [
        Playbook(
            id=pb["id"],
            nome=pb["nome"],
            categoria=pb["categoria"],
            gatilho=pb["gatilho"],
            sinais_para_aplicar=pb.get("sinais_para_aplicar", []),
            decisor_primario=pb["decisor_primario"],
            decisor_secundario=pb.get("decisor_secundario", ""),
            dor_alvo=pb["dor_alvo"],
            mensagem_central=pb["mensagem_central"],
            sequencia=pb.get("sequencia", []),
        )
        for pb in data.get("playbooks", [])
    ]

    objecoes = [
        Objecao(id=k, titulo=v["titulo"], resposta=v["resposta"])
        for k, v in (data.get("objecoes") or {}).items()
    ]

    return PlaybookLibrary(playbooks, objecoes)


# Singleton lazy load
_library: PlaybookLibrary | None = None


def get_library() -> PlaybookLibrary:
    global _library
    if _library is None:
        _library = load_playbooks()
    return _library
