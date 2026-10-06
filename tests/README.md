# Testes

A versão 0.8.0 possui 93 testes locais. Eles cobrem as regras financeiras e salariais, importação, dossiês, fórmulas e valores do Excel, HTTP e os novos caminhos de automação.

```powershell
python -m unittest discover -s tests -v
```

`test_automacao.py` verifica seleção automática da prefeitura, ano efetivamente publicado, ausência de dados sem coleta indevida, Excel em uma resposta, reutilização de tabelas após reabrir o aplicativo, metadados não presumidos, recortes ambíguos e abertura do navegador com servidor simulado.

Os testes Python não acessam a internet. A consulta real separada está registrada em `docs/evidencias/consulta_automatica_v0.8.0.json`.

## Interação da interface

Opcional para desenvolvimento: instale Node.js e `jsdom` em uma pasta de teste. O projeto não precisa de Node para funcionar.

```text
python -m scripts.preparar_qa_interface caminho-das-respostas.json
node scripts/testar_interface.cjs caminho-das-respostas.json
```

O script carrega `jsdom` normalmente pelo Node; se estiver instalado em outra pasta, defina `JSDOM_PATH` com o caminho do módulo. As respostas são geradas pelas rotas reais em diretório temporário. Durante o teste de DOM, `fetch` e download são simulados. A verificação cobre validação dos campos, clique único, preenchimento mínimo, download automático, recuperação de falha e reutilização da preparação.

Esse teste não substitui uma inspeção visual em navegador. O ambiente de validação é Linux; o `.bat` não foi executado em Windows.
