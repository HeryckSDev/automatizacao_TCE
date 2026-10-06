# Análise Municipal — versão 0.9.0

Escolha o que precisa e clique em **Gerar Excel**. A tela inicial reúne a consulta e a entrega do arquivo na mesma ação.

## Abrir no Windows

1. Extraia todo o ZIP para uma pasta.
2. Dentro de `projeto_jornada_magisterio`, abra **Iniciar.bat** com dois cliques.
3. Aguarde o navegador abrir. Na primeira vez, o sistema instala os componentes necessários; mantenha a internet conectada.

O computador precisa ter Python 3.11 ou mais recente instalado. O arquivo de abertura avisa se ele não for encontrado. Mantenha a janela aberta enquanto usa o sistema; feche-a para encerrar.

## Contas do município

1. Digite e escolha o município.
2. Mantenha **Histórico disponível**, escolha **Último ano disponível** ou informe os anos desejados.
3. Clique em **Gerar Excel** e aguarde o download.

A prefeitura, os relatórios e os exercícios publicados são identificados pelo sistema. O histórico reúne até dez exercícios fechados, a partir de 2019. Os anos sem publicação aparecem como ausência de dados. Uma consulta pode levar alguns minutos, conforme a resposta do TCE-PR.

O botão **Ver exemplo pronto de Curitiba** funciona sem consultar a internet e identifica expressamente os dados preservados de 2019–2025.

## Comparar salários

Para uma tabela já preparada, escolha **município e profissão** e clique em **Gerar Excel**. Duas preparações acompanham o projeto:

- **Cafezal do Sul / Professor/a / 2026:** exemplo enviado pelo professor, com 36 vencimentos. A jornada de 20 horas é uma premissa indicada na tela e no Excel; os centavos usam truncamento.
- **Curitiba / Auxiliar Administrativo Operacional / 2026:** 184 vencimentos oficiais, com uma simulação didática de +5% na base inicial. Essa referência não representa piso legal ou reajuste aprovado.

Para outra tabela, clique em **Usar outro documento** e escolha o arquivo. A leitura começa automaticamente. A tela pede apenas município, profissão, ano ou jornada que não tenham sido identificados e, quando faltar uma referência, pergunta como comparar. Gere o Excel; a preparação fica salva neste computador para as próximas consultas.

Se o documento reunir várias tabelas, escolha a desejada. PDFs com continuação exigem conferir se o recorte está completo. PDFs escaneados e imagens podem ser lidos com Tesseract opcional; estruturas não reconhecidas podem precisar de correção ou transcrição em **Revisão detalhada e fontes**. A versão não busca automaticamente tabelas salariais de todas as prefeituras nem declara seis dossiês completos.

## Modelo do Excel

A exportação mantém o modelo já reconstruído a partir das páginas 9–11 do material do professor: estrutura, tabela atual verde, referência roxa, não conformidades, diferenças monetárias e defasagem. As abas auxiliares preservam parâmetros, dados originais e fontes. Todas as classes são mantidas, inclusive nas carreiras que precisam de blocos de continuação.

Arredondamento comercial é o padrão das novas análises. Cafezal mantém o truncamento para reproduzir o anexo. Ambos permanecem ajustáveis. O PSPN é uma referência exclusiva do magistério; outras profissões usam a referência informada para sua análise.

## Ajustes detalhados e desenvolvimento

A tela anterior continua disponível pelo link **Revisão detalhada e fontes**. Use-a para corrigir classes e níveis, informar regras especiais, selecionar outras entidades financeiras ou registrar o dossiê completo. Esse trabalho não faz parte do caminho normal das tabelas já preparadas.

Para executar pelo terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe iniciar.py
```

`python app.py` continua abrindo o servidor em `http://127.0.0.1:5000/`, sem abrir o navegador. As duas formas iniciam sem debug e sem recarga automática. `tzdata` permanece nas dependências para o fuso funcionar no Windows.

As preparações da tela simplificada são guardadas em `%LOCALAPPDATA%/AnaliseMunicipal/tabelas_salariais` no Windows e em `~/.local/share/AnaliseMunicipal/tabelas_salariais` nos demais sistemas. Elas permanecem ao extrair uma nova versão do projeto. Arquivos de entrada não são enviados a um serviço de interpretação externo.

Detalhes técnicos e históricos: `docs/20_guia_detalhado_v0.7.2.md`, `docs/21_automacao_v0.8.md` e `CHANGELOG.md`.

## Verificações

```powershell
python -m unittest discover -s tests -v
```

A suíte local possui 93 testes. A automação completa também consultou Cruzeiro do Sul e entregou o Excel de 2025 usando apenas município e período. A evidência está em `docs/evidencias/v0.8/`. O teste da interface usa DOM simulado; o instalador `.bat` ainda precisa de execução em um Windows real.


## Evolução 0.9.0

- Escolha de tabelas em documentos grandes: lista agrupada (por grupo ocupacional), com título distinto, porte e valor inicial, e caixa de filtro quando há 8 ou mais tabelas (Curitiba tem 67).
- Andamento visível: barra, tempo decorrido e mensagens que mudam devagar na leitura de documentos, na geração do Excel salarial e na consulta financeira.
- O mesmo documento não é lido duas vezes: a preparação é reaproveitada pelo SHA-256 e pela versão da leitura (Curitiba: de cerca de 22 s para menos de 1 s na segunda vez).
- Piso salarial de Curitiba (Agente Comunitário de Saúde e Agente de Combate às Endemias): os 3 níveis passam a ser lidos (antes só o último saía, em silêncio). Salvaguarda: página cujos níveis lidos não cobrem os níveis indicados no texto não é incorporada e gera pendência.
- Teste de interface em navegador real: `python scripts/testar_navegador.py` (requer `pip install -r requirements-dev.txt` e `playwright install chromium`).

## Evolução 0.8.2

Esta versão evolui a 0.8.1 e mantém suas 28 rotas explícitas e os perfis existentes. Consulte [entrega e limites](docs/24_entrega_v0.8.2.md). Os prompts recebidos foram preservados em `docs/instrucoes_recebidas` e a skill aplicada em `skills/analise-municipal-magisterio`; instruções antigas devem ser lidas junto com o estado real desta versão.

No Git Bash, dentro da pasta do projeto:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000.

## Leitor geral — 0.9.0

PDF, DOC/DOCX, XLS/XLSX, CSV/TSV, HTML e imagens PNG/JPG/JPEG. OCR e conversão DOC dependem de ferramentas opcionais. Leia [resultados e limitações](docs/28_leitor_geral_v0.9.0.md) antes de usar documentos escaneados.


## Conteúdo publicado no GitHub

Este repositório contém o código da versão 0.9.0, interface, dependências, testes, scripts e amostras da aplicação. Documentos recebidos, PDFs salariais externos, evidências geradas e os diretórios `referencias/`, `docs/` e `skills/` não fazem parte desta publicação. As menções a esses arquivos acima descrevem o pacote completo, não arquivos disponíveis neste repositório.

Alguns testes de integração precisam dos documentos de referência ausentes. Os 155 testes aprovados anteriormente se referem ao pacote completo; a suíte não foi executada novamente nesta publicação reduzida. O leitor reconhece estruturas suportadas e não garante leitura de qualquer tabela municipal.
