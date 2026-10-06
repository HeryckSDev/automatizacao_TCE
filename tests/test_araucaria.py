import unittest
from pathlib import Path
import pdfplumber
from src.salarial.revisao_service import extrair_para_revisao, organizar_registros
from src.salarial.araucaria import extrair
from src.salarial.tabelas_coordenadas import candidato_registros,registro

P=Path(__file__).resolve().parents[1]/'referencias/araucaria/Tabela-Salarial-Magisterio-Araucaria-jun2026.pdf'
class AraucariaTest(unittest.TestCase):
 def test_pdf_tres_blocos_todos_os_valores_sem_jornada_inventada(self):
  d=extrair_para_revisao(P.name,P.read_bytes())['candidatos']
  self.assertEqual([len(x['niveis']) for x in d],[6,5,6])
  self.assertTrue(all(x['classes']==list('ABCDEFGHIJKLMNOPQRST') for x in d))
  self.assertEqual(sum(len(n['valores']) for x in d for n in x['niveis']),340)
  self.assertEqual([x['niveis'][0]['valores'][0] for x in d],[2397.69,2997.07,3596.49])
  self.assertEqual([x['niveis'][-1]['valores'][-1] for x in d],[9869.18,9869.67,14804.55])
  self.assertTrue(all('jornada_semanal' not in x and not x['jornada_confirmada_no_documento'] for x in d))
 def test_linha_incompleta_rejeita_pagina(self):
  with pdfplumber.open(P) as p:t=p.pages[0].extract_text()
  with self.assertRaises(ValueError):extrair(t.replace('2.397,69','',1),P.name,1,organizar_registros,candidato_registros,registro)
