# Guia de colaboração

## Fluxo simples de Git/GitHub

1. Atualize a `main` antes de começar.
2. Crie uma branch curta para uma única tarefa.
3. Faça commits pequenos e explicativos.
4. Abra um Pull Request, mesmo que inicialmente como rascunho.
5. Peça pelo menos uma revisão antes de integrar na `main`.
6. Atualize a documentação quando o comportamento do sistema mudar.

## Padrão de branches

- `feat/coleta-tce-2019`
- `feat/interface-filtros`
- `fix/conversao-moeda`
- `test/validacao-curitiba-2019`
- `docs/requisitos-modulo-1`

## Padrão de commits

- `feat: adiciona coleta inicial do TCE`
- `fix: corrige conversão de valores monetários`
- `test: valida dados de Curitiba em 2019`
- `docs: atualiza requisitos do módulo financeiro`
- `refactor: separa coleta e tratamento`

## Revisão

- Código de coleta deve ser revisado por outro integrante do back-end.
- Fórmulas e valores devem possuir evidência da fonte usada.
- Mudanças de interface devem ser verificadas por outro integrante do front-end.
- O QA não é o único responsável pela qualidade; todos devem testar o que produzem.
- Pull Requests abertos no fim de semana podem ficar como rascunho para revisão do QA em dia útil.

## Definição de pronto

Uma tarefa só está pronta quando:

- atende aos critérios de aceitação;
- foi executada ou testada;
- não contém dados inventados;
- recebeu revisão;
- possui documentação suficiente para outro integrante entendê-la.

