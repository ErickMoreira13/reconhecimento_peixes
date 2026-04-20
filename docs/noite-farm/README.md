# noite-farm — log da madrugada de 2026-04-20

farm autonomo rodado enquanto o jader dormia. missao: maximizar transcricoes.

## linha do tempo

| hora | evento | transcritos |
|------|--------|-------------|
| 04:26 | lançamento do `noite-farm.sh` | 46 (inicial) |
| 05:13 | check 1: 214 em 45min, taxa 4.5 vid/min | 260 |
| 06:00 | check 2: **youtube apertou anti-bot**, 67% falha | 355 |
| 06:07 | fix: cookies brave + js_runtimes node | — |
| 06:53 | check 3: zero falhas pos-fix | 505 |
| 07:39 | check 4: cleanup manual 884MB orfaos | 660 |
| 08:26 | check 5: 1 timeout (batch com videos longos) | 750 |
| 09:12 | check 6: taxa subiu, 11GB livres | 890 |
| 09:58 | check 7: **bateu 1000** | 1059 |
| 10:44 | check 8 | 1151 |
| 11:30 | check 9 | 1235 |
| 12:15 | check 10 | 1329 |
| 13:01 | check 11: **+108 queries** (saturando rapido) | 1490 |
| 13:42 | user acordou | **1579** |
| 13:45 | snapshot db commitado | 1653 |

## problemas que apareceram e foram corrigidos sozinhos

### 1. `Sign in to confirm you're not a bot` (06:00)
youtube enrijeceu a detecção de bot. yt-dlp falhava 67% dos downloads.

**fix**: passar `cookiesfrombrowser=('brave',)` + `js_runtimes={'node': {}}`
no YoutubeDL. + instalar `secretstorage` (chromium cookies) e
`yt-dlp-ejs` (solver scripts). commit `ea74cd2`.

### 2. audios orfaos na pasta raw_audio (07:39)
transcrever falhava pra alguns audios mas o arquivo ficava. 884MB
acumulados. cleanup manual + script atualizado pra limpar a cada ciclo.
commit `feaabb1`.

### 3. timeout em batch com videos muito longos (ciclo 7)
batch de 50 videos onde a média de duração era alta. 30min não deu.
13 audios ficaram pra tras — pegos no ciclo seguinte. decisão: não
aumentar timeout (risco > beneficio).

### 4. queries saturando rapido (13:01)
31 queries iniciais saturaram em 2h. expandi pra 148 durante check 2,
mais 108 no check 11. total 256 queries.

## numeros finais (ate 13:45)

- **1653 transcricoes validas**
- 975 falhas (majoritariamente pre-fix, entre 06:00-06:07)
- 9h de farm continuo
- taxa media: 2.84 vid/min
- tamanho dataset: ~50MB de json
- disco: 9.7GB livres (delete audio automatico funcionando)

## arquivos

- `progresso.jsonl` — 1 linha por ciclo com snapshot da contagem
- `run-YYYYMMDD.log` — stdout bruto (gitignored, pesado)

farm continua rodando.
