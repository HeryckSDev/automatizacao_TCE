"""Armazena respostas públicas do TCE para auditoria e reprodução."""

from pathlib import Path
import re
import hashlib
from datetime import datetime, timezone
from uuid import uuid4


class ArquivoBrutoStore:
    def __init__(self, diretorio="data/raw/tce"):
        self.diretorio = Path(diretorio)

    @staticmethod
    def _segmento(valor):
        seguro = re.sub(r"[^a-zA-Z0-9_-]", "-", str(valor)).strip("-")
        if not seguro:
            raise ValueError("Identificador inválido para armazenamento.")
        return seguro

    def salvar(self, municipio_id, entidade_id, ano, relatorio_id, conteudo):
        destino = (
            self.diretorio
            / self._segmento(municipio_id)
            / self._segmento(entidade_id)
            / self._segmento(ano)
        )
        destino.mkdir(parents=True, exist_ok=True)
        arquivo = destino / f"relatorio-{self._segmento(relatorio_id)}.csv"
        versoes = destino / "versoes"
        versoes.mkdir(exist_ok=True)
        digest = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
        instante = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        copia = versoes / f"{arquivo.stem}-{instante}-{digest[:12]}-{uuid4().hex[:8]}.csv"
        with copia.open("x", encoding="utf-8") as original:
            original.write(conteudo)
        temporario = destino / f".{arquivo.stem}-{uuid4().hex}.tmp"
        try:
            temporario.write_text(conteudo, encoding="utf-8")
            temporario.replace(arquivo)
        finally:
            temporario.unlink(missing_ok=True)
        return arquivo
