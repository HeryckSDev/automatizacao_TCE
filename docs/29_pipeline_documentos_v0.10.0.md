# Processamento modular de documentos — v0.10.0

## Proposta e implementação

A proposta do tester, `Arquitetura_Processamento_Universal_TCE_PR.pdf`, recomenda identificar o formato, preservar tabelas, usar OCR quando necessário e normalizar antes da análise. Esta versão aplica esse fluxo ao módulo salarial. A expressão “universal” descreve a arquitetura extensível, não uma garantia de reconhecer qualquer documento ou tabela.

`src/document_processor/processor.py` é a entrada `processar_documento(nome, conteudo)`. Os módulos PDF, DOC/DOCX, XLS/XLSX, CSV/TSV e imagem separam a extração; HTML e JSON mantêm os leitores existentes. Extensões são aceitas por lista e PDF, imagens, DOCX/XLSX têm verificação adicional de conteúdo. Limites de arquivo e de expansão ZIP são aplicados antes da leitura. A normalização valida a estrutura salarial e acrescenta arquivo, SHA-256, localização, método e necessidade de revisão. O texto e as pendências continuam disponíveis para a revisão existente.

O PDF mantém adaptadores já testados. Nas páginas restantes, tenta primeiro tabelas nativas, depois texto. Se não houver tabela reconhecida e existir conteúdo em imagem ou texto insuficiente, tenta OCR local opcional. Uma tabela estruturalmente incompleta gera pendência; não é substituída por uma leitura que esconderia a lacuna. A decisão acontece por página, para aceitar documentos híbridos. Blocos separados são processados individualmente.

O normalizador não decide regras legais: valida níveis, classes e valores; a camada de análise mantém a validação de progressões e referência. Componentes `VB`/vencimento básico e totais por titulação ficam separados. As referências compostas classe-nível são preservadas como rótulos; a representação em uma série salarial não é uma equivalência jurídica de carreiras. RT individual não é uma tabela de vencimento básico. O PSPN não é aplicado automaticamente a totais ou ao magistério superior. A opção fica desabilitada na tela e é rejeitada tanto na automação quanto na camada de cálculo quando o indicador `pspn_inaplicavel` acompanha os dados.

## Resultado dos documentos reais

| Documento | Resultado |
|---|---|
| Magistério de Araucária, junho/2026 | 3 tabelas, 340 valores; extremos iguais aos testes anteriores. Jornada continua sem presunção. |
| Magistério superior, abril/2026, Universidade Federal do Cariri | 24 opções, 186 valores entre VB e totais por titulação/regime; âncoras conferidas no texto original. Documento federal, não tabela municipal nem base para usar PSPN da educação básica. |
| Reajuste de 5,17%, janeiro/2026, PDF escaneado | OCR executado; 0 tabelas confiáveis. Grade complexa não reconstruída; precisa revisão/transcrição ou planilha estruturada. |

A leitura não modifica o documento original. Campos ausentes de município, cargo, ano e jornada continuam sendo pedidos. Dedicação exclusiva não foi convertida automaticamente em horas. As opções de titulação podem compartilhar valores idênticos com VB; continuam separadas porque representam componentes distintos.

## O que esta versão não implementa

- Importar relatório fiscal genérico e cruzá-lo automaticamente com o TCE. A proposta exemplifica esse uso, mas ainda faltam regras de identificação de RCL/DTP/FUNDEB, entidade, exercício, período e natureza do valor no documento. `documento_normalizado.integracao_fiscal` é `false`.
- IA externa, interpretação semântica de qualquer lei ou reconhecimento de qualquer layout. OCR é Tesseract local opcional, sem envio de documentos a terceiros.
- Recuperação garantida de tabelas escaneadas, reconhecimento perfeito de cabeçalhos mesclados, união de continuações ou revisão humana dispensável.
- RT individual como base de uma comparação com piso, cálculo de folha ou validação jurídica de vigência/enquadramento.

O cliente TCE existente consulta o portal SIM-AM por sessão/postbacks e CSV oficial; a API Flask é local. A mudança não cria uma API REST oficial do TCE nem uma API salarial nacional.

## Execução e testes

O fluxo do usuário permanece: escolher arquivo, escolher tabela se necessário, preencher o que faltar, conferir o recorte quando solicitado e gerar Excel. Tesseract deve estar instalado no sistema para PDFs escaneados e imagens. A leitura funciona para formatos estruturados sem essa ferramenta.

A aba “Fontes e premissas” recebe SHA-256, método e localização. Cores, blocos e fórmulas do modelo principal permanecem. A versão de cache passou a `0.10.0` para não reutilizar extrações antigas.

Verificação realizada em Linux/Python 3.12, dependências instaladas pelo requirements. Testes sintéticos cobrem assinatura incompatível, tabela nativa versus texto embaralhado, página com cabeçalho textual e tabela-imagem, erro estrutural sem fallback silencioso, componentes separados, múltiplas tabelas, JSON fiscal não confundido com salário, upload HTTP, exportação e bloqueio de PSPN para totais. PNG e JPEG sintéticos foram lidos pelo OCR real. A suíte completa inclui documentos de referência do pacote local.

Não houve teste em Windows real, consulta TCE ao vivo ou nova inspeção visual no navegador. OCR foi testado com Tesseract e idioma disponível no ambiente; sua acurácia depende da imagem e do idioma instalado. O PDF escaneado de 5,17% permanece como evidência negativa. Os 186 valores do magistério superior não constituem validação jurídica; âncoras e separação de componentes foram conferidas, sem afirmar auditoria independente de todas as células.

A publicação GitHub não inclui documentos recebidos, fontes externas e evidências brutas. Alguns testes da versão completa exigem essas referências, ausentes da publicação reduzida.

## Evidência de exportação real

Foi gerado via API um Excel com a primeira tabela de VB do magistério superior, jornada de teste de 20 horas e simulação explícita de +5%, sem tratar esse cenário como norma ou piso legal. As 54 fórmulas têm cache e foram recalculadas no LibreOffice: zero erros de fórmula e zero divergências numéricas em relação aos valores produzidos pelo servidor, com tolerância 0,0000001. Isso verifica a exportação dessa amostra, não a adequação jurídica da comparação.

Validação final: 168 testes passaram em 38,577 segundos, com `TESTES_LENTOS=1`, incluindo os documentos locais de referência. Sintaxe JavaScript conferida com `node --check`.
