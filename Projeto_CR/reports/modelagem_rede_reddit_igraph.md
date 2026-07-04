# Modelagem simples de rede Reddit com igraph

## 1. Ideia central da modelagem de redes

Modelar uma rede e transformar um problema em tres perguntas simples:

1. Quem sao os objetos importantes? Eles viram os nos.
2. Qual relacao liga esses objetos? Ela vira a aresta.
3. A relacao tem direcao, peso ou tipo? Isso vira atributo do grafo.

No Reddit SNAP, a modelagem mais direta e:

- No: subreddit.
- Aresta dirigida: um hyperlink saindo de um subreddit para outro.
- Peso: quantidade de hyperlinks observados naquele par origem -> destino.
- Sinal: quantidade de links positivos/neutros e negativos.

Em notacao de grafos, temos `G = (V, E)`: `V` e o conjunto de subreddits e `E` e o conjunto de links entre eles.

## 2. Por que esta modelagem faz sentido

Se a pergunta for "quais comunidades do Reddit apontam para quais outras comunidades?", uma rede subreddit -> subreddit e adequada. A direcao importa porque `A -> B` nao significa a mesma coisa que `B -> A`. O peso importa porque uma relacao que aparece 200 vezes e mais forte do que uma relacao que aparece uma vez.

Outras modelagens seriam possiveis. Por exemplo, uma rede bipartida `postagem -> subreddit` serviria melhor para estudar posts especificos. Mas, para estudar fluxo entre comunidades, a rede dirigida e ponderada e a escolha mais simples e interpretavel.

## 3. Codigo-base em igraph

O script reprodutivel esta em `Projeto_CR/src/analyze_reddit_igraph.py`. O trecho essencial e:

```python
import igraph as ig
import pandas as pd

edges = pd.read_csv('Projeto_CR/data/processed/reddit_title_edges_gephi.csv')
tuples = list(edges[['Source', 'Target']].itertuples(index=False, name=None))

g = ig.Graph.TupleList(tuples, directed=True, vertex_name_attr='name')
g.es['weight'] = edges['weight'].astype(int).tolist()

in_strength = g.strength(mode='in', weights='weight')
out_strength = g.strength(mode='out', weights='weight')
pagerank = g.pagerank(weights='weight')
```

## 4. Dados analisados

- Arquivo de entrada: `C:/Users/Micro/Desktop/UFABC/CR/Projeto_CR/data/processed/reddit_title_edges_gephi.csv`
- Nos: 40964
- Arestas agregadas: 163785
- Densidade: 0.00009761
- Reciprocidade: 0.1209
- Componentes fracas: 595
- Maior componente fraca: 39710 nos (96.94% da rede)
- Componentes fortemente conexas: 30082
- Links positivos/neutros: 343808
- Links negativos: 41107 (10.68% dos links com sinal agregado)

A densidade baixa indica que, embora existam muitos links, a rede e esparsa: so uma parte muito pequena dos pares possiveis de subreddits esta conectada. Isso e comum em redes reais grandes.

## 5. Metricas principais

- Grau de entrada: quantos subreddits apontam para um subreddit.
- Grau de saida: para quantos subreddits um subreddit aponta.
- Forca de entrada: soma dos pesos recebidos.
- Forca de saida: soma dos pesos enviados.
- PageRank: importancia considerando a importancia de quem aponta.
- Betweenness: quanto um no aparece como ponte em caminhos da rede.

No grafo completo, priorizei grau/forca/componentes porque sao metricas estaveis e baratas. Betweenness foi calculada no subgrafo das arestas mais fortes, pois no grafo completo ela pode ficar pesada e menos didatica. Para essa metrica, o script usa `distance = 1 / weight`, porque no igraph pesos de betweenness representam custo/distancia, nao intensidade.

## 6. Subreddits com maior forca total no grafo completo

| subreddit | total_strength |
| --- | ---: |
| subredditdrama | 21182.0000 |
| bestof | 16892.0000 |
| askreddit | 13525.0000 |
| iama | 7518.0000 |
| pics | 7323.0000 |
| todayilearned | 7251.0000 |
| titlegore | 6970.0000 |
| funny | 6954.0000 |
| worldnews | 5707.0000 |
| shitredditsays | 5626.0000 |

## 7. Maiores emissores e receptores

### Entrada ponderada

| subreddit | in_strength |
| --- | ---: |
| askreddit | 13525.0000 |
| iama | 7516.0000 |
| pics | 7147.0000 |
| todayilearned | 6333.0000 |
| funny | 6290.0000 |
| worldnews | 5505.0000 |
| videos | 5401.0000 |
| news | 4043.0000 |
| adviceanimals | 3590.0000 |
| wtf | 3472.0000 |

### Saida ponderada

| subreddit | out_strength |
| --- | ---: |
| subredditdrama | 19249.0000 |
| bestof | 16105.0000 |
| titlegore | 6957.0000 |
| shitredditsays | 5120.0000 |
| shitpost | 4389.0000 |
| switcharoo | 4274.0000 |
| circlebroke2 | 3659.0000 |
| shitamericanssay | 3468.0000 |
| shitstatistssay | 3128.0000 |
| fitnesscirclejerk | 2540.0000 |

## 8. Arestas mais fortes

| origem | destino | peso | positivos | negativos |
| --- | --- | ---: | ---: | ---: |
| moronicmondayandroid | android | 340 | 340 | 0 |
| goodshibe | dogecoin | 286 | 286 | 0 |
| evenwithcontext | askreddit | 214 | 142 | 72 |
| titlegore | todayilearned | 212 | 212 | 0 |
| nightlypick | hockey | 208 | 208 | 0 |
| drugscirclejerk | drugs | 197 | 161 | 36 |
| switcharoo | pics | 194 | 186 | 8 |
| shitredditsays | funny | 191 | 169 | 22 |
| switcharoo | funny | 190 | 178 | 12 |
| switcharoo | wtf | 188 | 169 | 19 |

## 9. Analise do subgrafo filtrado

Para enxergar uma estrutura mais interpretavel, foi criado um subgrafo com as 500 arestas de maior peso.

- Nos no subgrafo: 357
- Arestas no subgrafo: 500
- Densidade do subgrafo: 0.003934
- Reciprocidade do subgrafo: 0.0160
- Componentes fracas no subgrafo: 65

### PageRank no subgrafo

| subreddit | pagerank |
| --- | ---: |
| askreddit | 0.0353 |
| smashbros | 0.0237 |
| ssbpm | 0.0220 |
| worldnews | 0.0125 |
| bitcoin | 0.0115 |
| pics | 0.0102 |
| subredditdrama | 0.0090 |
| planetside | 0.0081 |
| bitcoinmarkets | 0.0075 |
| hockey | 0.0065 |

### Betweenness no subgrafo

| subreddit | betweenness |
| --- | ---: |
| subredditdrama | 633.0000 |
| bestof | 111.0000 |
| subredditdramadrama | 110.0000 |
| bitcoin | 65.0000 |
| buttcoin | 31.0000 |
| srssucks | 30.0000 |
| shitredditsays | 20.0000 |
| dogecoin | 12.0000 |
| conspiracy | 9.0000 |
| smashbros | 9.0000 |

## 10. Como interpretar para o projeto

Uma leitura simples e segura e separar tres papeis:

- Receptores: subreddits com alta forca de entrada, ou seja, recebem muitos links.
- Emissores: subreddits com alta forca de saida, ou seja, apontam muito para outros.
- Pontes: subreddits com alto betweenness em subgrafos, pois conectam partes da rede.

No relatorio final, evite dizer que centralidade prova importancia social absoluta. O correto e dizer que ela indica importancia dentro da modelagem escolhida. Se os nos, arestas ou filtros mudam, a interpretacao tambem muda.

## 11. Comandos para reproduzir

```powershell
python Projeto_CR\src\analyze_reddit_igraph.py
python Projeto_CR\src\analyze_reddit_igraph.py --top-edges 1000 --top-n 15
```
