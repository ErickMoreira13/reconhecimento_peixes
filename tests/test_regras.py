import pytest

from src.schemas import CampoExtraido
from src.verificador import regras


TRANSC_EXEMPLO = (
    "fala galera, hoje a gente ta aqui no rio madeira pescando tucunare. "
    "joguei uma farinhada boa de milho e peguei um tambaqui de 5kg. "
    "estamos em porto velho, rondonia."
)


def test_evidencia_alinha_trecho_existe():
    score = regras.evidencia_alinha("rio madeira", TRANSC_EXEMPLO)
    assert score > 0.9


def test_evidencia_alinha_trecho_ausente():
    # trecho que nao existe deve retornar score baixo
    score = regras.evidencia_alinha("rio parana", TRANSC_EXEMPLO)
    assert score < 0.9


def test_evidencia_alinha_vazia():
    assert regras.evidencia_alinha("", TRANSC_EXEMPLO) == 0.0


def test_regra_aceita_campo_null():
    c = CampoExtraido(valor=None, confianca=0.0, evidencia="", modelo_usado="qwen")
    v = regras.aplica_regras("bacia", c, TRANSC_EXEMPLO, {})
    assert v.aceito


def test_regra_aceita_campo_com_evidencia_real():
    c = CampoExtraido(
        valor="Rio Madeira",
        confianca=0.9,
        evidencia="rio madeira pescando",
        modelo_usado="qwen",
    )
    v = regras.aplica_regras("rio", c, TRANSC_EXEMPLO, {})
    assert v.aceito


def test_regra_rejeita_evidencia_inventada():
    # valor que nao aparece no texto deve falhar
    c = CampoExtraido(
        valor="Rio Xingu",
        confianca=0.9,
        evidencia="estavamos no rio xingu catando pintado",
        modelo_usado="qwen",
    )
    v = regras.aplica_regras("rio", c, TRANSC_EXEMPLO, {})
    assert not v.aceito
    assert v.tipo_rejeicao == "evidencia_nao_alinha"


def test_regra_rejeita_confianca_baixa():
    c = CampoExtraido(
        valor="Rondonia",
        confianca=0.2,  # abaixo do threshold de estado (0.7)
        evidencia="rondonia",
        modelo_usado="qwen",
    )
    v = regras.aplica_regras("estado", c, TRANSC_EXEMPLO, {})
    assert not v.aceito
    assert v.tipo_rejeicao == "confianca_baixa"


def test_regra_detecta_nome_proprio_como_peixe():
    # "joao" nao deve ser extraido como especie
    c = CampoExtraido(
        valor=[{"nome": "Joao", "evidencia": "o Joao pescou muito"}],
        confianca=0.8,
        evidencia="o Joao pescou",
        modelo_usado="qwen",
    )
    v = regras.aplica_regras("especies", c, "fala galera, o Joao pescou muito aqui", {})
    assert not v.aceito
    assert v.tipo_rejeicao == "nome_proprio_confundido"


def test_regra_aceita_especies_reais():
    c = CampoExtraido(
        valor=[{"nome": "tucunare", "evidencia": "pescando tucunare"}],
        confianca=0.85,
        evidencia="pescando tucunare",
        modelo_usado="qwen",
    )
    v = regras.aplica_regras("especies", c, TRANSC_EXEMPLO, {})
    assert v.aceito


def test_regra_aceita_estado_enum_fechado():
    c = CampoExtraido(
        valor="RO",
        confianca=0.95,
        evidencia="porto velho, rondonia",
        modelo_usado="qwen",
    )
    v = regras.aplica_regras("estado", c, TRANSC_EXEMPLO, {})
    assert v.aceito


def test_regra_rejeita_estado_invalido():
    # "XX" nao eh uma UF valida do ibge
    c = CampoExtraido(
        valor="XX",
        confianca=0.9,
        evidencia="porto velho",
        modelo_usado="qwen",
    )
    v = regras.aplica_regras("estado", c, TRANSC_EXEMPLO, {})
    assert not v.aceito


def test_regra_nao_rejeita_por_fora_do_gazetteer():
    # REGRA CRUCIAL: mesmo com fora_do_gazetteer=true, o campo deve passar
    # se a evidencia bate e a confianca eh boa
    # (nunca rejeitar so pq nao ta no dict)
    c = CampoExtraido(
        valor="piabanha",  # peixe que pode nao estar no dict
        confianca=0.7,
        evidencia="peguei uma piabanha massa",
        modelo_usado="qwen",
        fora_do_gazetteer=True,
    )
    transc = "fala galera hoje peguei uma piabanha massa no rio"
    v = regras.aplica_regras("especies", c, transc, {})
    # deve aceitar: fora_do_gazetteer=true nao eh motivo pra rejeitar
    assert v.aceito
    # e a razao NAO deve ser valor_fora_gazetteer
    assert v.tipo_rejeicao != "valor_fora_gazetteer"


def test_ceva_keywords_aceita_com_ceva_no_texto():
    # fix 1: tipo_ceva so eh valido se texto mencionar ceva/seva/ceba/cevar
    c = CampoExtraido(
        valor="bola_de_massa",
        confianca=0.8,
        evidencia="fiz uma ceva",
        modelo_usado="qwen",
    )
    transc = "fala galera, fiz uma ceva top com milho pra pegar tilapia"
    v = regras.aplica_regras("tipo_ceva", c, transc, {})
    assert v.aceito


def test_ceva_keywords_rejeita_sem_ceva_no_texto():
    # video sem mencao explicita a ceva nao pode ter tipo_ceva preenchido
    c = CampoExtraido(
        valor="ceva_solta_na_agua",
        confianca=0.8,
        evidencia="",
        modelo_usado="qwen",
    )
    # texto nao menciona ceva, so pesca com isca viva
    transc = "peguei um tucunare com isca de lambari e linha fininha"
    v = regras.aplica_regras("tipo_ceva", c, transc, {})
    assert not v.aceito
    assert v.tipo_rejeicao == "evidencia_nao_alinha"


def test_ceva_keywords_aceita_variacoes_coloquiais():
    # ceba, seva sao grafias coloquiais frequentes nas transcricoes do whisper
    for keyword in ["ceva", "seva", "ceba", "cevar", "cevando", "cevador"]:
        c = CampoExtraido(
            valor="bola_de_massa",
            confianca=0.8,
            evidencia=keyword,
            modelo_usado="qwen",
        )
        transc = f"fala galera, hoje a gente vai {keyword} com milho"
        v = regras.aplica_regras("tipo_ceva", c, transc, {})
        assert v.aceito, f"falhou pra keyword {keyword}"


def test_ceva_keywords_nao_afeta_outros_campos():
    # regra de ceva so roda pra tipo_ceva, outros campos nao tem a restricao
    c = CampoExtraido(
        valor="tucunare",
        confianca=0.8,
        evidencia="um tucunare",
        modelo_usado="qwen",
    )
    transc = "peguei um tucunare bonito"  # sem palavra "ceva"
    v = regras.aplica_regras("especies", c, transc, {})
    # aceita mesmo sem ceva no texto pq especies nao precisa
    assert v.aceito or v.tipo_rejeicao != "evidencia_nao_alinha"


def test_rio_aparece_direto_no_texto():
    # fix 2: rio precisa aparecer literalmente na transcricao
    assert regras.rio_aparece_no_texto("Rio Madeira", "pescando no rio madeira top")
    assert regras.rio_aparece_no_texto("Rio Negro", "estamos aqui no rio negro amazonico")


def test_rio_sem_prefixo_tambem_bate():
    # "Madeira" sozinho bate se texto menciona "rio madeira"
    assert regras.rio_aparece_no_texto("Madeira", "aqui eh o rio madeira")


def test_rio_alucinado_nao_bate():
    # rio que nao aparece no texto = alucinacao
    assert not regras.rio_aparece_no_texto(
        "Rio Sao Francisco",
        "pescaria linda aqui no amazonas com tucunare",
    )


def test_rio_vazio_retorna_false():
    assert not regras.rio_aparece_no_texto("", "qualquer texto")
    assert not regras.rio_aparece_no_texto(None, "qualquer")


def test_rio_tolera_erro_whisper_leve():
    # fuzzy partial >= 90% pega typo pequeno do whisper
    # "iriri" vs "iriry" por exemplo
    assert regras.rio_aparece_no_texto("Rio Iriri", "acampamento na beira do rio iriry")


def test_regra_aceita_rio_mesmo_quando_nome_exato_nao_aparece():
    # apos revert do fix 2, regra _passa_rio_aparece foi removida.
    # rio "Rio Araguaia" ainda passa nas regras deterministicas se
    # a evidencia bate no texto. o critic llm decide depois.
    c = CampoExtraido(
        valor="Rio Araguaia",
        confianca=0.9,
        evidencia="no rio",  # smith_waterman passa
        modelo_usado="llama3.1:8b",
    )
    transc = "fala galera, pescaria em rondonia no rio madeira"
    v = regras.aplica_regras("rio", c, transc, {})
    assert v.aceito


def test_regra_aceita_rio_que_aparece_no_texto():
    c = CampoExtraido(
        valor="Rio Madeira",
        confianca=0.9,
        evidencia="rio madeira",
        modelo_usado="llama3.1:8b",
    )
    transc = "fala galera, pescaria no rio madeira em rondonia"
    v = regras.aplica_regras("rio", c, transc, {})
    assert v.aceito


def test_tipo_ceva_blacklist_rejeita_vara():
    # fix 3: "vara de bambu" eh equipamento, nao tipo de ceva
    c = CampoExtraido(
        valor="vara de bambu",
        confianca=0.8,
        evidencia="vara de bambu",
        modelo_usado="qwen",
    )
    transc = "fala galera, usando vara de bambu com ceva"  # tem "ceva" pra passar keywords
    v = regras.aplica_regras("tipo_ceva", c, transc, {})
    assert not v.aceito
    assert v.tipo_rejeicao == "contexto_irrelevante"


def test_tipo_ceva_blacklist_rejeita_carretilha():
    c = CampoExtraido(
        valor="Avenado GS",  # modelo de carretilha
        confianca=0.9,
        evidencia="avenado",
        modelo_usado="qwen",
    )
    transc = "pesca com carretilha avenado gs e ceva de milho"
    v = regras.aplica_regras("tipo_ceva", c, transc, {})
    assert not v.aceito


def test_tipo_ceva_blacklist_rejeita_nome_comercial_de_isca():
    c = CampoExtraido(
        valor="Isquinha Hunter Bait",
        confianca=0.9,
        evidencia="hunter bait",
        modelo_usado="qwen",
    )
    transc = "pesca com hunter bait na ceva"  # tem ceva pra passar keywords
    v = regras.aplica_regras("tipo_ceva", c, transc, {})
    assert not v.aceito


def test_tipo_ceva_blacklist_aceita_valor_legitimo():
    c = CampoExtraido(
        valor="bola_de_massa",
        confianca=0.8,
        evidencia="bola de massa",
        modelo_usado="qwen",
    )
    transc = "fiz uma ceva com bola de massa de milho"
    v = regras.aplica_regras("tipo_ceva", c, transc, {})
    assert v.aceito


def test_eh_especie_generica_bonito_adjetivo():
    # fix 4: "bonito" como adjetivo nao eh peixe
    assert regras._eh_especie_generica("bonito")
    assert regras._eh_especie_generica("peixe bonito")


def test_eh_especie_generica_paca_mamifero():
    assert regras._eh_especie_generica("paca")


def test_eh_especie_generica_girias():
    for g in ["cimprao", "pai tainha", "galera", "rapaziada", "peixe grande"]:
        assert regras._eh_especie_generica(g), f"falhou pra {g}"


def test_eh_especie_generica_aceita_peixe_real():
    # tucunare nao contem nenhum stop term, aceita
    assert not regras._eh_especie_generica("tucunare")
    assert not regras._eh_especie_generica("pacu")
    assert not regras._eh_especie_generica("traira")
    assert not regras._eh_especie_generica("pirarucu")


def test_especies_stop_terms_rejeita_generico():
    # fix 4: especies com termo generico sao rejeitadas
    c = CampoExtraido(
        valor=[{"nome": "peixe grande", "evidencia": "peguei um peixe grande"}],
        confianca=0.8,
        evidencia="peixe grande",
        modelo_usado="qwen",
    )
    transc = "fala galera, hoje peguei um peixe grande la no rio"
    v = regras.aplica_regras("especies", c, transc, {})
    assert not v.aceito
    assert v.tipo_rejeicao == "contexto_irrelevante"


def test_especies_stop_terms_rejeita_mix_com_generico():
    # se UM item for generico, rejeita o campo inteiro
    c = CampoExtraido(
        valor=[
            {"nome": "tucunare", "evidencia": "tucunare"},
            {"nome": "peixe grande", "evidencia": "peixe grande"},
        ],
        confianca=0.85,
        evidencia="tucunare e peixe grande",
        modelo_usado="qwen",
    )
    transc = "peguei tucunare e peixe grande"
    v = regras.aplica_regras("especies", c, transc, {})
    assert not v.aceito


def test_especies_stop_terms_aceita_so_peixe_real():
    c = CampoExtraido(
        valor=[{"nome": "tucunare", "evidencia": "tucunare"}],
        confianca=0.85,
        evidencia="tucunare",
        modelo_usado="qwen",
    )
    v = regras.aplica_regras("especies", c, TRANSC_EXEMPLO, {})
    assert v.aceito


def test_bacia_reconhecida_nome_principal():
    # fix 7: bacias principais do BR
    assert regras.bacia_reconhecida("Amazonica")
    assert regras.bacia_reconhecida("Sao Francisco")
    assert regras.bacia_reconhecida("Parana")
    assert regras.bacia_reconhecida("Uruguai")
    assert regras.bacia_reconhecida("Tocantins-Araguaia")


def test_bacia_reconhecida_com_acento():
    # texto do whisper nem sempre tem acento, funcao normaliza
    assert regras.bacia_reconhecida("Amazônica")
    assert regras.bacia_reconhecida("São Francisco")
    assert regras.bacia_reconhecida("Paraná")


def test_bacia_reconhecida_com_prefixo_bacia():
    assert regras.bacia_reconhecida("Bacia do Parana")
    assert regras.bacia_reconhecida("Bacia do Sao Francisco")
    assert regras.bacia_reconhecida("bacia da amazonica")


def test_bacia_reconhecida_alias_coloquial():
    # "velho chico" eh o Sao Francisco
    assert regras.bacia_reconhecida("velho chico")
    # "pantanal" eh a bacia do paraguai
    assert regras.bacia_reconhecida("pantanal")


def test_bacia_reconhecida_rio_principal_da_bacia():
    # se extraiu "Sao Francisco" como bacia (aparece como rio tambem),
    # eh reconhecido (nome de bacia = nome de rio principal)
    assert regras.bacia_reconhecida("Tapajos")  # rio da amazonica
    assert regras.bacia_reconhecida("Tiete")    # rio da parana


def test_bacia_reconhecida_rejeita_termo_invalido():
    # casos que apareceram nas anotacoes manuais
    assert not regras.bacia_reconhecida("Lago do Anzol")  # lago, nao bacia
    assert not regras.bacia_reconhecida("Piracema")        # epoca de desova
    assert not regras.bacia_reconhecida("Piau Sul")        # variedade de peixe


def test_bacia_reconhecida_vazio():
    assert not regras.bacia_reconhecida("")
    assert not regras.bacia_reconhecida(None)
