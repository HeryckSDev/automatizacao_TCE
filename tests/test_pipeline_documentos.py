"""Casos sintéticos de contrato, seleção de leitor e falha segura."""
import unittest
from unittest.mock import patch, MagicMock
from hashlib import sha256
from src.document_processor import processar_documento
from src.document_processor.processor import identificar_formato
from src.document_processor.pdf_processor import ler_pdf
from src.salarial.revisao_service import organizar_registros

MATRIZ = [['Nível','A','B'],['I','1200,00','1260,00'],['II','1500,00','1575,00']]
class PipelineTest(unittest.TestCase):
    def test_normaliza_csv_sem_inventar_indicador_fiscal(self):
        b=b'Nivel;A;B\nI;1200,00;1260,00\nII;1500,00;1575,00'
        d=processar_documento('carreira.csv',b)
        self.assertEqual(d['documento_normalizado']['tipo_documento'],'tabela_salarial')
        self.assertFalse(d['documento_normalizado']['integracao_fiscal'])
        self.assertEqual(d['candidatos'][0]['rastreabilidade']['sha256'],sha256(b).hexdigest())
        self.assertEqual(d['candidatos'][0]['niveis'][1]['valores'],[1500,1575])
    def test_extensao_nao_substitui_assinatura(self):
        for n in ['fake.pdf','fake.png','fake.docx','fake.xlsx']:
            with self.subTest(n=n),self.assertRaises(ValueError): identificar_formato(n,b'nao e documento')
    def test_tabela_duplicada_no_json_rejeitada(self):
        import json
        d=processar_documento('a.csv',b'Nivel;A;B\nI;1200,00;1260,00')['candidatos'][0]
        d['classes']=['A','A']
        with self.assertRaisesRegex(ValueError,'Classes duplicadas'):
            processar_documento('a.json',json.dumps(d).encode())
    def pagina(self, texto='', imagens=()):
        page=MagicMock();page.extract_text.return_value=texto;page.extract_tables.return_value=[];page.images=imagens
        return page
    def documento(self,page):
        doc=MagicMock();doc.__enter__.return_value.pages=[page];return doc
    def test_prioridade_de_tabela_nativa_sobre_texto_embaralhado(self):
        page=self.pagina('Nivel A B\nI 9999,00 9999,00');page.extract_tables.return_value=[MATRIZ]
        with patch('src.document_processor.pdf_processor.pdfplumber.open',return_value=self.documento(page)),patch('src.document_processor.pdf_processor.ocr_pagina') as ocr:
            d,t,p=ler_pdf('a.pdf',b'a',organizar_registros)
        self.assertEqual(d[0]['niveis'][0]['valores'],[1200,1260]);ocr.assert_not_called()
        self.assertEqual(d[0]['metodo_extracao'],'tabela_nativa')
    def test_cabecalho_textual_e_tabela_imagem_tentam_ocr(self):
        page=self.pagina('Prefeitura Municipal: relatório com texto de cabeçalho selecionável', [{}])
        with patch('src.document_processor.pdf_processor.pdfplumber.open',return_value=self.documento(page)),patch('src.document_processor.pdf_processor.ocr_pagina',return_value='Nivel A B\nI 1200,00 1260,00\nII 1500,00 1575,00') as ocr:
            d,t,p=ler_pdf('a.pdf',b'a',organizar_registros)
        self.assertEqual(len(d),1);self.assertTrue(d[0]['origem_ocr']);ocr.assert_called_once()
    def test_tabela_incompleta_nao_recebe_fallback_que_oculta_erro(self):
        page=self.pagina('Nivel A B\nI 1200,00 1260,00',[{}]);page.extract_tables.return_value=[[['Nivel','A','B'],['I','1200,00',None]]]
        with patch('src.document_processor.pdf_processor.pdfplumber.open',return_value=self.documento(page)),patch('src.document_processor.pdf_processor.ocr_pagina') as ocr:
            d,t,p=ler_pdf('a.pdf',b'a',organizar_registros)
        self.assertFalse(d);self.assertTrue(p);ocr.assert_not_called()
    def test_vb_total_separados(self):
        from src.document_processor.components import ler_componentes
        t=[['Classe','Nível','VB','Total'],['A','1','2000,00','2400,00'],[None,'2','2100,00','2520,00']]
        d,p=ler_componentes([t],'a',organizar_registros,'')
        self.assertEqual(len(d),2);self.assertEqual(d[0]['niveis'][0]['valores'],[2000,2100])
        self.assertEqual(d[1]['niveis'][0]['valores'],[2400,2520]);self.assertTrue(d[1]['pspn_inaplicavel']);self.assertFalse(d[0]['pspn_inaplicavel'])
    def test_componentes_incompletos_nao_salvam_meia_tabela(self):
        from src.document_processor.components import ler_componentes
        d,p=ler_componentes([[['Classe','Nível','VB','Total'],['A','1','2000,00',None]]],'a',organizar_registros,'')
        self.assertFalse(d);self.assertTrue(p)

    def test_tabela_componentes_nao_oculta_matriz_da_mesma_pagina(self):
        from src.document_processor.table_processor import ler_tabelas
        t=[['Classe','Nível','VB','Total'],['A','1','2000,00','2400,00']]
        d,p=ler_tabelas([t,MATRIZ],'a',organizar_registros,'')
        self.assertEqual(len(d),3)
        self.assertEqual(d[-1]['niveis'][1]['valores'],[1500,1575])

    def test_json_fiscal_nao_e_interpretado_como_salario(self):
        with self.assertRaisesRegex(ValueError,'fiscal genérico'):
            processar_documento('fiscal.json',b'{"tipo_documento":"relatorio_fiscal","dados":{"rcl":1000}}')

class PipelineImagemTest(unittest.TestCase):
    @unittest.skipUnless(__import__('shutil').which('tesseract'),'OCR opcional não instalado')
    def test_png_e_jpeg_sinteticos(self):
        from PIL import Image,ImageDraw,ImageFont
        from pathlib import Path
        from io import BytesIO
        im=Image.new('RGB',(1200,450),'white');draw=ImageDraw.Draw(im)
        font=ImageFont.truetype(str(Path(__file__).resolve().parents[1]/'assets/fonts/DejaVuSans.ttf'),35)
        for y,row in [(40,['Nivel','A','B']),(130,['I','1200,00','1260,00']),(220,['II','1500,00','1575,00'])]:
            for x,v in zip([70,450,850],row):draw.text((x,y),v,font=font,fill='black')
        for formato,ext in [('PNG','png'),('JPEG','jpg')]:
            with self.subTest(formato=formato):
                b=BytesIO();im.save(b,format=formato)
                r=processar_documento('sintetico.'+ext,b.getvalue())
                self.assertEqual(len(r['candidatos']),1,r['pendencias'])
                self.assertEqual(r['candidatos'][0]['niveis'][1]['valores'],[1500,1575])
                self.assertEqual(r['candidatos'][0]['rastreabilidade']['metodo'],'ocr')
