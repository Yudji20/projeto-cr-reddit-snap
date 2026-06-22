# Inspecao inicial dos dados brutos

Data da inspecao: 22/06/2026

Fonte: SNAP Reddit Hyperlink Network  
URL: https://snap.stanford.edu/data/soc-RedditHyperlinks.html

## Arquivos baixados

| Arquivo | Tamanho | Linhas de dados | Subreddits unicos | Periodo |
| --- | ---: | ---: | ---: | --- |
| `data/raw/soc-redditHyperlinks-title.tsv` | 237.73 MB | 384.915 | 40.964 | 2013-12-31 16:20:20 a 2017-04-29 07:33:59 |
| `data/raw/soc-redditHyperlinks-body.tsv` | 304.16 MB | 286.561 | 35.776 | 2013-12-31 16:39:58 a 2017-04-30 16:58:21 |

## Colunas

Os dois arquivos possuem as mesmas colunas:

- `SOURCE_SUBREDDIT`
- `TARGET_SUBREDDIT`
- `POST_ID`
- `TIMESTAMP`
- `LINK_SENTIMENT`
- `PROPERTIES`

## Distribuicao de sinal

| Arquivo | Positivo/neutro (`1`) | Negativo (`-1`) |
| --- | ---: | ---: |
| `title` | 343.808 | 41.107 |
| `body` | 265.491 | 21.070 |

## Observacoes iniciais

- A base `title` possui mais arestas e mais subreddits unicos.
- A base `body` tem menos arestas, mas intervalo temporal ligeiramente maior no limite final.
- Ambas permitem a separacao entre interacoes positivas/neutras e negativas por meio de `LINK_SENTIMENT`.
- A proxima decisao do cronograma sera escolher se a analise principal usara `title`, `body` ou a combinacao dos dois.

