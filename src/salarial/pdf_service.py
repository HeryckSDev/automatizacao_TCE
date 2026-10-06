"""Inspeção segura de PDFs antes de definir as regras de extração salarial."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


LIMITE_PDF_BYTES = 15 * 1024 * 1024
LIMITE_PREVIA_CARACTERES = 4000


def inspecionar_pdf(nome_arquivo, conteudo):
    if not nome_arquivo or not nome_arquivo.lower().endswith(".pdf"):
        raise ValueError("Envie um arquivo PDF.")
    if not conteudo:
        raise ValueError("O PDF enviado está vazio.")
    if len(conteudo) > LIMITE_PDF_BYTES:
        raise ValueError("O PDF excede o limite de 15 MB.")

    try:
        leitor = PdfReader(BytesIO(conteudo))
    except (PdfReadError, OSError, ValueError) as erro:
        raise ValueError("O arquivo não pôde ser interpretado como PDF.") from erro

    textos = []
    paginas_com_texto = 0
    for pagina in leitor.pages:
        texto = (pagina.extract_text() or "").strip()
        if texto:
            paginas_com_texto += 1
            textos.append(texto)

    texto_completo = "\n\n".join(textos)
    return {
        "nome_arquivo": nome_arquivo,
        "tamanho_bytes": len(conteudo),
        "quantidade_paginas": len(leitor.pages),
        "paginas_com_texto": paginas_com_texto,
        "quantidade_caracteres": len(texto_completo),
        "texto_extraivel": bool(texto_completo),
        "provavelmente_escaneado": bool(leitor.pages) and paginas_com_texto == 0,
        "previa_texto": texto_completo[:LIMITE_PREVIA_CARACTERES],
        "status": "inspecionado_sem_regras_salariais",
    }
