"""Orquestra a coleta anual e histórica sem misturar regras e interface."""

from dataclasses import replace

from src.calculos.indicadores import (
    classificar_percentual,
    diferenca_pontos_percentuais,
    percentual_comprometimento,
    variacao_percentual,
)
from src.coleta.tce_client import TCEClient, TCEError, TCEConsultaIndisponivel
from src.extracao.relatorios import (
    extrair_rcl_rreo,
    extrair_resumo_fundeb,
    extrair_resumo_pessoal,
)
from src.modelos.analise import (
    AnaliseFinanceira,
    AnaliseHistorica,
    DadosFundeb,
    ErroAno,
    EvolucaoFinanceira,
    LimitesPessoal,
    ResumoHistorico,
)
from src.persistencia.arquivos import ArquivoBrutoStore


class AnaliseService:
    """Liga coleta, extração e cálculos em funções menores e testáveis."""

    PERIODO_FECHAMENTO_MDE = "32"

    def __init__(self, cliente_factory=TCEClient, raw_store=None, salvar_brutos=True):
        self.cliente_factory = cliente_factory
        self.raw_store = raw_store or ArquivoBrutoStore()
        self.salvar_brutos = salvar_brutos

    def _coletar_relatorio(
        self,
        municipio_id,
        entidade_id,
        ano,
        relatorio_id,
        periodo_id=None,
    ):
        conteudo = self.cliente_factory().coletar_relatorio_csv(
            municipio_id,
            entidade_id,
            relatorio_id,
            ano,
            periodo_id=periodo_id,
        )
        aviso = None
        if self.salvar_brutos:
            try:
                self.raw_store.salvar(
                    municipio_id,
                    entidade_id,
                    ano,
                    relatorio_id,
                    conteudo,
                )
            except OSError:
                aviso = f"O relatório {relatorio_id} foi processado, mas não pôde ser salvo localmente."
        return conteudo, aviso

    def _coletar(self, municipio_id, entidade_id, ano, incluir_fundeb=True):
        # O portal é antigo e pode responder 500 quando duas sessões geram
        # relatórios simultaneamente. A coleta permanece sequencial.
        avisos = []
        csv_rcl, aviso = self._coletar_relatorio(
            municipio_id, entidade_id, ano, TCEClient.RELATORIO_RCL
        )
        if aviso:
            avisos.append(aviso)
        csv_pessoal, aviso = self._coletar_relatorio(
            municipio_id, entidade_id, ano, TCEClient.RELATORIO_PESSOAL
        )
        if aviso:
            avisos.append(aviso)

        csv_fundeb = None
        if incluir_fundeb:
            try:
                csv_fundeb, aviso = self._coletar_relatorio(
                    municipio_id,
                    entidade_id,
                    ano,
                    TCEClient.RELATORIO_MDE,
                    periodo_id=self.PERIODO_FECHAMENTO_MDE,
                )
                if aviso:
                    avisos.append(aviso)
            except TCEError as erro:
                avisos.append(f"FUNDEB indisponível para {ano}: {erro}")
        return csv_rcl, csv_pessoal, csv_fundeb, avisos

    def analisar(
        self,
        municipio_id,
        municipio_nome,
        entidade_id,
        entidade_nome,
        ano,
        incluir_fundeb=True,
    ):
        csv_rcl, csv_pessoal, csv_fundeb, avisos = self._coletar(
            municipio_id, entidade_id, ano, incluir_fundeb=incluir_fundeb
        )
        rcl_rreo = extrair_rcl_rreo(csv_rcl)
        resumo = extrair_resumo_pessoal(csv_pessoal)

        limites = LimitesPessoal(
            alerta=resumo["limite_alerta"],
            prudencial=resumo["limite_prudencial"],
            maximo=resumo["limite_maximo"],
        )
        percentual = percentual_comprometimento(
            resumo["despesa_total_pessoal"], resumo["rcl_ajustada"]
        )

        fundeb = None
        if csv_fundeb:
            try:
                resumo_fundeb = extrair_resumo_fundeb(csv_fundeb)
                fundeb = DadosFundeb(
                    receitas_recebidas=resumo_fundeb["receitas_recebidas"],
                    resultado_liquido_transferencias=resumo_fundeb[
                        "resultado_liquido_transferencias"
                    ],
                    fonte="RREO - Manutenção e Desenvolvimento do Ensino (MDE)",
                    periodo="6º Bimestre",
                    percentual_aplicacao_mde=resumo_fundeb.get(
                        "percentual_aplicacao_mde"
                    ),
                )
            except TCEError as erro:
                avisos.append(f"O relatório do FUNDEB foi obtido, mas não pôde ser extraído: {erro}")

        return AnaliseFinanceira.agora(
            municipio_id=municipio_id,
            municipio=municipio_nome,
            entidade_id=entidade_id,
            entidade=entidade_nome,
            ano=ano,
            receita_corrente_liquida=resumo["rcl"],
            receita_corrente_liquida_ajustada=resumo["rcl_ajustada"],
            despesa_total_pessoal=resumo["despesa_total_pessoal"],
            percentual_oficial=resumo["percentual_oficial"],
            percentual_calculado=round(percentual, 4),
            classificacao=classificar_percentual(percentual, limites),
            limites=limites,
            rcl_relatorio_rreo=rcl_rreo,
            diferenca_validacao_rcl=round(resumo["rcl"] - rcl_rreo, 2),
            fonte_receita="RREO - Demonstrativo da Receita Corrente Líquida",
            fonte_pessoal="RGF - Demonstrativo da Despesa com Pessoal",
            fundeb=fundeb,
            avisos=tuple(avisos),
        )

    @staticmethod
    def _adicionar_evolucoes(resultados):
        atualizados = []
        anterior = None
        for atual in resultados:
            fundeb_atual = atual.fundeb.receitas_recebidas if atual.fundeb else None
            fundeb_anterior = (
                anterior.fundeb.receitas_recebidas
                if anterior is not None and anterior.fundeb is not None
                else None
            )
            evolucao = EvolucaoFinanceira(
                rcl_ajustada_percentual=variacao_percentual(
                    atual.receita_corrente_liquida_ajustada,
                    anterior.receita_corrente_liquida_ajustada if anterior else None,
                ),
                despesa_pessoal_percentual=variacao_percentual(
                    atual.despesa_total_pessoal,
                    anterior.despesa_total_pessoal if anterior else None,
                ),
                receitas_fundeb_percentual=variacao_percentual(fundeb_atual, fundeb_anterior),
                comprometimento_pontos_percentuais=diferenca_pontos_percentuais(
                    atual.percentual_calculado,
                    anterior.percentual_calculado if anterior else None,
                ),
            )
            atualizados.append(replace(atual, evolucao=evolucao))
            anterior = atual
        return tuple(atualizados)

    @staticmethod
    def _resumir(resultados, quantidade_erros):
        primeiro = resultados[0]
        ultimo = resultados[-1]
        primeiro_fundeb = primeiro.fundeb.receitas_recebidas if primeiro.fundeb else None
        ultimo_fundeb = ultimo.fundeb.receitas_recebidas if ultimo.fundeb else None
        maior = max(resultados, key=lambda item: item.percentual_calculado)
        media = sum(item.percentual_calculado for item in resultados) / len(resultados)
        return ResumoHistorico(
            anos_analisados=len(resultados),
            anos_com_erro=quantidade_erros,
            evolucao_acumulada_rcl_ajustada=variacao_percentual(
                ultimo.receita_corrente_liquida_ajustada,
                primeiro.receita_corrente_liquida_ajustada,
            ),
            evolucao_acumulada_despesa_pessoal=variacao_percentual(
                ultimo.despesa_total_pessoal,
                primeiro.despesa_total_pessoal,
            ),
            evolucao_acumulada_receitas_fundeb=variacao_percentual(
                ultimo_fundeb, primeiro_fundeb
            ),
            media_comprometimento=round(media, 4),
            maior_comprometimento=maior.percentual_calculado,
            ano_maior_comprometimento=maior.ano,
        )

    def analisar_historico(
        self,
        municipio_id,
        municipio_nome,
        entidade_id,
        entidade_nome,
        ano_inicial,
        ano_final,
        incluir_fundeb=True,
        anos_disponiveis=None,
    ):
        if ano_final < ano_inicial:
            raise ValueError("O exercício final deve ser maior ou igual ao inicial.")
        if ano_final - ano_inicial > 9:
            raise ValueError("A análise histórica aceita no máximo 10 exercícios por consulta.")

        resultados = []
        erros = []
        for ano in range(ano_inicial, ano_final + 1):
            if anos_disponiveis is not None and ano not in anos_disponiveis:
                erros.append(ErroAno(ano=ano, mensagem="Não há publicação disponível para este exercício no catálogo consultado."))
                continue
            try:
                resultados.append(
                    self.analisar(
                        municipio_id,
                        municipio_nome,
                        entidade_id,
                        entidade_nome,
                        ano,
                        incluir_fundeb=incluir_fundeb,
                    )
                )
            except TCEConsultaIndisponivel:
                # O catálogo é da entidade, anterior à seleção do ano.
                # Repetir os demais anos não disponibiliza um relatório ausente.
                raise
            except (TCEError, ValueError) as erro:
                erros.append(ErroAno(ano=ano, mensagem=str(erro)))

        if not resultados:
            detalhes = "; ".join(f"{erro.ano}: {erro.mensagem}" for erro in erros)
            raise TCEError(
                "Nenhum exercício pôde ser analisado no intervalo informado. "
                f"Detalhes por ano: {detalhes}"
            )

        resultados_com_evolucao = self._adicionar_evolucoes(resultados)
        return AnaliseHistorica.agora(
            municipio_id=municipio_id,
            municipio=municipio_nome,
            entidade_id=entidade_id,
            entidade=entidade_nome,
            ano_inicial=ano_inicial,
            ano_final=ano_final,
            resultados=resultados_com_evolucao,
            erros=tuple(erros),
            resumo=self._resumir(resultados_com_evolucao, len(erros)),
        )
