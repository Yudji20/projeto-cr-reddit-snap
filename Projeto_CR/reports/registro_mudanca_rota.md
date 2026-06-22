# Registro metodologico - mudanca de rota

Em 22/06/2026, o projeto deixou de utilizar coleta direta pela API oficial do Reddit como fonte principal de dados. A decisao foi tomada porque essa estrategia exigiria autenticacao, controle de limites de requisicao, coleta em alto volume, tratamento de dados de usuarios e maior risco de incompletude dentro do prazo disponivel.

A fonte principal passou a ser a base publica SNAP Reddit Hyperlink Network, que ja disponibiliza hyperlinks reais entre subreddits, com origem, destino, sinal da interacao, timestamp e atributos textuais. Essa mudanca preserva a pergunta central do projeto, pois a rede continua modelando relacoes entre comunidades do Reddit, mas torna a execucao mais viavel e reprodutivel.

Na nova modelagem, cada vertice representa um subreddit e cada aresta dirigida representa um hyperlink de um subreddit de origem para um subreddit de destino. A agregacao de arestas repetidas sera usada para obter pesos entre pares de subreddits, e o campo `LINK_SENTIMENT` permitira comparar interacoes positivas/neutras e negativas.

