"""Contrato comum de documento, sem converter salário em indicador fiscal."""
from copy import deepcopy
from hashlib import sha256
from src.salarial.analise_service import _decimal

def normalizar(resultado, nome, conteudo, formato):
    impressao = sha256(conteudo).hexdigest()
    saida = deepcopy(resultado)
    candidatos = []
    pendencias = list(saida.get("pendencias") or [])
    for indice, candidato in enumerate(saida.get("candidatos") or [], 1):
        try:
            niveis = candidato.get("niveis")
            if not isinstance(niveis, list) or not niveis:
                raise ValueError("Tabela sem níveis salariais.")
            quantidade_classes = None
            codigos = set()
            for nivel in niveis:
                codigo = str(nivel.get("codigo", "")).strip().upper()
                valores = nivel.get("valores")
                if not codigo or codigo in codigos:
                    raise ValueError("Níveis ausentes ou duplicados.")
                codigos.add(codigo)
                if not isinstance(valores, list) or not valores:
                    raise ValueError("Nível sem vencimentos.")
                if quantidade_classes is not None and len(valores) != quantidade_classes:
                    raise ValueError("Classes incompletas entre níveis.")
                quantidade_classes = len(valores)
                if any(_decimal(v, "Vencimento") <= 0 for v in valores):
                    raise ValueError("Vencimento deve ser positivo.")
            classes = candidato.get("classes")
            if classes is not None:
                if not isinstance(classes, list) or len(classes) != len(niveis[0]["valores"]) or len(set(map(str, classes))) != len(classes):
                    raise ValueError("Classes duplicadas ou incompatíveis com os vencimentos.")
            candidato["rastreabilidade"] = {"arquivo": nome, "sha256": impressao,
                "formato": formato, "localizacao": candidato.get("arquivo_fonte", nome),
                "metodo": candidato.get("metodo_extracao", "ocr" if candidato.get("origem_ocr") else "estruturado"),
                "revisao_obrigatoria": True}
            candidatos.append(candidato)
        except (ValueError, TypeError, KeyError, AttributeError) as erro:
            if formato == "json":
                raise ValueError(f"Tabela {indice} inválida: {erro}") from erro
            titulo = candidato.get("profissao", "") if isinstance(candidato, dict) else ""
            pendencias.append(f"Tabela {indice} ({titulo}) não incorporada: {erro}")
    saida.update(candidatos=candidatos, pendencias=list(dict.fromkeys(pendencias)))
    saida["documento_normalizado"] = {"versao_contrato": 1, "tipo_documento": "tabela_salarial" if candidatos else "nao_classificado",
        "formato": formato, "fonte": {"tipo": "documento_enviado", "arquivo": nome, "sha256": impressao},
        "status": "requer_revisao" if candidatos else "nao_reconhecido", "quantidade_tabelas": len(candidatos),
        "integracao_fiscal": False}
    return saida
