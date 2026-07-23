# Validacao das metricas do SaaS

Fonte SaaS local: `Projeto_CR/app/visualization/public/graph-structural-metrics.json`.

Fonte recalculada: `C:/Users/Micro/Desktop/UFABC/CR/Projeto_CR/data/processed/reddit_graph.duckdb`, tabela `edges_by_layer`.

Esta validacao cobre dois escopos: `full` e `largest_component`.
No escopo `largest_component`, o grafo e segmentado antes do calculo; portanto `sampled_64`, centralidades medias, conectividade, caminho medio e diametro sao calculados somente na componente gigante.

## Formulas

| Metrica | Forma de calculo |
| --- | --- |
| Vertices | `n = |V|` no escopo analisado. |
| Arestas | `m = |E|` no escopo analisado. |
| Peso total | Soma dos pesos das arestas do escopo. |
| Densidade | `m / (n * (n - 1))` para grafo dirigido sem laco. |
| Grau medio | `2m / n`. |
| Reciprocidade | Fracao de arestas `i -> j` que possuem volta `j -> i`. |
| Componentes fracas | Componentes conexas ignorando a direcao. |
| Conectividade de vertices | `vertex_connectivity(G)` no grafo nao dirigido do escopo. |
| Conectividade de arestas | `edge_connectivity(G)` no grafo nao dirigido do escopo. |
| Pontos de articulacao | Vertices cuja remocao aumenta o numero de componentes conexas do escopo. |
| Caminho medio e diametro | Exatos ate 2.500 vertices; acima disso usam amostra deterministica de 64 fontes (`sampled_64`). |
| Centralidades medias | Media aritmetica das centralidades dos vertices do escopo. |

## Camada combined / full

| Metrica | SaaS | Recalculado | Status |
| --- | ---: | ---: | --- |
| Vertices | 57559 | 57559 | OK |
| Arestas | 274698 | 274698 | OK |
| Peso total | 671476 | 671476 | OK |
| Grau medio | 9.54491912646 | 9.54491912646 | OK |
| Densidade | 8.2915660086e-05 | 8.2915660086e-05 | OK |
| Reciprocidade | 0.181348244254 | 0.181348244254 | OK |
| Numero de componentes conexas | 619 | 619 | OK |
| Vertices na maior componente | 56234 | 56234 | OK |
| Participacao da maior componente | 0.976980142115 | 0.976980142115 | OK |
| Conectividade de vertices | 0 | 0 | OK |
| Conectividade de arestas | 0 | 0 | OK |
| Pontos de articulacao | 7125 | 7125 | OK |
| Clustering medio | 0.211414673654 | 0.211414673654 | OK |
| Caminho medio | 3.07256415272 | 3.07256415272 | OK |
| Diametro | 13 | 13 | OK |
| Modularidade | 0.555827586212 | 0.555827586212 | OK |
| Comunidades | 701 | 701 | OK |
| Centralidade de grau media | 0.000150794710794 | 0.000150794710794 | OK |
| Centralidade de intermediacao media | 0.000120598183405 | 0.000120598183405 | OK |
| Centralidade de proximidade media | 0.328616539821 | 0.328616539821 | OK |
| Centralidade de autovetor media | 0.000951674095954 | 0.000951674095954 | OK |
| PageRank medio | 1.7373477649e-05 | 1.7373477649e-05 | OK |
| Radialidade media | 0.823291489542 | 0.823291489542 | OK |
| Excentricidade media | 5.01386403516 | 5.01386403516 | OK |
| Metodo de caminhos | sampled_64 | sampled_64 | OK |
| Metodo de centralidade | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | OK |

Tempo de recalc.: 11.141 s.

## Camada combined / largest_component

| Metrica | SaaS | Recalculado | Status |
| --- | ---: | ---: | --- |
| Vertices | 56234 | 56234 | OK |
| Arestas | 273958 | 273958 | OK |
| Peso total | 670638 | 670638 | OK |
| Grau medio | 9.74350037344 | 9.74350037344 | OK |
| Densidade | 8.66350752533e-05 | 8.66350752533e-05 | OK |
| Reciprocidade | 0.181640981464 | 0.181640981464 | OK |
| Numero de componentes conexas | 1 | 1 | OK |
| Vertices na maior componente | 56234 | 56234 | OK |
| Participacao da maior componente | 1 | 1 | OK |
| Conectividade de vertices | 1 | 1 | OK |
| Conectividade de arestas | 1 | 1 | OK |
| Pontos de articulacao | 7056 | 7056 | OK |
| Clustering medio | 0.216263894931 | 0.216263894931 | OK |
| Caminho medio | 3.07256415272 | 3.07256415272 | OK |
| Diametro | 13 | 13 | OK |
| Modularidade | 0.555156281887 | 0.555156281887 | OK |
| Comunidades | 83 | 83 | OK |
| Centralidade de grau media | 0.000157533670408 | 0.000157533670408 | OK |
| Centralidade de intermediacao media | 0.000125903008362 | 0.000125903008362 | OK |
| Centralidade de proximidade media | 0.333160021791 | 0.333160021791 | OK |
| Centralidade de autovetor media | 0.000974097686258 | 0.000974097686258 | OK |
| PageRank medio | 1.77828360067e-05 | 1.77828360067e-05 | OK |
| Radialidade media | 0.840572868498 | 0.840572868498 | OK |
| Excentricidade media | 5.06247110289 | 5.06247110289 | OK |
| Metodo de caminhos | sampled_64 | sampled_64 | OK |
| Metodo de centralidade | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | OK |

Tempo de recalc.: 19.35 s.

## Camada title / full

| Metrica | SaaS | Recalculado | Status |
| --- | ---: | ---: | --- |
| Vertices | 40964 | 40964 | OK |
| Arestas | 163785 | 163785 | OK |
| Peso total | 384915 | 384915 | OK |
| Grau medio | 7.99653354165 | 7.99653354165 | OK |
| Densidade | 9.76067859e-05 | 9.76067859e-05 | OK |
| Reciprocidade | 0.120926824801 | 0.120926824801 | OK |
| Numero de componentes conexas | 595 | 595 | OK |
| Vertices na maior componente | 39710 | 39710 | OK |
| Participacao da maior componente | 0.969387755102 | 0.969387755102 | OK |
| Conectividade de vertices | 0 | 0 | OK |
| Conectividade de arestas | 0 | 0 | OK |
| Pontos de articulacao | 5642 | 5642 | OK |
| Clustering medio | 0.177563522538 | 0.177563522538 | OK |
| Caminho medio | 3.07085413571 | 3.07085413571 | OK |
| Diametro | 12 | 12 | OK |
| Modularidade | 0.501267951164 | 0.501267951164 | OK |
| Comunidades | 662 | 662 | OK |
| Centralidade de grau media | 0.000183410293102 | 0.000183410293102 | OK |
| Centralidade de intermediacao media | 0.000150003454429 | 0.000150003454429 | OK |
| Centralidade de proximidade media | 0.332632203503 | 0.332632203503 | OK |
| Centralidade de autovetor media | 0.00123182172935 | 0.00123182172935 | OK |
| PageRank medio | 2.4411678547e-05 | 2.4411678547e-05 | OK |
| Radialidade media | 0.808309980979 | 0.808309980979 | OK |
| Excentricidade media | 4.03725222146 | 4.03725222146 | OK |
| Metodo de caminhos | sampled_64 | sampled_64 | OK |
| Metodo de centralidade | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | OK |

Tempo de recalc.: 4.482 s.

## Camada title / largest_component

| Metrica | SaaS | Recalculado | Status |
| --- | ---: | ---: | --- |
| Vertices | 39710 | 39710 | OK |
| Arestas | 163102 | 163102 | OK |
| Peso total | 384154 | 384154 | OK |
| Grau medio | 8.21465625787 | 8.21465625787 | OK |
| Densidade | 0.000103435697926 | 0.000103435697926 | OK |
| Reciprocidade | 0.121200230531 | 0.121200230531 | OK |
| Numero de componentes conexas | 1 | 1 | OK |
| Vertices na maior componente | 39710 | 39710 | OK |
| Participacao da maior componente | 1 | 1 | OK |
| Conectividade de vertices | 1 | 1 | OK |
| Conectividade de arestas | 1 | 1 | OK |
| Pontos de articulacao | 5589 | 5589 | OK |
| Clustering medio | 0.182994513655 | 0.182994513655 | OK |
| Caminho medio | 3.07085413571 | 3.07085413571 | OK |
| Diametro | 12 | 12 | OK |
| Modularidade | 0.500612896139 | 0.500612896139 | OK |
| Comunidades | 73 | 73 | OK |
| Centralidade de grau media | 0.000194334965418 | 0.000194334965418 | OK |
| Centralidade de intermediacao media | 0.000158796294643 | 0.000158796294643 | OK |
| Centralidade de proximidade media | 0.33416916668 | 0.33416916668 | OK |
| Centralidade de autovetor media | 0.00127072136291 | 0.00127072136291 | OK |
| PageRank medio | 2.5182573659e-05 | 2.5182573659e-05 | OK |
| Radialidade media | 0.827430207359 | 0.827430207359 | OK |
| Excentricidade media | 4.41659531604 | 4.41659531604 | OK |
| Metodo de caminhos | sampled_64 | sampled_64 | OK |
| Metodo de centralidade | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | OK |

Tempo de recalc.: 10.167 s.

## Camada body / full

| Metrica | SaaS | Recalculado | Status |
| --- | ---: | ---: | --- |
| Vertices | 35776 | 35776 | OK |
| Arestas | 137821 | 137821 | OK |
| Peso total | 286561 | 286561 | OK |
| Grau medio | 7.70466234347 | 7.70466234347 | OK |
| Densidade | 0.000107682213046 | 0.000107682213046 | OK |
| Reciprocidade | 0.195775680049 | 0.195775680049 | OK |
| Numero de componentes conexas | 497 | 497 | OK |
| Vertices na maior componente | 34671 | 34671 | OK |
| Participacao da maior componente | 0.969113372093 | 0.969113372093 | OK |
| Conectividade de vertices | 0 | 0 | OK |
| Conectividade de arestas | 0 | 0 | OK |
| Pontos de articulacao | 5055 | 5055 | OK |
| Clustering medio | 0.180901018438 | 0.180901018438 | OK |
| Caminho medio | 3.21402103764 | 3.21402103764 | OK |
| Diametro | 9 | 9 | OK |
| Modularidade | 0.659892735844 | 0.659892735844 | OK |
| Comunidades | 572 | 572 | OK |
| Centralidade de grau media | 0.000194282867604 | 0.000194282867604 | OK |
| Centralidade de intermediacao media | 0.000160545402348 | 0.000160545402348 | OK |
| Centralidade de proximidade media | 0.297414280285 | 0.297414280285 | OK |
| Centralidade de autovetor media | 0.00114782508329 | 0.00114782508329 | OK |
| PageRank medio | 2.79516994633e-05 | 2.79516994633e-05 | OK |
| Radialidade media | 0.717835766524 | 0.717835766524 | OK |
| Excentricidade media | 5.40275603757 | 5.40275603757 | OK |
| Metodo de caminhos | sampled_64 | sampled_64 | OK |
| Metodo de centralidade | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | OK |

Tempo de recalc.: 4.807 s.

## Camada body / largest_component

| Metrica | SaaS | Recalculado | Status |
| --- | ---: | ---: | --- |
| Vertices | 34671 | 34671 | OK |
| Arestas | 137039 | 137039 | OK |
| Peso total | 285657 | 285657 | OK |
| Grau medio | 7.90510801534 | 7.90510801534 | OK |
| Densidade | 0.000114005018969 | 0.000114005018969 | OK |
| Reciprocidade | 0.196571778837 | 0.196571778837 | OK |
| Numero de componentes conexas | 1 | 1 | OK |
| Vertices na maior componente | 34671 | 34671 | OK |
| Participacao da maior componente | 1 | 1 | OK |
| Conectividade de vertices | 1 | 1 | OK |
| Conectividade de arestas | 1 | 1 | OK |
| Pontos de articulacao | 5006 | 5006 | OK |
| Clustering medio | 0.186170425879 | 0.186170425879 | OK |
| Caminho medio | 3.21402103764 | 3.21402103764 | OK |
| Diametro | 9 | 9 | OK |
| Modularidade | 0.658544806154 | 0.658544806154 | OK |
| Comunidades | 76 | 76 | OK |
| Centralidade de grau media | 0.000205599868564 | 0.000205599868564 | OK |
| Centralidade de intermediacao media | 0.000169709497619 | 0.000169709497619 | OK |
| Centralidade de proximidade media | 0.318956957151 | 0.318956957151 | OK |
| Centralidade de autovetor media | 0.00118440743503 | 0.00118440743503 | OK |
| PageRank medio | 2.88425485276e-05 | 2.88425485276e-05 | OK |
| Radialidade media | 0.7539999857 | 0.7539999857 | OK |
| Excentricidade media | 4.97060944305 | 4.97060944305 | OK |
| Metodo de caminhos | sampled_64 | sampled_64 | OK |
| Metodo de centralidade | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | degree_exact;pagerank_weighted;eigenvector_weighted;betweenness_proxy_degree_clustering;distance_sampled_64 | OK |

Tempo de recalc.: 7.568 s.
