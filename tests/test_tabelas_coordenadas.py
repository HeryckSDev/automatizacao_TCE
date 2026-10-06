import unittest
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table,TableStyle
from reportlab.lib import colors
from src.salarial.revisao_service import extrair_para_revisao
from src.salarial.tabelas_coordenadas import candidato_registros,registro
from src.salarial.revisao_service import organizar_registros

class TabelasCoordenadasTest(unittest.TestCase):
    def test_html_preserva_eixos_sem_inventar_cargo_jornada(self):
        html=b'<h4>Data Refer\xc3\xaancia: 07/09/2026</h4><h4>Grupo salarial</h4><table><tr><th>Classe</th><th>N\xc3\xadvel</th><th>Valor</th></tr><tr><td>A</td><td>1</td><td>R$ 2.000,00</td></tr><tr><td>A</td><td>2</td><td>R$ 2.040,00</td></tr></table>'
        r=extrair_para_revisao('tabela.html',html);self.assertEqual(len(r['candidatos']),1)
        d=r['candidatos'][0];self.assertEqual(d['niveis'][0]['valores'],[2000,2040]);self.assertNotIn('profissao',d);self.assertNotIn('jornada_semanal',d);self.assertTrue(r['revisao_obrigatoria'])
    def test_html_catalogo_nao_vira_salario(self):
        r=extrair_para_revisao('leis.html',b'<table><tr><td>Lei 999/2026</td><td>Plano salarial</td></tr></table>')
        self.assertEqual(r['candidatos'],[]);self.assertTrue(r['pendencias'])
    def test_blocos_numericos_ordenados_sem_perder_referencias(self):
        d=candidato_registros([registro('I',1,'100,00'),registro('I',65,'165,00'),registro('I',2,'102,00')],'teste.pdf',organizar_registros)
        self.assertEqual(d['classes'],['1','2','65']);self.assertEqual(d['niveis'][0]['valores'],[100,102,165])
    def test_pdf_coluna_referencia_valor_com_bordas(self):
        out=BytesIO();c=canvas.Canvas(out,pagesize=A4)
        c.drawString(25,800,'PREFEITURA MUNICIPAL DE CURITIBA');c.drawString(25,780,'TABELA SALARIAL - JANEIRO 2026');c.drawString(25,760,'ANEXO - B1')
        t=Table([['Parte Permanente\nNível I',''],['Referência','Valor'],['I','R$ 2.180,44'],['II','R$ 2.241,49']],colWidths=[130,120],rowHeights=[30,20,20,20]);t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),1,colors.black)]));t.wrapOn(c,250,200);t.drawOn(c,25,600);c.save()
        r=extrair_para_revisao('synthetic.pdf',out.getvalue());self.assertEqual(len(r['candidatos']),1);self.assertEqual(r['candidatos'][0]['niveis'][0]['valores'],[2180.44,2241.49])
    def test_matriz_incompleta_nao_tem_sucesso_parcial(self):
        html='<table><tr><th>Classe</th><th>Nível</th><th>Valor</th></tr><tr><td>A</td><td>1</td><td>2.000,00</td></tr><tr><td>B</td><td>2</td><td>3.000,00</td></tr></table>'
        r=extrair_para_revisao('incompleta.html',html.encode());self.assertFalse(r['candidatos']);self.assertTrue(any('incompletas' in a for a in r['pendencias']))
