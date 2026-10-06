"""Entrada central: identifica conteúdo, extrai e normaliza sem usar IA externa."""
from io import BytesIO
from pathlib import Path
import zipfile
from .normalizer import normalizar

FORMATOS = {".pdf":"pdf", ".docx":"docx", ".doc":"doc", ".xlsx":"xlsx", ".xls":"xls",
    ".csv":"csv", ".tsv":"tsv", ".png":"imagem", ".jpg":"imagem", ".jpeg":"imagem",
    ".html":"html", ".htm":"html", ".json":"json"}

def identificar_formato(nome, conteudo):
    ext = Path(nome).suffix.lower()
    if ext not in FORMATOS:
        raise ValueError("Use PDF, DOC/DOCX, XLS/XLSX, CSV/TSV, HTML, JSON ou PNG/JPG.")
    if not conteudo or len(conteudo) > 16*1024*1024:
        raise ValueError("Envie um arquivo não vazio de até 16 MB.")
    if ext == ".pdf" and b"%PDF-" not in conteudo[:1024]:
        raise ValueError("O conteúdo não corresponde a um PDF válido.")
    if ext in {".xlsx", ".docx"}:
        try:
            with zipfile.ZipFile(BytesIO(conteudo)) as z:
                infos = z.infolist()
                if len(infos)>2000 or sum(i.file_size for i in infos)>100*1024*1024:
                    raise ValueError("Documento compactado muito extenso; envie um recorte.")
                prefixo = "xl/" if ext == ".xlsx" else "word/"
                if not any(i.filename.startswith(prefixo) for i in infos):
                    raise ValueError("O conteúdo não corresponde ao formato informado.")
        except zipfile.BadZipFile as erro:
            raise ValueError("Documento compactado inválido; envie outro arquivo.") from erro
    if ext in {".png", ".jpg", ".jpeg"}:
        assinatura = b"\x89PNG\r\n\x1a\n" if ext == ".png" else b"\xff\xd8"
        if not conteudo.startswith(assinatura):
            raise ValueError("O conteúdo não corresponde à imagem informada.")
    return FORMATOS[ext]

def processar_documento(nome, conteudo):
    formato = identificar_formato(nome, conteudo)
    # Importação tardia evita ciclo com os organizadores salariais existentes.
    from src.salarial.revisao_service import _extrair_para_revisao
    try:
        extraido = _extrair_para_revisao(nome, conteudo)
    except (UnicodeDecodeError, zipfile.BadZipFile) as erro:
        raise ValueError("Documento inválido ou com codificação ilegível; envie outro arquivo.") from erro
    return normalizar(extraido, nome, conteudo, formato)
