from src.extracao.prompts import monta_prompt_extrator, _top_peixes_por_bm25


def test_monta_prompt_contem_transcricao():
    transc = "peguei um tucunare de 5kg no rio madeira"
    prompt = monta_prompt_extrator(transc, {"peixe": [], "bacia hidrografica": []})
    assert transc in prompt


def test_monta_prompt_inclui_spans_do_gliner():
    transc = "pesca de tucunare"
    spans = {
        "peixe": [{"text": "tucunare", "score": 0.9}],
        "bacia hidrografica": [{"text": "bacia amazonica", "score": 0.8}],
    }
    prompt = monta_prompt_extrator(transc, spans)
    # os nomes dos spans aparecem no prompt
    assert "tucunare" in prompt
    assert "bacia amazonica" in prompt


def test_monta_prompt_sem_spans_nao_quebra():
    prompt = monta_prompt_extrator("texto qualquer", {"peixe": [], "bacia hidrografica": []})
    assert "nenhum" in prompt


def test_monta_prompt_mencao_vocabulario_aberto():
    # a regra central deve estar explicita no prompt
    prompt = monta_prompt_extrator("", {"peixe": [], "bacia hidrografica": []})
    p = prompt.lower()
    # alguma forma de vocabulario aberto tem que aparecer
    assert "vocabulario aberto" in p or "valor bruto" in p or "fora_do_gazetteer" in p


def test_monta_prompt_instrui_json():
    prompt = monta_prompt_extrator("", {"peixe": [], "bacia hidrografica": []})
    assert "json" in prompt.lower()


def test_top_peixes_bm25_retorna_lista():
    # texto com nome de peixe conhecido deve ranquear ele
    peixes = _top_peixes_por_bm25("peguei um tambaqui grande", k=5)
    assert isinstance(peixes, list)
    assert len(peixes) <= 5
    # tambaqui deve estar no topo
    assert any("tambaqui" in p.lower() for p in peixes)


def test_top_peixes_texto_sem_peixe():
    # texto generico deve retornar poucos/nenhum
    peixes = _top_peixes_por_bm25("hoje o dia esta bonito pra ir na praca", k=5)
    # tolera alguns matches falsos, mas em geral eh pequeno
    assert isinstance(peixes, list)


def test_top_peixes_limite_k():
    peixes = _top_peixes_por_bm25("pescamos tucunare tambaqui pacu dourado pirarucu piranha traira", k=3)
    assert len(peixes) <= 3


def test_prompt_menciona_isca_vs_especie_alvo():
    # fix 5: prompt tem que ensinar a distinguir isca de especie pescada
    prompt = monta_prompt_extrator("teste", {"peixe": [], "bacia hidrografica": []})
    p = prompt.lower()
    # palavras chave que indicam a instrucao
    assert "isca" in p
    assert "camarao" in p or "piabao" in p  # menciona pelo menos uma isca tipica


def test_prompt_menciona_ceva_exige_evidencia():
    # fix 1: prompt deve deixar claro que tipo_ceva exige evidencia
    prompt = monta_prompt_extrator("teste", {"peixe": [], "bacia hidrografica": []})
    p = prompt.lower()
    # palavras-chave da instrucao
    assert "explicitamente" in p or "evidencia" in p
    # deve mencionar pelo menos uma das keywords de ceva
    assert any(kw in p for kw in ["cevar", "cevador", "cevando"])


def test_prompt_menciona_uf_exemplos():
    # fix 6: prompt deve ter exemplos de nome UF -> sigla
    prompt = monta_prompt_extrator("teste", {"peixe": [], "bacia hidrografica": []})
    p = prompt.lower()
    # checa pelo menos 3 pares nome -> sigla
    assert "sao paulo" in p and "sp" in p
    assert "minas gerais" in p and "mg" in p
    assert "rondonia" in p and "ro" in p


def test_prompt_menciona_adjetivo_regional():
    # adjetivo regional tipo "paulista", "mineiro", "paraense" tb deve ser pego
    prompt = monta_prompt_extrator("teste", {"peixe": [], "bacia hidrografica": []})
    p = prompt.lower()
    # pelo menos 2 adjetivos na lista
    assert sum(1 for a in ["paulista", "mineiro", "paraense", "gaucho", "baiano"]
               if a in p) >= 2
