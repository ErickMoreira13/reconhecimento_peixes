import json
from pathlib import Path

import pytest

from src import config


def _cria_extracao_fake(out_dir: Path, video_id: str, suffix: str, campos_valores: dict):
    # helper pra gerar um _extracao_<suffix>.json fake
    out_dir.mkdir(parents=True, exist_ok=True)
    campos = {}
    for nome, val in campos_valores.items():
        campos[nome] = {
            "valor": val,
            "confianca": 0.8,
            "evidencia": "" if val else "",
            "modelo_usado": suffix,
            "fora_do_gazetteer": False,
            "latencia_ms": 1000,
        }
    data = {
        "video_id": video_id,
        "url": f"http://yt/{video_id}",
        "canal": "test",
        "publicado_em": "2025-01-01",
        "campos": campos,
        "verificado": False,
    }
    p = out_dir / f"{video_id}_extracao_{suffix}.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_benchmark_analisa_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)

    # cria 3 extracoes fake com suffix "modelo_x"
    _cria_extracao_fake(tmp_path, "vid1", "modelo_x", {
        "estado": "SP", "rio": "Rio Tiete", "grao": "milho",
        "municipio": None, "bacia": None,
        "tipo_ceva": "garrafa_pet_perfurada",
        "especies": [{"nome": "tilapia"}],
        "observacoes": "pesca de tarde",
    })
    _cria_extracao_fake(tmp_path, "vid2", "modelo_x", {
        "estado": None, "rio": None, "grao": None,
        "municipio": None, "bacia": None, "tipo_ceva": None,
        "especies": [], "observacoes": None,
    })
    _cria_extracao_fake(tmp_path, "vid3", "modelo_x", {
        "estado": "RJ", "rio": None, "grao": None,
        "municipio": None, "bacia": None, "tipo_ceva": None,
        "especies": [{"nome": "pacu"}, {"nome": "traira"}],
        "observacoes": "manha cedo",
    })

    from src.benchmark import analisa_suffix
    stats = analisa_suffix("modelo_x")

    assert stats["total_videos"] == 3
    # cobertura
    assert stats["cobertura_por_campo"]["estado"] == 2
    assert stats["cobertura_por_campo"]["especies"] == 2
    assert stats["cobertura_por_campo"]["grao"] == 1
    # especies unicas
    assert stats["especies_unicas"] == 3  # tilapia, pacu, traira
    # parse fail: vid2 tem tudo null
    assert stats["parse_fail_count"] == 1
    assert stats["parse_fail_pct"] == pytest.approx(33.3, abs=0.5)


def test_benchmark_retorna_erro_se_sem_arquivos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    from src.benchmark import analisa_suffix
    stats = analisa_suffix("naoexiste")
    assert "erro" in stats
