import unittest
from src.coleta.cache_catalogo import cache_catalogo
class TestCache(unittest.TestCase):
 def test_expira_limpa_e_nao_guarda_erros(self):
  t=[0]; chamadas=[]
  @cache_catalogo(maxsize=1,ttl=10,clock=lambda:t[0])
  def fonte(x):
   chamadas.append(x)
   if x==0: raise ValueError("falha")
   return len(chamadas)
  self.assertEqual(fonte(1),fonte(1));t[0]=10;self.assertEqual(fonte(1),2)
  fonte.cache_clear();self.assertEqual(fonte(1),3)
  for _ in range(2):
   with self.assertRaises(ValueError):fonte(0)
  self.assertEqual(chamadas.count(0),2);fonte(2);self.assertEqual(fonte(1),7)
