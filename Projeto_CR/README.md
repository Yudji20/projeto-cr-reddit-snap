# Projeto CR - Reddit SNAP

Projeto de analise de redes complexas usando a base SNAP Reddit Hyperlink Network.

## Estrutura

- `data/raw/`: arquivos originais baixados da SNAP.
- `data/processed/`: tabelas tratadas e agregadas.
- `notebooks/`: exploracoes interativas.
- `src/`: scripts reprodutiveis de limpeza, inspecao e analise.
- `results/figures/`: figuras finais para o relatorio.
- `reports/`: textos, registros metodologicos e resultados intermediarios.

## Dados brutos

Arquivos baixados em 22/06/2026:

- `data/raw/soc-redditHyperlinks-title.tsv`
- `data/raw/soc-redditHyperlinks-body.tsv`

Fonte: https://snap.stanford.edu/data/soc-RedditHyperlinks.html

Os arquivos TSV brutos nao sao versionados porque ultrapassam o limite de 100 MB por arquivo do GitHub. A pasta `data/raw/` contem um README com a fonte oficial para baixar os dados novamente.
