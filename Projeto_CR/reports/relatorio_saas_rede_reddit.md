# Relatorio tecnico - SaaS de analise da rede Reddit SNAP

**Universidade Federal do ABC**  
**Disciplina:** BCM0506 - Comunicacao e Redes - 2026.2  
**Projeto:** Analise de Redes Complexas no Reddit: comunidades-ponte e influencia entre subreddits  
**Data:** 06/07/2026  
**Artefato analisado:** `Projeto_CR/app/visualization/index.html`

## Resumo

Este relatorio apresenta a versao atual do SaaS local desenvolvido para explorar a rede Reddit Hyperlink Network da SNAP. A aplicacao transforma os dados de hyperlinks entre subreddits em uma visualizacao interativa de grafo dirigido, ponderado e assinado por sentimento. O objetivo e apoiar a pergunta principal do projeto: quais subreddits funcionam como pontes entre comunidades e como essa estrutura aparece nas camadas `title`, `body` e `combined`. A versao analisada integra 57.559 vertices, 274.698 arestas agregadas e 701 comunidades detectadas, permitindo filtros por camada, sinal, peso minimo, busca por subreddit, visualizacao de comunidades, rede ego e exportacao de resultados.

**Palavras-chave:** redes complexas; Reddit; SNAP; grafos dirigidos; centralidade; comunidades; SaaS.

## 1. Introducao

O projeto investiga a rede de hyperlinks entre subreddits a partir da base publica SNAP Reddit Hyperlink Network. Cada subreddit e modelado como vertice e cada hyperlink de um subreddit para outro e modelado como aresta dirigida. Quando ha multiplos hyperlinks entre o mesmo par origem-destino, essas ocorrencias sao agregadas em um peso.

A proposta revisada substituiu a coleta direta pela API do Reddit pela base SNAP. Essa decisao reduziu riscos de autenticacao, limites de requisicao e incompletude dos dados, mantendo a pergunta cientifica central. O SaaS local foi criado como uma camada demonstravel para navegar pelos resultados, aproximando a analise estatistica do grafo de uma experiencia visual adequada para apresentacao em aula.

## 2. Alinhamento com as aulas

O relatorio segue o formato academico compacto demonstrado nos trabalhos da Aula 1: titulo, resumo, introducao, fundamentacao, metodologia, resultados, discussao e referencias.

Os conteudos das aulas foram usados da seguinte forma:

| Aula | Conteudo usado | Aplicacao no projeto |
| --- | --- | --- |
| Aula 1 | proposta, escopo e estrutura de trabalho | organizacao do relatorio e justificativa do problema |
| Aula 2 | redes como vertices e arestas; propriedades estatisticas | definicao da rede Reddit e leitura de grau, caminhos e distribuicoes |
| Aula 3 | teoria dos grafos; grafo `G = (V, E)`; direcao e caminhos | modelagem subreddit -> subreddit e interpretacao de arestas dirigidas |
| Aula 4 | grafos dirigidos, ponderados e alternativa bipartida | escolha da rede projetada entre subreddits e discussao de alternativas |
| Aula 5 | vizinhanca, busca e rede ego | ferramenta de rede ego para analisar um subreddit central |
| Aula 6 | centralidades: grau, forca, intermediacao, proximidade e PageRank | rankings de hubs, emissores, receptores e possiveis pontes |
| Aulas 7 e 8 | mundo pequeno, grafos aleatorios, leis de potencia e redes sem escala | interpretacao da rede esparsa, desigual e concentrada em poucos hubs |

## 3. Dados e modelagem

Os dados brutos usados sao os arquivos `soc-redditHyperlinks-title.tsv` e `soc-redditHyperlinks-body.tsv`, baixados em 22/06/2026. A base `title` possui 384.915 hyperlinks e a base `body` possui 286.561 hyperlinks. A versao combinada agrega as duas camadas por par `source -> target`.

### 3.1 Definicao do grafo

Formalmente, o grafo e definido como `G = (V, E)`, em que:

- `V` e o conjunto de subreddits.
- `E` e o conjunto de hyperlinks dirigidos entre subreddits.
- `weight` representa a quantidade de hyperlinks agregados entre origem e destino.
- `positive` e `negative` preservam o sinal original da interacao.
- `layer` diferencia links extraidos de titulos, corpos de postagem ou da combinacao dos dois.

Essa modelagem e coerente com a proposta porque a pergunta do projeto nao e sobre usuarios individuais, mas sobre fluxo e influencia entre comunidades.

## 4. SaaS desenvolvido

O SaaS atual esta implementado como uma aplicacao web local em `Projeto_CR/app/visualization`. Ele carrega arquivos JSON exportados a partir do banco DuckDB e renderiza a rede em canvas.

### 4.1 Funcionalidades implementadas

- Mapa de comunidades para a rede combinada.
- Alternancia entre camadas `title`, `body` e `combined`.
- Filtro por sinal: todos, positivo/neutro ou negativo.
- Filtro por peso minimo da aresta.
- Busca por subreddit.
- Painel com metricas globais: vertices, arestas, comunidades e camada ativa.
- Painel de selecao com comunidade, papel estrutural, forca total, entrada, saida, PageRank e negatividade.
- Destaques por popularidade, ponte e influencia mista.
- Aba de analises com distribuicoes estruturais, rede ego e principais arestas por peso.
- Exportacao de analises em JSON e CSV.

### 4.2 Arquitetura de dados

O pipeline materializa os dados em `Projeto_CR/data/processed/reddit_graph.duckdb` e exporta os ativos do SaaS para:

- `app/visualization/public/graph-core.json`
- `app/visualization/public/edges-title.json`
- `app/visualization/public/edges-body.json`
- `app/visualization/public/edges-combined.json`
- `app/visualization/public/graph-data-summary.json`

O DuckDB armazena as tabelas `edges_raw`, `edges_combined`, `nodes`, `communities`, `node_strengths` e `graph_stats`. O frontend consome esses dados sem recalcular as metricas pesadas no navegador.

## 5. Resultados principais

### 5.1 Estatisticas globais

| Camada | Vertices | Arestas agregadas | Peso total | Positivos/neutros | Negativos | Negativos (%) | Comunidades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| combined | 57.559 | 274.698 | 671.476 | 609.299 | 62.177 | 9,26% | 701 |
| title | 40.964 | 163.785 | 384.915 | 343.808 | 41.107 | 10,68% | - |
| body | 35.776 | 137.821 | 286.561 | 265.491 | 21.070 | 7,35% | - |

A rede combinada e grande e esparsa. O numero de arestas observadas e alto em termos absolutos, mas pequeno diante do total de pares possiveis entre mais de 57 mil subreddits. Esse comportamento e esperado em redes reais: muitos vertices possuem poucas conexoes e poucos vertices concentram grande parte da atividade.

### 5.2 Subreddits com maior forca total

| Subreddit | Comunidade | Papel | Entrada | Saida | Forca total | PageRank |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| subredditdrama | community_036 | hub | 2.986 | 23.914 | 26.900 | 0,001386 |
| askreddit | community_021 | hub | 20.854 | 1.338 | 22.192 | 0,022592 |
| bestof | community_021 | emissor | 1.233 | 16.105 | 17.338 | 0,000764 |
| iama | community_007 | hub | 11.210 | 1.183 | 12.393 | 0,018799 |
| pics | community_021 | hub | 9.926 | 180 | 10.106 | 0,011103 |
| todayilearned | community_021 | hub | 8.704 | 918 | 9.622 | 0,006889 |
| funny | community_021 | hub | 8.336 | 719 | 9.055 | 0,009467 |
| videos | community_021 | hub | 7.847 | 218 | 8.065 | 0,009018 |
| worldnews | community_029 | hub | 7.762 | 210 | 7.972 | 0,005751 |
| titlegore | community_021 | emissor | 20 | 6.960 | 6.980 | 0,000015 |

O ranking mostra diferencas importantes entre popularidade e emissao. `askreddit`, `iama`, `pics`, `funny` e `videos` recebem muitos links e tambem aparecem com PageRank alto. `subredditdrama`, `bestof` e `titlegore` se destacam pelo peso de saida, indicando papel mais ativo em apontar para outras comunidades.

### 5.3 Subreddits com maior potencial de ponte

Para estimar pontes no SaaS, foi calculado o peso das arestas que conectam comunidades diferentes e a quantidade de comunidades distintas alcancadas por cada subreddit.

| Subreddit | Comunidade | Peso entre comunidades | Comunidades conectadas | Escore de ponte |
| --- | --- | ---: | ---: | ---: |
| subredditdrama | community_036 | 22.177 | 46 | 107.561,72 |
| bestof | community_021 | 11.321 | 41 | 53.635,16 |
| askreddit | community_021 | 10.647 | 45 | 51.410,54 |
| iama | community_007 | 10.080 | 43 | 48.224,63 |
| todayilearned | community_021 | 4.952 | 40 | 23.341,61 |
| pics | community_021 | 4.350 | 43 | 20.811,22 |
| worldnews | community_029 | 4.194 | 37 | 19.450,04 |
| gaming | community_024 | 3.968 | 39 | 18.605,47 |
| titlegore | community_021 | 3.883 | 43 | 18.577,01 |
| videos | community_021 | 3.833 | 43 | 18.337,80 |

Esse resultado reforca a hipotese da proposta: alguns subreddits nao sao apenas populares; eles tambem atravessam fronteiras entre comunidades. `subredditdrama` e o caso mais forte, pois combina alta saida ponderada com conexoes para muitas comunidades distintas.

### 5.4 Maiores comunidades detectadas

| ID | Rotulo operacional | Vertices | Peso interno | Top subreddits |
| ---: | --- | ---: | ---: | --- |
| 21 | popular / memes | 8.655 | 88.245 | askreddit, bestof, pics, todayilearned, funny, videos |
| 29 | news / politics | 5.458 | 54.434 | worldnews, news, conspiracy, politics, technology |
| 24 | gaming | 4.435 | 32.782 | gaming, pcmasterrace, games, buildapc, techsupport |
| 1 | community_001 | 2.917 | 13.871 | motorcycles, bicycling, cars, seattle, assistance |
| 5 | sports | 2.748 | 17.197 | science, fitnesscirclejerk, fitness, drugs, space |
| 0 | technology | 2.574 | 14.394 | sysadmin, programming, entrepreneur, linux, diy |
| 7 | music / media | 2.454 | 12.669 | iama, books, television, episodehub, asoiaf |
| 36 | controversial topics | 2.451 | 27.088 | subredditdrama, drama, legaladvice, relationships |

Os rotulos sao interpretativos e devem ser tratados como apoio visual, nao como classificacao definitiva. Eles foram inferidos a partir dos principais subreddits de cada comunidade.

### 5.5 Arestas mais fortes na rede combinada

| Origem | Destino | Peso | Positivos/neutros | Negativos | Balanco |
| --- | --- | ---: | ---: | ---: | ---: |
| trendingsubreddits | changelog | 548 | 548 | 0 | 1,0000 |
| moronicmondayandroid | android | 340 | 340 | 0 | 1,0000 |
| goodshibe | dogecoin | 286 | 286 | 0 | 1,0000 |
| streetfighter | sf4 | 279 | 240 | 39 | 0,7204 |
| buildapc | buildapcforme | 245 | 244 | 1 | 0,9918 |
| mushroomkingdom | gamesale | 243 | 243 | 0 | 1,0000 |
| summonerschool | leagueoflegends | 220 | 216 | 4 | 0,9636 |
| evenwithcontext | askreddit | 214 | 142 | 72 | 0,3271 |

As arestas mais fortes tendem a aparecer entre comunidades relacionadas por tema ou por pratica recorrente de referencia. A aresta `evenwithcontext -> askreddit` e um caso interessante por apresentar proporcao negativa maior que as demais do ranking.

## 6. Discussao

O SaaS torna visivel uma caracteristica central de redes reais: a estrutura nao e homogenea. Ha comunidades muito grandes, como `popular / memes`, `news / politics` e `gaming`, e ha subreddits que funcionam como articuladores entre blocos. A leitura por forca total identifica os vertices de maior volume, enquanto a leitura por ponte destaca vertices que atravessam comunidades.

O caso de `subredditdrama` e especialmente relevante. Ele possui a maior forca total na rede combinada e o maior escore de ponte, mas nao possui o maior PageRank. Isso mostra por que a Aula 6 recomenda comparar centralidades em vez de usar apenas uma metrica: grau/forca, PageRank e ponte capturam aspectos diferentes de influencia estrutural.

Tambem e importante separar as camadas. A camada `title` possui maior percentual de links negativos (10,68%) que a camada `body` (7,35%). Isso sugere que referencias no titulo podem concentrar interacoes mais marcadas, enquanto referencias no corpo sao mais numerosas em alguns contextos, mas proporcionalmente menos negativas.

## 7. Limitacoes

- A centralidade mede importancia dentro da modelagem escolhida, nao importancia social absoluta.
- Os rotulos de comunidades sao interpretativos e podem precisar de revisao manual.
- A visualizacao completa exige filtros, pois a rede possui dezenas de milhares de vertices.
- O escore de ponte usado no SaaS e uma aproximacao operacional baseada em conexoes entre comunidades; ele nao substitui uma centralidade de intermediacao calculada em todos os caminhos do grafo.
- A base SNAP cobre um periodo historico especifico e nao representa necessariamente o Reddit atual.

## 8. Conclusao

A versao atual do SaaS cumpre o papel de demonstrar, de forma interativa, a modelagem de redes complexas proposta para o projeto. A aplicacao conecta os conceitos das aulas com um caso real: vertices, arestas dirigidas, pesos, sinais, comunidades, redes ego e centralidades.

Os resultados indicam que `subredditdrama`, `bestof`, `askreddit` e `iama` sao vertices centrais para a circulacao entre comunidades, mas por motivos estruturais diferentes. `askreddit` lidera em PageRank, enquanto `subredditdrama` lidera em forca total e escore de ponte. Essa diferenca sera importante para a versao final do relatorio, pois mostra que influencia em redes complexas depende da metrica observada.

## Referencias

[1] J. Leskovec e A. Krevl, "SNAP Datasets: Stanford Large Network Dataset Collection", Stanford University. Disponivel em: https://snap.stanford.edu/data/soc-RedditHyperlinks.html

[2] UFABC, "BCM0506 - Comunicacao e Redes: materiais das Aulas 1 a 8", 2026.2.

[3] Projeto_CR, `Proposta_Revisada_RedeReddit_SNAP.md`, 22/06/2026.

[4] Projeto_CR, `Cronograma_Projeto_Reddit_SNAP.md`, 22/06/2026.

[5] Projeto_CR, `Cronograma_Implementacao_SaaS_Grafos.md`, 05/07/2026.

[6] Projeto_CR, `reports/duckdb_graph_store_summary.md`, 2026.

[7] Projeto_CR, `app/visualization/public/graph-data-summary.json`, 2026.

