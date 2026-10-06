from io import BytesIO
from src.salarial.leitor_geral import ler_texto
from .ocr_processor import ocr_pagina

def ler_imagem(nome,conteudo,organizar):
    from PIL import Image
    from types import SimpleNamespace
    try:im=Image.open(BytesIO(conteudo))
    except Exception as erro:raise ValueError('Imagem inválida; envie PNG/JPG legível.') from erro
    if im.width*im.height>20000000:raise ValueError('Imagem extensa: envie um recorte de até 20 megapixels.')
    class Pagina:
        def to_image(self,resolution):return SimpleNamespace(original=im.convert('RGB'))
    texto=ocr_pagina(Pagina())
    d,p=ler_texto(texto,nome,organizar)
    for c in d:c['origem_ocr']=True;c['avisos_importacao'].append('Imagem lida por OCR: confira cada célula no original.')
    p.append('OCR de imagem: confirmação dos valores obrigatória; leitura pode confundir letras e dígitos.')
    return d,texto,p

