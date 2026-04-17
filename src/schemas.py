from dataclasses import dataclass, field
from typing import Any, Literal


# dataclasses usadas em todo o pipeline
# mantidas simples de proposito, sem frozen/slots/kw_only, essa coisa toda


# tipo_rejeicao: lista FINAL de razoes validas que o verificador pode usar
# obs importante: NAO tem "valor_fora_gazetteer" aqui porque o vocabulario do projeto eh ABERTO
# se o modelo capturar uma especie/bacia/rio/ceva/grao que nao ta no dict, a gente QUER saber
# o dict em src/dicts/ eh hint pra canonizar, nao filtro
TipoRejeicao = Literal[
    "evidencia_nao_alinha",
    "conflito_cross_field",
    "alucinacao_suspeita",
    "confianca_baixa",
    "nome_proprio_confundido",
    "contexto_irrelevante",
]


@dataclass
class CampoExtraido:
    # valor pode ser str, lista (pra especies), ou None quando nao mencionado
    valor: Any
    confianca: float
    evidencia: str
    modelo_usado: str
    # flag crucial: true quando o valor NAO bate com o gazetteer
    # nao eh erro, eh dado novo. serve pra analise depois.
    fora_do_gazetteer: bool = False
    latencia_ms: int = 0


@dataclass
class Veredito:
    aceito: bool
    razao: str
    sugestao_retry: str | None = None
    confianca_critica: float = 0.0
    tipo_rejeicao: TipoRejeicao | None = None


@dataclass
class ResultadoVideo:
    video_id: str
    plataforma: str
    autor: str
    link: str
    data_publicacao: str  # mes/ano
    campos: dict[str, CampoExtraido] = field(default_factory=dict)
    # manifesto tecnico pra reproducibilidade
    manifesto: dict = field(default_factory=dict)
