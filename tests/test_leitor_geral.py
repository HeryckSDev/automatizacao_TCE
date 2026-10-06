import unittest
from src.salarial.leitor_geral import ler_matrizes,ler_texto
from src.salarial.revisao_service import organizar_registros
class GeralTest(unittest.TestCase):
 def test_matriz_sem_nome_de_municipio(self):
  d,p=ler_matrizes([[['Faixa','Inicial','Final'],['I','1.200,00','1.260,00'],['II',1500,1575]]],'x',organizar_registros)
  self.assertEqual(d[0]['niveis'][1]['valores'],[1500,1575]);self.assertNotIn('municipio',d[0])
 def test_transposta(self):
  d,p=ler_matrizes([[['Classe','I','II'],['A','1200,00','1500,00'],['B','1260,00','1575,00']]],'x',organizar_registros)
  self.assertEqual(d[0]['classes'],['A','B']);self.assertEqual(d[0]['niveis'][0]['valores'],[1200,1260])
 def test_incompleta_nao_vira_zero(self):
  d,p=ler_matrizes([[['Nivel','A','B'],['I','1200,00','ilegível']]],'x',organizar_registros)
  self.assertFalse(d);self.assertTrue(p)
 def test_bloco_texto_nao_usa_reajuste_como_progressao(self):
  t='Município: Cidade Nova\nAno: 2026\nReajuste 9%\nNível A B\nI 1.000,00 1.020,00\nII 1.200,00 1.224,00'
  d,p=ler_texto(t,'x',organizar_registros);self.assertEqual(d[0]['progressoes_classes_percentuais'],[2]);self.assertEqual(d[0]['municipio'],'Cidade Nova')

 def test_lista_de_cargos_sem_carreira_inventada(self):
  d,p=ler_matrizes([[['Cargo','Vencimento'],['Técnico','2000,00'],['Motorista','2200,00']]],'x',organizar_registros)
  self.assertEqual([x['profissao'] for x in d],['Técnico','Motorista']);self.assertEqual(d[0]['progressoes_classes_percentuais'],[])

 def test_duas_matrizes_na_mesma_aba(self):
  d,p=ler_matrizes([[['Nivel','A','B'],['I',1200,1260],['Nivel','C','D'],['II',1500,1575]]],'x',organizar_registros)
  self.assertEqual(len(d),2);self.assertFalse(p)

 def test_nivel_ilegivel_nao_e_omitido(self):
  d,p=ler_texto('Nivel A B\nI 1000,00 1020,00\nII ilegível','x',organizar_registros)
  self.assertFalse(d);self.assertTrue(p)
