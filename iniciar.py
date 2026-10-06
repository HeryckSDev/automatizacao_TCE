"""Abre o aplicativo local e o navegador; usado pelo Iniciar.bat."""
from threading import Timer
import webbrowser

from werkzeug.serving import make_server

from app import create_app


def iniciar():
    # Uma porta reservada pelo próprio servidor evita abrir outra versão já ligada.
    servidor = make_server("127.0.0.1", 0, create_app(), threaded=True)
    endereco = f"http://127.0.0.1:{servidor.server_port}/"
    print(f"Seu sistema está aberto em {endereco}", flush=True)
    print("Mantenha esta janela aberta enquanto usa o sistema. Para encerrar, feche a janela.", flush=True)
    abertura = Timer(0.7, webbrowser.open, args=(endereco,))
    abertura.daemon = True
    abertura.start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        abertura.cancel()
        servidor.server_close()


if __name__ == "__main__":
    iniciar()
