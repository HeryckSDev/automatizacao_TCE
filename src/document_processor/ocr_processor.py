"""OCR local opcional, com tempo e resolução limitados."""
from pathlib import Path
import shutil, subprocess, tempfile

def ocr_pagina(page):
    exe=shutil.which('tesseract')
    if not exe:raise ValueError('PDF imagem: instale Tesseract OCR ou envie PDF com texto/Excel.')
    with tempfile.TemporaryDirectory(prefix='jornada-ocr-') as tmp:
        p=Path(tmp)/'pagina.png'
        width=float(getattr(page,'width',612));height=float(getattr(page,'height',792))
        resolution=min(180,72*2800/max(width,1),72*4000/max(height,1))
        if resolution<36:raise ValueError('Página muito extensa para OCR; envie um recorte legível.')
        image=page.to_image(resolution=resolution).original
        image.thumbnail((2800,4000))
        image.convert('RGB').save(p)
        langs=subprocess.run([exe,'--list-langs'],capture_output=True,text=True,timeout=10).stdout.splitlines()
        lang='por' if 'por' in langs else 'eng'
        r=subprocess.run([exe,str(p),'stdout','-l',lang,'--psm','6'],capture_output=True,text=True,timeout=45)
        if r.returncode:raise ValueError('OCR não conseguiu ler a página; transcreva na revisão.')
        return r.stdout

