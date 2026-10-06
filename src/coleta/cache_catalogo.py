"""Cache limitado com expiração; erros de coleta nunca são armazenados."""
from collections import OrderedDict
from functools import wraps
from threading import RLock
from time import monotonic


def cache_catalogo(maxsize=512, ttl=86400, clock=monotonic):
    def decorar(func):
        valores = OrderedDict()
        lock = RLock()
        @wraps(func)
        def chamada(*args, **kwargs):
            chave = (args, tuple(sorted(kwargs.items())))
            with lock:
                if chave in valores:
                    expiracao, valor = valores[chave]
                    if clock() < expiracao:
                        valores.move_to_end(chave)
                        return valor
                    del valores[chave]
                valor = func(*args, **kwargs)
                valores[chave] = (clock() + ttl, valor)
                while len(valores) > maxsize:
                    valores.popitem(last=False)
                return valor
        def limpar():
            with lock:
                valores.clear()
        chamada.cache_clear = limpar
        return chamada
    return decorar
