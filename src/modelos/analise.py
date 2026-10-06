from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class LimitesPessoal:
    alerta: float
    prudencial: float
    maximo: float


@dataclass(frozen=True)
class DadosFundeb:
    receitas_recebidas: float
    resultado_liquido_transferencias: float
    fonte: str
    periodo: str
    percentual_aplicacao_mde: Optional[float] = None


@dataclass(frozen=True)
class EvolucaoFinanceira:
    rcl_ajustada_percentual: Optional[float]
    despesa_pessoal_percentual: Optional[float]
    receitas_fundeb_percentual: Optional[float]
    comprometimento_pontos_percentuais: Optional[float]


@dataclass(frozen=True)
class AnaliseFinanceira:
    municipio_id: str
    municipio: str
    entidade_id: str
    entidade: str
    ano: int
    receita_corrente_liquida: float
    receita_corrente_liquida_ajustada: float
    despesa_total_pessoal: float
    percentual_oficial: float
    percentual_calculado: float
    classificacao: str
    limites: LimitesPessoal
    rcl_relatorio_rreo: float
    diferenca_validacao_rcl: float
    fonte_receita: str
    fonte_pessoal: str
    coletado_em: str
    fundeb: Optional[DadosFundeb] = None
    evolucao: Optional[EvolucaoFinanceira] = None
    avisos: tuple[str, ...] = ()

    @classmethod
    def agora(cls, **dados):
        horario_brasilia = datetime.now(ZoneInfo("America/Sao_Paulo"))
        return cls(coletado_em=horario_brasilia.isoformat(timespec="seconds"), **dados)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ErroAno:
    ano: int
    mensagem: str


@dataclass(frozen=True)
class ResumoHistorico:
    anos_analisados: int
    anos_com_erro: int
    evolucao_acumulada_rcl_ajustada: Optional[float]
    evolucao_acumulada_despesa_pessoal: Optional[float]
    evolucao_acumulada_receitas_fundeb: Optional[float]
    media_comprometimento: float
    maior_comprometimento: float
    ano_maior_comprometimento: int


@dataclass(frozen=True)
class AnaliseHistorica:
    municipio_id: str
    municipio: str
    entidade_id: str
    entidade: str
    ano_inicial: int
    ano_final: int
    resultados: tuple[AnaliseFinanceira, ...]
    erros: tuple[ErroAno, ...]
    resumo: ResumoHistorico
    coletado_em: str

    @classmethod
    def agora(cls, **dados):
        horario_brasilia = datetime.now(ZoneInfo("America/Sao_Paulo"))
        return cls(coletado_em=horario_brasilia.isoformat(timespec="seconds"), **dados)

    def to_dict(self):
        return asdict(self)
