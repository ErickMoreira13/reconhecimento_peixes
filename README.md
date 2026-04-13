# 🎣 Sistema de Análise de Vídeos sobre Pesca com Ceva

## 📋 Visão Geral

Este projeto é um sistema automatizado de mineração e análise de dados que coleta informações de vídeos do YouTube sobre técnicas de pesca com ceva no Brasil. Utiliza inteligência artificial para transcrever e analisar o conteúdo dos vídeos, extraindo insights valiosos sobre métodos, materiais e localidades.

## 🎯 Objetivo do Projeto

### Por que este projeto existe?

A pesca com ceva é uma técnica amplamente utilizada no Brasil, mas há pouca documentação sistematizada sobre:
- Quais métodos são mais eficazes em diferentes regiões
- Tipos de ceva e grãos mais utilizados
- Distribuição geográfica das técnicas
- Evolução das práticas ao longo do tempo

Este sistema visa preencher essa lacuna, criando uma base de dados estruturada a partir do conhecimento compartilhado em vídeos do YouTube.

## 🔧 Como Funciona

### 1. **Coleta de Dados** 
```
YouTube API → Busca vídeos → Filtra por relevância → Download de áudio
```
- Busca vídeos usando palavras-chave específicas ("Pesca com ceva")
- Filtra vídeos dos últimos 10 anos
- Utiliza múltiplas chaves API para contornar limites de cota
- Baixa apenas o áudio para otimizar processamento

### 2. **Transcrição com IA**
```
Áudio → Whisper AI → Texto transcrito → Segmentação
```
- Usa o modelo Whisper (OpenAI) para transcrever áudio em texto
- Modelo "medium" para balance entre precisão e velocidade
- Processa áudios em chunks de 10 minutos para eficiência
- Gera transcrições completas com timestamps

### 3. **Análise de Conteúdo**
```
Texto → NLP → Extração de entidades → Classificação
```
O sistema analisa as transcrições buscando:

**Tipos de Ceva:**
- Galão plástico perfurado
- Saco de ráfia
- Garrafa PET perfurada
- Cano de PVC perfurado

**Grãos Utilizados:**
- Soja
- Milho

**Localização:**
- Identifica os 27 estados brasileiros mencionados
- Mapeia distribuição geográfica das técnicas

...

## 📊 Estrutura de Dados Coletados

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `video_id` | ID único do YouTube | "dQw4w9WgXcQ" |
| `title` | Título do vídeo | "Pesca com ceva no Rio Paraná" |
| `channel` | Nome do canal | "Pescador Experiente" |
| `published_at` | Data de publicação | "2024-01-15" |
| `transcription` | Texto completo transcrito | "Hoje vamos usar milho..." |
| `ceva_types` | Tipos de ceva identificados | ["garrafa pet", "saco de ráfia"] |
| `grains` | Grãos mencionados | ["milho", "soja"] |
| `states` | Estados brasileiros citados | ["São Paulo", "Paraná"] |
| `relevance_score` | Score de relevância (0-1) | 0.85 |


## 🛠️ Tecnologias Utilizadas

| Tecnologia | Função | Por quê? |
|------------|--------|----------|
| **Whisper** | Transcrição de áudio | Melhor modelo open-source para português |
| **YouTube API** | Coleta de metadados | Acesso oficial e estruturado |
| **yt-dlp** | Download de áudio | Mais robusto e mantido que youtube-dl |
| **Sentence Transformers** | Análise semântica | Embeddings multilíngues de alta qualidade |
| **spaCy** | Processamento de texto | NER e análise linguística em português |
| **pandas/CSV** | Armazenamento | Formato universal para análise de dados |

## 📈 Casos de Uso

### Pesquisa Acadêmica
- Estudos sobre práticas de pesca no Brasil
- Análise de disseminação de conhecimento tradicional
- Mapeamento de técnicas regionais

### Inteligência de Mercado
- Identificar demanda por tipos de equipamentos
- Tendências de consumo de insumos (grãos)
- Oportunidades regionais

### Educação e Divulgação
- Criar guias baseados em dados reais
- Identificar melhores práticas por região
- Documentar evolução das técnicas

## ⚙️ Configurações

Principais parâmetros ajustáveis em `tWhisperTesteTranscricao10.py`:

```python
SEARCH_QUERY = "Pesca com ceva"  # Termo de busca
MAX_RESULTS = 50000              # Quantidade de vídeos
ULTIMOS_ANOS = 10                # Período de análise
BATCH_SIZE = 100                 # Vídeos por lote
MEMORY_LIMIT_GB = 8              # Limite de RAM
```

## 📁 Estrutura de Arquivos

```
projeto/
└── src/
    ├── agentes/
    │   ├── agente_base.py
    │   ├── bacia.py
    │   ├── ceva.py
    │   ├── cidade.py
    │   ├── especies.py
    │   ├── estado.py
    │   ├── gemma.py
    │   ├── graos.py
    │   ├── pais.py
    │   └── rio.py
    │
    ├── pipelines/
    │   ├── agentes_pipeline.py
    │   ├── full_pipeline.py
    │   └── video_pipeline.py
    │
    ├── extrair_audio.py
    ├── main.py
    ├── processar_audio.py
    │
    ├── README.md
    └── requirements.txt
```

## 🔒 Considerações Éticas

- ✅ Usa apenas dados públicos do YouTube
- ✅ Respeita limites de API e termos de serviço
- ✅ Não baixa vídeos completos, apenas áudio
- ✅ Preserva atribuição aos criadores originais
- ✅ Fins educacionais e de pesquisa

## 📝 Limitações Conhecidas

- Dependente da qualidade do áudio dos vídeos
- Precisão da transcrição varia com sotaques regionais
- Limites de cota da API do YouTube
- Requer conexão estável com internet
- Processamento intensivo de CPU/GPU

## 🎯 Resultados Esperados

Após processar 50.000 vídeos, o sistema fornecerá:
- Base de dados com milhares de técnicas documentadas
- Mapa de práticas por região do Brasil
- Tendências temporais (últimos 10 anos)
- Ranking de métodos mais populares
- Correlações entre técnicas e localidades

---

### Objetivo do Trabalho: 

O projeto visa minerar dados em texto via processamento de vídeo com Inteligência Artificial de peixes pescados na bacia hidrográfica oriundas de gravações de pesca comercial utilizadas em vídeos publicados em mídias de comunicação para ampliar a coleta de dados.
Especificamente, o projeto busca:

Analisar vídeos disponíveis em plataformas virtuais (inicialmente o YouTube) para documentar as espécies de peixes que consomem cevas
Auxiliar no mapeamento do uso de soja e milho e sobrepor no mapa com as áreas de produção de grãos
Catalogar e registrar peixes de locais através de um algoritmo com inteligência artificial para tratamento de informações via processamento de vídeos feitos por profissionais da área de pesca

Porém, o projeto mencionado tem uma limitação importante: o alcance dos dados é limitado, pois o aplicativo usado para coletar os dados é suportado somente para a plataforma Android. Por isso, há a ideia de expandir para outras plataformas ou métodos de coleta, como redes sociais.

**Desenvolvido para análise e pesquisa sobre técnicas tradicionais de pesca no Brasil** 🇧🇷
