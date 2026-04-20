# data/ — dataset do projeto

## transcriptions/

1600+ vídeos de pescaria brasileira transcritos com faster-whisper
large-v3-turbo. cada arquivo `<video_id>.json` tem:

```json
{
  "texto": "texto completo em pt-br",
  "segmentos": [
    {"start": 0.0, "end": 3.2, "text": "..."},
    ...
  ],
  "duracao_seg": 234.5,
  "idioma_detectado": "pt"
}
```

coletados via harvester do projeto rodando pela madrugada/manhã de
2026-04-20. fonte: YouTube, queries em `data/queries.yaml`.

## videos.db (NAO commitado)

sqlite com metadados de coleta: video_id, url, title, channel,
published_at, status de pipeline (pendente/baixado/transcrito/extraido/
verificado/falhou). schema em `src/storage/db.py`.

snapshots periódicos podem ser commitados como `videos-snapshot-*.db`.

## queries.yaml

lista de termos de busca do harvester. harvester rotaciona queries
ativas, marca saturada quando dedup rate ≥ 0.8.

## results/ (nao commitado)

CSVs e JSONs de exportação da planilha final. gerados por `make exportar`.

## raw_audio/ (nao commitado)

áudios baixados do YouTube em .opus 32kbps. **deletados automaticamente
após transcrever** pra economizar disco. só ficam os que ainda estão
aguardando whisper.
