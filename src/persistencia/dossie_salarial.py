"""Persistência local e auditável dos documentos salariais originais."""

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata
from zoneinfo import ZoneInfo


class DossieSalarialStore:
    def __init__(self, diretorio="data/raw/salarios"):
        self.diretorio = Path(diretorio)

    @staticmethod
    def _segmento(valor):
        normalizado = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
        seguro = re.sub(r"[^a-zA-Z0-9_-]+", "-", normalizado).strip("-").lower()
        if not seguro:
            raise ValueError("Identificador inválido para armazenamento.")
        return seguro

    @staticmethod
    def _nome_armazenado(categoria, nome_original):
        extensao = Path(nome_original).suffix.lower()
        base = DossieSalarialStore._segmento(Path(nome_original).stem)[:80]
        return f"{categoria}--{base}{extensao}"

    def salvar(self, metadados, arquivos):
        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
        assinatura = sha256(
            "".join(item["sha256"] for item in arquivos).encode("ascii")
        ).hexdigest()[:12]
        dossie_id = f"{agora:%Y%m%dT%H%M%S%f}-{assinatura}"
        relativo = (
            Path(self._segmento(f"{metadados['municipio']}-{metadados['uf']}"))
            / str(metadados["ano_referencia"])
            / dossie_id
        )
        destino = self.diretorio / relativo
        destino.mkdir(parents=True, exist_ok=False)

        registros = []
        for item in arquivos:
            nome = self._nome_armazenado(item["categoria"], item["nome_original"])
            (destino / nome).write_bytes(item["conteudo"])
            registros.append({chave: valor for chave, valor in item.items() if chave != "conteudo"} | {"nome_armazenado": nome})

        presentes = {item["categoria"] for item in registros}
        ausentes = [
            categoria
            for categoria in ("plano_carreira", "ato_reajuste")
            if categoria not in presentes
        ]
        manifest = {
            "schema_version": 1,
            "dossie_id": dossie_id,
            **metadados,
            "registrado_em": agora.isoformat(timespec="seconds"),
            "status": "completo_para_triagem" if not ausentes else "parcial_para_triagem",
            "itens_recomendados_ausentes": ausentes,
            "arquivos": registros,
            "proxima_etapa": "Confirmar vigência e selecionar somente a tabela do magistério antes de estruturar os dados.",
            "localizacao_relativa": str(Path("data/raw/salarios") / relativo).replace("\\", "/"),
        }
        (destino / "manifesto.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return manifest
