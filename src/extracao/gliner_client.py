from pathlib import Path
from typing import Iterable

from gliner import GLiNER


# cliente do gliner pra extrair spans de peixe e bacia
# se tiver um checkpoint fine-tuned local, usa ele
# senao cai no base multilingue zero-shot (nao eh tao bom mas quebra galho)
#
# tentei expandir pra 4 labels (issue #10) mas latencia explodiu +261% e
# cobertura de bacia regrediu -16pp. voltei pra 2. ficou documentado
# em docs/comparacao-gliner-labels/

LABELS_PADRAO = ["peixe", "bacia hidrografica"]

_modelo: GLiNER | None = None


def _carrega(checkpoint_path: str | Path | None = None) -> GLiNER:
    # tenta local primeiro, cai pro base
    global _modelo
    if _modelo is not None:
        return _modelo

    if checkpoint_path and Path(checkpoint_path).exists():
        print(f"carregando gliner fine-tuned de {checkpoint_path}")
        _modelo = GLiNER.from_pretrained(str(checkpoint_path), local_files_only=True)
    else:
        # base multilingue, tem suporte pt nativo
        print("carregando gliner base (zero-shot multi), fine-tuned nao encontrado")
        _modelo = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")

    return _modelo


def extrai_spans(
    texto: str,
    labels: Iterable[str] = LABELS_PADRAO,
    threshold: float = 0.5,
    checkpoint_path: str | Path | None = None,
) -> list[dict]:
    # retorna lista de dicts com {text, label, start, end, score}
    # threshold 0.5 eh default do gliner, se tiver mt falso positivo sobe pra 0.6-0.7
    m = _carrega(checkpoint_path)
    labels_list = list(labels)

    # gliner tem limite de 384 tokens por padrao, se texto for mt longo precisa janelinhar
    # por enquanto passa direto, se der problema implemento sliding window depois
    if len(texto.split()) > 600:
        # aviso rapido, 600 palavras eh ~850 tokens, pode truncar
        print(f"texto grande ({len(texto.split())} palavras), gliner pode truncar ??????")

    try:
        spans = m.predict_entities(texto, labels_list, threshold=threshold)
    except Exception as e:
        print(f"gliner falhou: {e}")
        return []

    return spans


def extrai_por_label(
    texto: str,
    checkpoint_path: str | Path | None = None,
    labels: Iterable[str] | None = None,
) -> dict[str, list[dict]]:
    # separa spans por label num dict {label: [spans]}
    # se labels=None, usa LABELS_PADRAO (peixe, bacia, rio, municipio)
    # passar labels explicito eh util pra testes ou pra rodar so com subset
    labels_list = list(labels) if labels is not None else list(LABELS_PADRAO)
    spans = extrai_spans(texto, labels=labels_list, checkpoint_path=checkpoint_path)
    out: dict[str, list[dict]] = {lbl: [] for lbl in labels_list}
    for s in spans:
        lbl = s.get("label", "")
        if lbl in out:
            out[lbl].append(s)
    return out
