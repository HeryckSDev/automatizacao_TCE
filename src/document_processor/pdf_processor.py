"""PDF híbrido por página: tabelas nativas, texto e OCR quando necessário."""
from io import BytesIO
import subprocess
import pdfplumber
from src.salarial.leitor_geral import ler_matrizes, ler_texto
from .table_processor import ler_tabelas
from .ocr_processor import ocr_pagina

def ler_pdf(nome, conteudo, organizar, ignorar_paginas=()):
    out, pend, textos = [], [], []
    with pdfplumber.open(BytesIO(conteudo)) as doc:
        if len(doc.pages)>300: raise ValueError("Envie recorte de até 300 páginas.")
        ocr_count = 0
        for i, page in enumerate(doc.pages, 1):
            if i in ignorar_paginas: continue
            text = page.extract_text() or ""
            local = f"{nome}, página {i}"
            candidatos, notas = [], []
            metodo = "tabela_nativa"
            try:
                tables = page.extract_tables()
                candidatos, notas = ler_tabelas(tables, local, organizar, text)
            except (ValueError, TypeError) as erro:
                notas.append(f"Página {i}: tabela inválida: {erro}")
            if not candidatos and not notas:
                metodo = "texto_nativo"
                candidatos, notas = ler_texto(text, local, organizar)
            # Texto de cabeçalho pode esconder uma tabela rasterizada. Não basta testar texto vazio.
            usar_ocr = not candidatos and not notas and (len(text.strip())<20 or bool(page.images))
            if usar_ocr:
                ocr_count += 1
                if ocr_count>10:
                    notas.append(f"Página {i}: limite de 10 páginas OCR por arquivo; envie um recorte.")
                else:
                    try:
                        texto_ocr = ocr_pagina(page)
                        text += "\n" + texto_ocr
                        candidatos, notas = ler_texto(texto_ocr, local, organizar)
                        metodo = "ocr"
                        notas.append(f"Página {i}: OCR aplicado; confira cada valor no original. Não há garantia de acurácia.")
                        for c in candidatos:
                            c["origem_ocr"] = True
                            c["avisos_importacao"].append("Valores lidos por OCR: revisão de todas as células obrigatória.")
                    except (ValueError, subprocess.TimeoutExpired) as erro:
                        notas.append(f"Página {i}: {erro}")
            for c in candidatos: c["metodo_extracao"] = metodo
            textos.append(f"PÁGINA {i}\n{text}")
            out.extend(candidatos); pend.extend(notas)
            if not candidatos:
                pend.append(f"Página {i}: não foi reconhecida uma tabela completa; consulte a revisão manual.")
    return out, "\n".join(textos), pend
