# Cronograma do Projeto

**Projeto:** Análise de Redes Complexas no Reddit: comunidades-ponte e influência entre subreddits  
**Disciplina:** BCM0506 - Comunicação e Redes - 2026.2  
**Base principal:** SNAP Reddit Hyperlink Network  
**Data de planejamento:** 22/06/2026  
**Entrega do relatório final:** 22/07/2026, 23h59

## Contexto inicial

O projeto foi inicialmente planejado com coleta direta pela API oficial do Reddit, buscando construir uma rede a partir de usuários, subreddits, comentários e menções. Durante as primeiras tentativas, essa estratégia se mostrou arriscada para o prazo do projeto, pois dependeria de autenticação, limite de requisições, grande volume de coleta, tratamento de dados de usuários e possível indisponibilidade ou incompletude dos dados.

Por isso, a partir de 22/06/2026, a fonte principal foi alterada para a base pública SNAP Reddit Hyperlink Network, que já disponibiliza uma rede real entre subreddits, com origem, destino, sinal da interação, timestamp e atributos textuais.

## Cronograma

| Período | Etapa | Entrega interna |
| --- | --- | --- |
| 22/06 | Registrar a mudança de rota: tentativas com a API do Reddit e decisão de trocar para a base SNAP | Texto curto para a metodologia |
| 22/06 - 24/06 | Baixar e inspecionar os arquivos da SNAP: title e/ou body | Dataset local, leitura em Python e contagem inicial |
| 25/06 - 27/06 | Definir o recorte do estudo | Decidir se a análise usará title, body ou ambos |
| 28/06 - 30/06 | Limpar e transformar os dados | Tabela de arestas agregada por origem, destino, peso e sinal |
| 01/07 - 03/07 | Construir o grafo principal | Grafo dirigido e ponderado entre subreddits |
| 04/07 - 06/07 | Calcular métricas estruturais | Número de vértices, arestas, densidade, componentes e graus |
| 07/07 - 09/07 | Calcular métricas de influência | PageRank, centralidade de intermediação e centralidade de proximidade, se viável |
| 10/07 - 12/07 | Detectar comunidades e subreddits-ponte | Clusters e ranking dos nós que conectam comunidades |
| 13/07 - 15/07 | Comparar interações positivas/neutras e negativas | Subgrafos por sinal e comparação das métricas |
| 16/07 | Prova da disciplina | Pausa ou atividade leve |
| 17/07 - 18/07 | Gerar visualizações finais | Figuras por Python e/ou exportação para Gephi |
| 19/07 - 20/07 | Escrever o relatório técnico | Introdução, metodologia, resultados e discussão |
| 21/07 | Revisar o relatório | Conferência de texto, figuras, referências e coerência |
| 22/07 | Entrega final | PDF em formato IEEE, em português |

## Produtos esperados

- Scripts ou notebook para leitura, limpeza e análise dos dados.
- Tabela de arestas tratada.
- Grafo principal dirigido e ponderado.
- Rankings de subreddits por grau, PageRank e centralidade de intermediação.
- Detecção de comunidades.
- Comparação entre rede geral, rede positiva/neutra e rede negativa.
- Figuras para o relatório.
- Relatório final em formato IEEE.

