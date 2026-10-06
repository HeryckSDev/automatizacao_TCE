"""Compatibilidade com chamadas da v0.9.0; processadores ficam separados por formato."""
import shutil, subprocess
from src.document_processor.pdf_processor import ler_pdf
from src.document_processor.docx_processor import ler_word
from src.document_processor.xls_processor import ler_xls
from src.document_processor.image_processor import ler_imagem
from src.document_processor.ocr_processor import ocr_pagina
