# 0.9.0

- Leitor geral por estrutura: matrizes, transpostas, registros e listas de cargos, sem dependência do nome do município.
- XLS legado, DOC convertido e OCR opcional em PDF/imagens; revisão manual de estruturas não reconhecidas.
- Rejeição de blocos incompletos; OCR sinalizado e conferência obrigatória; cache de extração versionado.
- 155 testes aprovados e 1.844 fórmulas recalculadas em três exportações Araucária. Consulte docs/28_leitor_geral_v0.9.0.md.

# 0.8.3

- Tela simples: lista de tabelas agrupada, com títulos distintos e filtro; descrição completa da tabela escolhida; avisos em lista curta; ajuda para escolher a referência; barra de andamento com tempo decorrido; botões e abas com pelo menos 44 px.
- Backend: `exibicao` (título, grupo e porte) em cada candidato; reaproveitamento da leitura pelo SHA-256 e `versao_extracao`.
- Curitiba: grupo ocupacional por página; pisos de ACS e ACE com os 3 níveis (separação de colunas lado a lado) e salvaguarda contra tabela incompleta.
- `scripts/testar_navegador.py`: 32 verificações em Chromium real (desktop e celular), incluindo downloads, filtro, erros e acessibilidade básica.
- 14 testes novos (136 no total, 2 lentos opcionais com `TESTES_LENTOS=1`).

# 0.8.2.1

Correção da revisão independente da 0.8.2: uma tabela inválida deixa de derrubar o documento inteiro na preparação; as demais permanecem e a ignorada vira pendência.

# 0.8.2

Painel financeiro reorganizado conforme a referência, média parametrizada e impressão em uma página; PDF salarial genérico e blocos de classes; extração coordenada de PDFs Curitiba/Londrina e HTML Ponta Grossa; versões imutáveis dos brutos; TTL do catálogo TCE; impressão de abas auxiliares e documentação das limitações. Mantidas rotas e perfis da 0.8.1. 118 testes aprovados. Consulte docs/24_entrega_v0.8.2.md.

# Histórico de mudanças

## 0.8.1 - 03/10/2026

- Parser salarial: documentos com termos de revogação ou alteração ("revogado", "nova redação", "passa a vigorar", "ficam alterados") geram aviso com o trecho encontrado. O sistema continua sem decidir a vigência.
- Análise salarial rejeita ano preenchido de forma inválida (antes aceitava "dois mil" e exibia "None" no Excel e no nome do arquivo). Ano ausente continua tolerado.
- Excel financeiro: as fórmulas do Painel agora trazem o valor calculado em cache (novo `src/exportacao/cache_xlsx.py`); pré-visualizações e leitores que não recalculam deixam de mostrar células em branco. As fórmulas permanecem vivas.
- Gráficos do Excel financeiro com linhas retas; a suavização criava picos inexistentes entre os exercícios.
- 15 testes novos (108 no total), incluindo a reprodução dos números do relatório-modelo do professor (referência 2.433,89; diferença -314,57; defasagem 14,84%). Conferência: zero erros de fórmula no LibreOffice e valores em cache idênticos ao recálculo em todos os Excel gerados.

## 0.8.0 - 08/09/2026

- Nova tela inicial com seleção curta e uma ação para preparar e baixar o Excel.
- Consulta financeira resolve município oficial, prefeitura, relatórios e anos publicados no servidor; mantém FUNDEB na análise.
- Anos sem publicação são registrados no histórico, sem solicitar relatórios inexistentes nem preencher valores presumidos.
- Tabelas salariais preparadas geram o Excel diretamente. Documento novo inicia a extração ao selecionar o arquivo, pede apenas dados ausentes e preserva a preparação para reutilização.
- Preparações salariais são mantidas na pasta de dados do usuário, fora da versão extraída do projeto.
- Cenário, referência e jornada continuam explícitos. Recortes ambíguos exigem conferir a completude; PSPN não é aplicado a outras profissões.
- Exportadores e modelo do Excel preservados. Tela detalhada anterior acessível em `/avancado`.
- Incluídos `Iniciar.bat` e `iniciar.py` para preparar dependências e abrir o navegador no Windows. Mantidas as correções de favicon, erros HTTP e recarga involuntária.
- Suíte ampliada para 93 testes, interação da nova interface verificada em DOM simulado e consulta real completa de Cruzeiro do Sul/2025 aprovada.

## 0.7.2 - 08/09/2026

- Confirmado que o 500 no carregamento vinha de favicon ausente; incluído o ícone e sua rota.
- Corrigida a escolha inicial de entidades: Município/Prefeitura recebe prioridade, preservando as demais opções.
- Conferido o catálogo antes de solicitar relatórios, evitando postbacks inválidos para entidades que não os oferecem.
- Ausência confirmada de relatório recebe resposta 422 e orientação; falhas de conexão/coleta continuam distintas.
- Histórico interrompe consultas a relatórios ausentes do catálogo e preserva os motivos individuais quando todos os anos falham por outros motivos.
- Adicionado diagnóstico de método, caminho e causa para erros de consulta/coleta no terminal.
- Desativados debug e reloader na execução padrão para evitar reinícios por eventos do watchdog em bibliotecas do Python.
- Oito novos testes; suíte ampliada de 72 para 80 testes.

## 0.7.1 - 08/09/2026

- Corrigido o handler genérico que convertia exceções HTTP, incluindo 404 e 405, em erro 500.
- Respostas HTTP preservam status e cabeçalhos originais e informam o método e caminho solicitados em JSON.
- Falhas internas continuam registradas com traceback; o log agora inclui método e caminho.
- Preservado o tratamento específico de uploads grandes (413).
- Adicionados quatro testes de regressão de erros HTTP.

## 0.7.0 - 07/09/2026

- Ampliada a comparação para diferentes profissões/cargos, com referência explícita e validação de ano e jornada.
- Criadas extração para revisão, seleção de tabelas candidatas e grade editável de níveis, classes, vencimentos e progressões.
- Adicionados CSV/TSV/XLSX/HTML e JSON ao fluxo de revisão; PDF/Word mantêm a extração textual com limitações declaradas.
- Refeito o Excel salarial com a ordem, tabelas e cores do relatório recebido: atual verde, referência roxa, alertas, diferenças e defasagem.
- Incluídas fórmulas editáveis, dados originais, parâmetros e fontes; carreiras longas preservam todas as classes.
- Mantido o truncamento em Cafezal; adotado arredondamento comercial como padrão para novas análises.
- Incorporada amostra de Auxiliar Administrativo Operacional de Curitiba/2026 com 184 vencimentos oficiais e referência didática explicitamente identificada.
- Servidor recalcula a entrada antes de exportar e impede aplicação automática do PSPN a outras profissões.
- Preservados tzdata, regras financeiras e documentos das versões anteriores.
- Registrados os limites da coleta dos seis municípios e as premissas ainda sujeitas à revisão do professor.

## 0.6.1 - 31/08/2026

- Adicionado `tzdata` às dependências para que `America/Sao_Paulo` funcione também no Windows sem base IANA do sistema.
- Reposicionado Cafezal do Sul como referência de layout e exemplo, não como estrutura padrão dos demais municípios.
- Confirmado que não existe uma API salarial municipal única equivalente à fonte financeira do TCE-PR.
- Criado catálogo inicial com seis pontos oficiais: Cafezal do Sul, Curitiba, Londrina, Maringá, Ponta Grossa e Siqueira Campos, além da opção livre.
- Criado fluxo independente de aquisição para tabela vigente, plano de carreira e ato de reajuste.
- Adicionados validação de PDF/DOC/DOCX/XLS/XLSX/CSV/HTML, hashes SHA-256, diagnóstico de OCR/conversão e manifesto JSON.
- Originais salariais passam a ser preservados em `data/raw/salarios/`, sem executar filtragem ou comparação automaticamente.
- Mantidos sem alteração os cálculos, importador, Excel e PDF da comparação existente.
- Adicionados 8 testes; suíte ampliada de 50 para 58 testes.

## 0.6.0 - 26/08/2026

- Auditado o escopo contra a APS atualizada, o relatório `XYZ`, a planilha `XYX`, o Anexo A de Cafezal, o link oficial do TCE, o Contexto Mestre e a conversa do grupo.
- Confirmado e documentado que Curitiba é a demonstração financeira preservada, não o único município da aplicação.
- Alterada a tela inicial para não apresentar Curitiba como se fosse todo o catálogo enquanto o TCE ainda está carregando.
- A consulta ao vivo agora é bloqueada quando município, entidade ou exercícios não puderem ser confirmados; nenhum ano genérico é usado silenciosamente.
- Adicionados estado visível da fonte, tentativa de reconexão e explicação separando consulta real e demonstração offline.
- A análise histórica virou o modo inicial por corresponder ao relatório e à planilha de referência.
- O modo anual passou a carregar qualquer amostra preservada de Curitiba entre 2019 e 2025, eliminando o bloqueio em 2019.
- Adicionado cache em memória para catálogos de municípios, entidades e exercícios durante a execução.
- Tornado mais robusto o disparo dos downloads no navegador e sanitizado o nome do Excel financeiro no servidor.
- Validada a integração real com 399 municípios, três entidades de Cafezal do Sul e sete exercícios fechados entre 2019 e 2025.
- Adicionados 4 testes de escopo e amostras; suíte ampliada de 46 para 50 testes.

## 0.5.1 - 25/08/2026

- Impedido que percentuais em notas ou parênteses sejam interpretados como classes salariais.
- A leitura dos valores de cada nível agora começa somente após o identificador do nível.
- Regras verticais duplicadas e diferentes deixam de ser sobrescritas: a importação informa o conflito e exige revisão humana.
- Declarações gerais de progressão conflitantes deixam de ser combinadas como uma falsa progressão não uniforme.
- A captura da progressão foi limitada à cláusula iniciada pelo termo relevante, ignorando observações posteriores entre parênteses.
- Adicionados 3 testes adversariais; suíte ampliada de 43 para 46 testes.

## 0.5.0 - 25/08/2026

- Corrigida a perda silenciosa de níveis em algarismos romanos com mais de um caractere.
- Adicionado suporte a códigos de nível numéricos e corrigida a leitura de valores sem separador de milhar, como `2400,00`.
- O importador agora interrompe a análise quando encontra uma linha salarial com `Nível` que não consegue interpretar com segurança.
- Adicionado reconhecimento de redações com `interstício` e inferência auditável quando a regra horizontal não aparece no documento.
- Adicionado suporte a progressões horizontais não uniformes, com um percentual por transição de classe.
- Adicionado suporte a regras verticais percentuais ou com acréscimo fixo em reais e nível de referência explícito.
- Atualizados interface, Excel e PDF para exibir as novas regras sem representar valor fixo como `0%`.
- Parametrizados `scripts/testar_tce.py` e `scripts/mapear_tce.py` para qualquer município, entidade e exercício.
- Incorporados testes de regressão do QA exploratório; suíte ampliada de 31 para 43 testes.

## 0.4.0 - 24/08/2026

- Incorporados os três materiais enviados pelo professor como referências preservadas.
- Implementada a amostra salarial real de Cafezal do Sul/2026, com 3 níveis e 12 classes.
- Implementadas importação de tabelas em PDF, DOCX e DOC legado, com LibreOffice opcional.
- Implementada comparação com PSPN proporcional à jornada, com truncamento ou arredondamento configurável.
- Implementadas diferença monetária, defasagem e verificação das progressões horizontal e vertical.
- Adicionadas exportação salarial Excel com fórmulas e relatório PDF em quatro páginas.
- Adicionada aba `Painel financeiro` ao Excel histórico, sem o link externo existente na planilha-modelo.
- Adicionada extração opcional do percentual de aplicação constitucional em MDE.
- Integrado o módulo salarial completo à interface web.
- Ampliada a suíte de 21 para 31 testes automatizados.
- Adicionadas evidências prontas de Excel/PDF e documentação das premissas ainda pendentes.

## 0.3.0 — 15/08/2026

- Mapeado o relatório 15 (RREO/MDE), período 6º bimestre, para receitas do FUNDEB.
- Implementada extração do FUNDEB por rótulo, tolerando a mudança de layout ocorrida a partir de 2021.
- Implementadas análise histórica de até 10 exercícios, falha parcial por ano e resumo acumulado.
- Implementadas evolução anual de RCL ajustada, despesa, FUNDEB e comprometimento.
- Adicionadas persistência local dos CSVs oficiais e novas rotas de apoio.
- Refeita a interface para alternar entre análise anual e histórica, com gráfico e avisos.
- Ampliada a exportação Excel para resultados históricos.
- Adicionados inspetores seguros de PDF salarial e planilha original.
- Criada amostra real de Curitiba/2019–2025, com 21 relatórios e nenhum ano com erro.
- Criada planilha de evidências com fórmulas, gráfico e rastreabilidade.
- Ampliada a suíte de 10 para 21 testes automatizados.
- Atualizada toda a documentação para separar o que está pronto do que depende de materiais externos.

## 0.2.0 — 15/08/2026

- Implementado cliente real do TCE-PR/SIM-AM.
- Implementadas coleta dos relatórios 10 e 20, extração, cálculos, interface e Excel anual.
- Criada amostra validada de Curitiba/2019 e 10 testes automatizados.

## 0.1.0 — 15/08/2026

- Criada a estrutura inicial do projeto e consolidado o escopo dos dois módulos.
- Atualizada a equipe para 7 integrantes e criada a documentação inicial.
