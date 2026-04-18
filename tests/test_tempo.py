import re

from src.utils.tempo import agora_iso, agora_compact


def test_agora_iso_retorna_iso8601_com_tz():
    # formato esperado: 2026-04-18T03:33:21.123456+00:00
    s = agora_iso()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", s)
    # tem timezone (+, - ou Z)
    assert "+" in s or s.endswith("Z") or s[-6] in "+-"


def test_agora_compact_retorna_YYYYMMDD_HHMM():
    s = agora_compact()
    assert re.match(r"^\d{8}_\d{4}$", s)


def test_timestamps_sao_crescentes():
    # chamadas seguidas devem retornar horarios >= os anteriores
    import time
    a = agora_iso()
    time.sleep(0.01)
    b = agora_iso()
    # string comparison funciona em iso8601
    assert b >= a
