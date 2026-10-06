"""Amostras salariais preservadas para demonstração e testes."""

import json
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
AMOSTRA_CAFEZAL_2026 = RAIZ_PROJETO / "data/processed/cafezal_do_sul_2026.json"


def carregar_cafezal_2026():
    """Retorna uma cópia dos dados transcritos do Anexo A da LC 064/2026."""

    return json.loads(AMOSTRA_CAFEZAL_2026.read_text(encoding="utf-8"))
