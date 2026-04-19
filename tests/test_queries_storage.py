from src.storage import db as storage


def test_upsert_e_lista(db_isolado):
    storage.upsert_queries(["pesca com ceva", "pescaria tucunare"], db_isolado)
    rows = storage.lista_queries(db_path=db_isolado)
    textos = {r["texto"] for r in rows}
    assert textos == {"pesca com ceva", "pescaria tucunare"}
    # todas entram como ativa
    assert all(r["status"] == "ativa" for r in rows)


def test_upsert_ignora_duplicata(db_isolado):
    storage.upsert_queries(["x"], db_isolado)
    storage.upsert_queries(["x", "y"], db_isolado)
    rows = storage.lista_queries(db_path=db_isolado)
    assert len(rows) == 2


def test_pega_query_ativa_ordem_menos_buscados(db_isolado):
    storage.upsert_queries(["a", "b"], db_isolado)
    # marca 'a' com mais buscas -> 'b' vem primeiro
    storage.atualiza_query("a", {"total_buscados": 10}, db_isolado)
    assert storage.pega_query_ativa(db_isolado) == "b"


def test_pega_query_ativa_none_quando_tudo_saturou(db_isolado):
    storage.upsert_queries(["a", "b"], db_isolado)
    storage.marca_query_saturada("a", "dedup_alto", db_isolado)
    storage.marca_query_saturada("b", "rejeicao_alta", db_isolado)
    assert storage.pega_query_ativa(db_isolado) is None


def test_marca_saturada_persiste_motivo(db_isolado):
    storage.upsert_queries(["q1"], db_isolado)
    storage.marca_query_saturada("q1", "dedup_alto", db_isolado)
    rows = storage.lista_queries("saturada", db_path=db_isolado)
    assert len(rows) == 1
    assert rows[0]["motivo_saturacao"] == "dedup_alto"


def test_atualiza_query_campos_numericos(db_isolado):
    storage.upsert_queries(["q"], db_isolado)
    storage.atualiza_query("q", {
        "total_buscados": 50,
        "total_novos": 10,
        "dedup_rate_ultima": 0.8,
    }, db_isolado)
    rows = storage.lista_queries(db_path=db_isolado)
    assert rows[0]["total_buscados"] == 50
    assert rows[0]["total_novos"] == 10
    assert rows[0]["dedup_rate_ultima"] == 0.8


def test_lista_queries_filtra_por_status(db_isolado):
    storage.upsert_queries(["a", "b", "c"], db_isolado)
    storage.marca_query_saturada("b", "dedup_alto", db_isolado)
    ativas = storage.lista_queries("ativa", db_isolado)
    satur = storage.lista_queries("saturada", db_isolado)
    assert {r["texto"] for r in ativas} == {"a", "c"}
    assert {r["texto"] for r in satur} == {"b"}
