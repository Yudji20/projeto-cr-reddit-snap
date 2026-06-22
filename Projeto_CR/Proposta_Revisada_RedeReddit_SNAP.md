# Proposta Revisada de Projeto

**Universidade Federal do ABC**  
**Disciplina:** BCM0506 - Comunicação e Redes - 2026.2  
**Projeto:** Análise de Redes Complexas no Reddit: identificação de comunidades-ponte e influência entre subreddits  
**Data da revisão:** 22/06/2026

## 1. Título

Análise de Redes Complexas no Reddit: identificação de comunidades-ponte e influência entre subreddits.

## 2. Objetivo geral

Identificar quais subreddits funcionam como pontes entre diferentes comunidades na rede de hyperlinks do Reddit, analisando sua influência estrutural por meio de métricas de redes complexas.

## 3. Objetivos específicos

- Construir uma rede dirigida entre subreddits a partir da base SNAP Reddit Hyperlink Network.
- Modelar os subreddits como vértices e os hyperlinks entre subreddits como arestas.
- Agregar arestas repetidas para obter pesos representando a intensidade das conexões.
- Analisar diferenças entre interações positivas/neutras e negativas.
- Calcular métricas como grau de entrada, grau de saída, PageRank, centralidade de intermediação, densidade e componentes.
- Detectar comunidades ou clusters que possam representar bolhas sociais.
- Identificar subreddits que atuam como pontes entre comunidades, mesmo quando não são os mais populares da rede.

## 4. Motivação

O Reddit é uma rede social organizada em comunidades temáticas chamadas subreddits. Embora cada subreddit tenha seu próprio tema, regras e público, as comunidades não estão isoladas: usuários frequentemente fazem hyperlinks para outras comunidades, levando informações, debates, memes e conflitos de um grupo para outro.

Estudar essa estrutura como uma rede complexa permite investigar como comunidades digitais se conectam, quais subreddits concentram influência e quais atuam como pontes entre grupos distintos. Essa análise pode ajudar a compreender fenômenos de disseminação de informação, formação de bolhas sociais e circulação de conteúdos positivos ou negativos entre comunidades online.

## 5. Mudança em relação à proposta inicial

A proposta inicial previa a coleta de dados diretamente pela API oficial do Reddit, com a possibilidade de construir uma rede bipartida entre usuários e subreddits. Durante o planejamento, essa estratégia foi considerada arriscada para o prazo do projeto, pois dependeria de autenticação, limites de requisição, grande volume de coleta e tratamento de dados de usuários.

Por esse motivo, a fonte principal foi alterada para a base pública SNAP Reddit Hyperlink Network. Essa base já disponibiliza uma rede real entre subreddits, incluindo origem, destino, sinal da interação, timestamp e atributos textuais. A mudança mantém a ideia central do projeto, mas torna a execução mais viável e mais alinhada aos conceitos de redes complexas estudados na disciplina.

## 6. Dados

Os dados serão obtidos a partir da base SNAP Reddit Hyperlink Network, disponível publicamente em:

https://snap.stanford.edu/data/soc-RedditHyperlinks.html

A base contém hyperlinks entre subreddits extraídos de posts e comentários do Reddit. Cada aresta representa uma referência de um subreddit para outro. A base também contém informações como timestamp, sinal da interação e propriedades textuais.

## 7. Modelagem da rede

**Vértices:** subreddits.  
**Arestas:** hyperlinks de um subreddit para outro.  
**Direção:** sim. A aresta vai do subreddit que fez a referência para o subreddit referenciado.  
**Peso:** sim. O peso representa a quantidade de hyperlinks entre o mesmo par de subreddits.  
**Sinal:** sim. A base permite separar interações positivas/neutras e negativas.  
**Tempo:** poderá ser usado como análise complementar, caso o cronograma permita.

## 8. Ferramentas

- Python para leitura, limpeza, modelagem e cálculo das métricas.
- NetworkX para construção e análise dos grafos.
- Pandas para manipulação dos dados.
- Matplotlib ou outras bibliotecas Python para visualização.
- Gephi como ferramenta opcional para visualizações finais da rede.

## 9. Métricas planejadas

- Número de vértices e arestas.
- Densidade da rede.
- Grau de entrada e grau de saída.
- Componentes conectados ou fortemente conectados.
- PageRank.
- Centralidade de intermediação.
- Centralidade de proximidade, se viável computacionalmente.
- Detecção de comunidades.
- Comparação entre rede geral, rede positiva/neutra e rede negativa.

## 10. Pergunta principal

Quais subreddits funcionam como pontes entre comunidades na rede de hyperlinks do Reddit, e como essa estrutura muda entre interações positivas/neutras e negativas?

## 11. Resultados esperados

Espera-se identificar subreddits com alta influência estrutural, tanto por popularidade quanto por capacidade de conectar comunidades diferentes. Também se espera observar a formação de clusters ou bolhas sociais e verificar se subreddits menores podem exercer papel importante como pontes entre grupos maiores.

Os resultados deverão incluir rankings de centralidade, visualizações da rede, comparação entre tipos de interação e discussão sobre o papel estrutural dos subreddits mais relevantes.

