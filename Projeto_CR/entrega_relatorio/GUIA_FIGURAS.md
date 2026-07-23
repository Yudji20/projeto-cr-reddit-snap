# Guia das figuras

Este arquivo descreve as imagens em `figuras/` e como cada uma sustenta a analise do relatorio.

## Distribuicao e estrutura global

### `histograma_grau_total_rede_combinada.png`

Mostra a distribuicao do grau total dos subreddits na rede combinada, em escala log-log. Serve para evidenciar que a rede e heterogenea: muitos subreddits possuem poucas conexoes e poucos subreddits concentram grau muito alto.

### `histograma_forca_total_rede_combinada.png`

Mostra a distribuicao da forca total ponderada dos subreddits, tambem em escala log-log. Complementa o histograma de grau, indicando que a concentracao nao ocorre apenas na quantidade de vizinhos, mas tambem no peso das interacoes.

### `barras_papeis_estruturais_rede_combinada.png`

Mostra quantos vertices foram classificados como `hub`, `emissor`, `receptor` e `misto`. Serve para resumir a composicao estrutural da rede e mostrar que hubs sao minoria em relacao ao total de vertices.

## Pontes e comunidades

### `barras_pares_comunidades_externas.png`

Mostra os pares direcionados de comunidades com maior peso de conexoes externas. Ajuda a identificar quais blocos de comunidades mais trocam hyperlinks entre si, como `news / politics`, `popular / memes` e `controversial topics`.

### `barras_subreddits_pontes_entre_comunidades.png`

Mostra os subreddits com maior forca externa, separando entrada externa e saida externa. Serve para distinguir conectores receptores, como `askreddit` e `iama`, de conectores emissores, como `subredditdrama`, `bestof` e `titlegore`.

### `grafo_pontes_entre_comunidades.png`

Visualiza os principais subreddits ponte e as comunidades externas mais conectadas a eles. Serve como representacao visual da analise entre comunidades, destacando os vertices que atravessam fronteiras comunitarias.

### `grafo_backbone_hubs_rede_combinada.png`

Mostra o backbone dos hubs da rede combinada, considerando conexoes fortes entre vertices classificados como hubs. Serve para visualizar a espinha dorsal da rede, isto e, o conjunto de subreddits mais influentes e suas conexoes principais.

## Pontos de articulacao

### `barras_impacto_pontos_articulacao.png`

Mostra os pontos de articulacao com maior impacto, medido pelo numero de componentes formadas apos a remocao do vertice. Sustenta a conclusao de que `askreddit`, `writingprompts`, `iama`, `funny` e `pics` sao vertices criticos para a conectividade da maior componente.

## Analise temporal

### `linhas_crescimento_temporal_rede_combinada.png`

Mostra o crescimento acumulado da rede combinada por ano, incluindo vertices, arestas agregadas e peso total. Serve para demonstrar a expansao da rede entre 2014 e 2017.

### `linhas_hubs_pontos_articulacao_temporal.png`

Mostra a evolucao acumulada da quantidade de hubs e pontos de articulacao ao longo do tempo. Sustenta a ideia de que os pontos de articulacao crescem conforme a rede se expande.

### `linhas_metricas_estruturais_temporais.png`

Mostra metricas estruturais ao longo do tempo, como participacao da maior componente, agrupamento medio e caminho medio. Serve para mostrar que a rede cresce mantendo uma grande componente conectada e caminhos medios baixos.

### `grafo_temporal_acumulado_2014.png`

Snapshot visual da rede acumulada ate 2014, filtrado para os vertices e arestas mais relevantes. Mostra a estrutura inicial da rede e os primeiros hubs centrais.

### `grafo_temporal_acumulado_2015.png`

Snapshot visual da rede acumulada ate 2015. Mostra a expansao da rede em relacao a 2014 e a consolidacao dos hubs principais.

### `grafo_temporal_acumulado_2016.png`

Snapshot visual da rede acumulada ate 2016. Mostra uma rede mais densa em torno dos hubs e a ampliacao das conexoes entre comunidades.

### `grafo_temporal_acumulado_2017.png`

Snapshot visual da rede acumulada ate 2017. Representa a estrutura final analisada no relatorio, com destaque para hubs como `askreddit`, `subredditdrama`, `bestof`, `pics`, `funny`, `videos` e `todayilearned`.

## Observacao metodologica

Os grafos visuais sao recortes filtrados da rede, nao o desenho literal de todos os 57.559 vertices. Essa escolha foi necessaria porque a visualizacao completa ficaria ilegivel. As metricas numericas do relatorio, por outro lado, foram calculadas sobre a rede combinada completa ou sobre a maior componente, conforme indicado em cada secao.
