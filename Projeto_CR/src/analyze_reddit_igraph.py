"""
Build and analyze a simple Reddit hyperlink network with python-igraph.

Input:
    Projeto_CR/data/processed/reddit_title_edges_gephi.csv

Outputs:
    Projeto_CR/reports/modelagem_rede_reddit_igraph.md
    Projeto_CR/reports/modelagem_rede_reddit_igraph.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import igraph as ig
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "reddit_title_edges_gephi.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def load_edges(path: Path) -> pd.DataFrame:
    edges = pd.read_csv(path)
    required = {"Source", "Target", "weight", "positive", "negative"}
    missing = required - set(edges.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns: {missing_cols}")

    edges = edges.copy()
    edges["Source"] = edges["Source"].astype(str)
    edges["Target"] = edges["Target"].astype(str)
    edges["weight"] = edges["weight"].astype(int)
    edges["positive"] = edges["positive"].astype(int)
    edges["negative"] = edges["negative"].astype(int)
    edges["sentiment_balance"] = (
        (edges["positive"] - edges["negative"]) / edges["weight"].clip(lower=1)
    )
    return edges


def build_graph(edges: pd.DataFrame) -> ig.Graph:
    tuples = list(edges[["Source", "Target"]].itertuples(index=False, name=None))
    graph = ig.Graph.TupleList(tuples, directed=True, vertex_name_attr="name")
    graph.es["weight"] = edges["weight"].tolist()
    graph.es["distance"] = (1 / edges["weight"].clip(lower=1)).tolist()
    graph.es["positive"] = edges["positive"].tolist()
    graph.es["negative"] = edges["negative"].tolist()
    graph.es["sentiment_balance"] = edges["sentiment_balance"].tolist()
    return graph


def top_vertices_table(graph: ig.Graph, metric: str, values: list[float], n: int) -> list[dict]:
    rows = [
        {"subreddit": graph.vs[index]["name"], metric: value}
        for index, value in enumerate(values)
    ]
    rows.sort(key=lambda row: row[metric], reverse=True)
    return rows[:n]


def top_edges_table(edges: pd.DataFrame, n: int) -> list[dict]:
    columns = ["Source", "Target", "weight", "positive", "negative"]
    rows = edges.nlargest(n, "weight")[columns].to_dict(orient="records")
    return [
        {
            "source": row["Source"],
            "target": row["Target"],
            "weight": int(row["weight"]),
            "positive": int(row["positive"]),
            "negative": int(row["negative"]),
        }
        for row in rows
    ]


def component_summary(graph: ig.Graph, mode: str) -> dict:
    components = graph.connected_components(mode=mode)
    sizes = sorted(components.sizes(), reverse=True)
    return {
        "count": len(sizes),
        "largest_size": sizes[0] if sizes else 0,
        "largest_share": sizes[0] / graph.vcount() if sizes and graph.vcount() else 0,
    }


def analyze_full_graph(graph: ig.Graph, edges: pd.DataFrame, top_n: int) -> dict:
    in_degree = graph.degree(mode="in")
    out_degree = graph.degree(mode="out")
    in_strength = graph.strength(mode="in", weights="weight")
    out_strength = graph.strength(mode="out", weights="weight")
    total_strength = [in_value + out_value for in_value, out_value in zip(in_strength, out_strength)]

    return {
        "nodes": graph.vcount(),
        "edges": graph.ecount(),
        "density": graph.density(loops=False),
        "reciprocity": graph.reciprocity(ignore_loops=True),
        "weak_components": component_summary(graph, "weak"),
        "strong_components": component_summary(graph, "strong"),
        "avg_in_degree": sum(in_degree) / graph.vcount(),
        "avg_out_degree": sum(out_degree) / graph.vcount(),
        "avg_weighted_in_strength": sum(in_strength) / graph.vcount(),
        "avg_weighted_out_strength": sum(out_strength) / graph.vcount(),
        "positive_links": int(edges["positive"].sum()),
        "negative_links": int(edges["negative"].sum()),
        "top_in_strength": top_vertices_table(graph, "in_strength", in_strength, top_n),
        "top_out_strength": top_vertices_table(graph, "out_strength", out_strength, top_n),
        "top_total_strength": top_vertices_table(graph, "total_strength", total_strength, top_n),
        "top_edges": top_edges_table(edges, top_n),
    }


def analyze_filtered_graph(edges: pd.DataFrame, top_edges: int, top_n: int) -> dict:
    sub_edges = edges.nlargest(top_edges, "weight").copy()
    graph = build_graph(sub_edges)

    in_strength = graph.strength(mode="in", weights="weight")
    out_strength = graph.strength(mode="out", weights="weight")
    pagerank = graph.pagerank(weights="weight")
    betweenness = graph.betweenness(directed=True, weights="distance")

    return {
        "top_edges_used": top_edges,
        "nodes": graph.vcount(),
        "edges": graph.ecount(),
        "density": graph.density(loops=False),
        "reciprocity": graph.reciprocity(ignore_loops=True),
        "weak_components": component_summary(graph, "weak"),
        "top_in_strength": top_vertices_table(graph, "in_strength", in_strength, top_n),
        "top_out_strength": top_vertices_table(graph, "out_strength", out_strength, top_n),
        "top_pagerank": top_vertices_table(graph, "pagerank", pagerank, top_n),
        "top_betweenness": top_vertices_table(graph, "betweenness", betweenness, top_n),
    }


def markdown_table(rows: list[dict], columns: list[tuple[str, str]]) -> list[str]:
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    text_columns = {"subreddit", "source", "target"}
    separator = "| " + " | ".join("---" if key in text_columns else "---:" for _, key in columns) + " |"
    lines = [header, separator]
    for row in rows:
        values = []
        for _, key in columns:
            value = row[key]
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_report(
    output: Path,
    input_path: Path,
    full: dict,
    filtered: dict,
) -> None:
    positive = full["positive_links"]
    negative = full["negative_links"]
    total_signed = positive + negative
    negative_share = negative / total_signed if total_signed else 0

    lines = [
        "# Modelagem simples de rede Reddit com igraph",
        "",
        "## 1. Ideia central da modelagem de redes",
        "",
        "Modelar uma rede e transformar um problema em tres perguntas simples:",
        "",
        "1. Quem sao os objetos importantes? Eles viram os nos.",
        "2. Qual relacao liga esses objetos? Ela vira a aresta.",
        "3. A relacao tem direcao, peso ou tipo? Isso vira atributo do grafo.",
        "",
        "No Reddit SNAP, a modelagem mais direta e:",
        "",
        "- No: subreddit.",
        "- Aresta dirigida: um hyperlink saindo de um subreddit para outro.",
        "- Peso: quantidade de hyperlinks observados naquele par origem -> destino.",
        "- Sinal: quantidade de links positivos/neutros e negativos.",
        "",
        "Em notacao de grafos, temos `G = (V, E)`: `V` e o conjunto de subreddits e `E` e o conjunto de links entre eles.",
        "",
        "## 2. Por que esta modelagem faz sentido",
        "",
        "Se a pergunta for \"quais comunidades do Reddit apontam para quais outras comunidades?\", uma rede subreddit -> subreddit e adequada. A direcao importa porque `A -> B` nao significa a mesma coisa que `B -> A`. O peso importa porque uma relacao que aparece 200 vezes e mais forte do que uma relacao que aparece uma vez.",
        "",
        "Outras modelagens seriam possiveis. Por exemplo, uma rede bipartida `postagem -> subreddit` serviria melhor para estudar posts especificos. Mas, para estudar fluxo entre comunidades, a rede dirigida e ponderada e a escolha mais simples e interpretavel.",
        "",
        "## 3. Codigo-base em igraph",
        "",
        "O script reprodutivel esta em `Projeto_CR/src/analyze_reddit_igraph.py`. O trecho essencial e:",
        "",
        "```python",
        "import igraph as ig",
        "import pandas as pd",
        "",
        "edges = pd.read_csv('Projeto_CR/data/processed/reddit_title_edges_gephi.csv')",
        "tuples = list(edges[['Source', 'Target']].itertuples(index=False, name=None))",
        "",
        "g = ig.Graph.TupleList(tuples, directed=True, vertex_name_attr='name')",
        "g.es['weight'] = edges['weight'].astype(int).tolist()",
        "",
        "in_strength = g.strength(mode='in', weights='weight')",
        "out_strength = g.strength(mode='out', weights='weight')",
        "pagerank = g.pagerank(weights='weight')",
        "```",
        "",
        "## 4. Dados analisados",
        "",
        f"- Arquivo de entrada: `{input_path.as_posix()}`",
        f"- Nos: {full['nodes']}",
        f"- Arestas agregadas: {full['edges']}",
        f"- Densidade: {full['density']:.8f}",
        f"- Reciprocidade: {full['reciprocity']:.4f}",
        f"- Componentes fracas: {full['weak_components']['count']}",
        f"- Maior componente fraca: {full['weak_components']['largest_size']} nos ({full['weak_components']['largest_share']:.2%} da rede)",
        f"- Componentes fortemente conexas: {full['strong_components']['count']}",
        f"- Links positivos/neutros: {positive}",
        f"- Links negativos: {negative} ({negative_share:.2%} dos links com sinal agregado)",
        "",
        "A densidade baixa indica que, embora existam muitos links, a rede e esparsa: so uma parte muito pequena dos pares possiveis de subreddits esta conectada. Isso e comum em redes reais grandes.",
        "",
        "## 5. Metricas principais",
        "",
        "- Grau de entrada: quantos subreddits apontam para um subreddit.",
        "- Grau de saida: para quantos subreddits um subreddit aponta.",
        "- Forca de entrada: soma dos pesos recebidos.",
        "- Forca de saida: soma dos pesos enviados.",
        "- PageRank: importancia considerando a importancia de quem aponta.",
        "- Betweenness: quanto um no aparece como ponte em caminhos da rede.",
        "",
        "No grafo completo, priorizei grau/forca/componentes porque sao metricas estaveis e baratas. Betweenness foi calculada no subgrafo das arestas mais fortes, pois no grafo completo ela pode ficar pesada e menos didatica. Para essa metrica, o script usa `distance = 1 / weight`, porque no igraph pesos de betweenness representam custo/distancia, nao intensidade.",
        "",
        "## 6. Subreddits com maior forca total no grafo completo",
        "",
        *markdown_table(
            full["top_total_strength"],
            [
                ("subreddit", "subreddit"),
                ("total_strength", "total_strength"),
            ],
        ),
        "",
        "## 7. Maiores emissores e receptores",
        "",
        "### Entrada ponderada",
        "",
        *markdown_table(
            full["top_in_strength"],
            [
                ("subreddit", "subreddit"),
                ("in_strength", "in_strength"),
            ],
        ),
        "",
        "### Saida ponderada",
        "",
        *markdown_table(
            full["top_out_strength"],
            [
                ("subreddit", "subreddit"),
                ("out_strength", "out_strength"),
            ],
        ),
        "",
        "## 8. Arestas mais fortes",
        "",
        *markdown_table(
            full["top_edges"],
            [
                ("origem", "source"),
                ("destino", "target"),
                ("peso", "weight"),
                ("positivos", "positive"),
                ("negativos", "negative"),
            ],
        ),
        "",
        "## 9. Analise do subgrafo filtrado",
        "",
        f"Para enxergar uma estrutura mais interpretavel, foi criado um subgrafo com as {filtered['top_edges_used']} arestas de maior peso.",
        "",
        f"- Nos no subgrafo: {filtered['nodes']}",
        f"- Arestas no subgrafo: {filtered['edges']}",
        f"- Densidade do subgrafo: {filtered['density']:.6f}",
        f"- Reciprocidade do subgrafo: {filtered['reciprocity']:.4f}",
        f"- Componentes fracas no subgrafo: {filtered['weak_components']['count']}",
        "",
        "### PageRank no subgrafo",
        "",
        *markdown_table(
            filtered["top_pagerank"],
            [
                ("subreddit", "subreddit"),
                ("pagerank", "pagerank"),
            ],
        ),
        "",
        "### Betweenness no subgrafo",
        "",
        *markdown_table(
            filtered["top_betweenness"],
            [
                ("subreddit", "subreddit"),
                ("betweenness", "betweenness"),
            ],
        ),
        "",
        "## 10. Como interpretar para o projeto",
        "",
        "Uma leitura simples e segura e separar tres papeis:",
        "",
        "- Receptores: subreddits com alta forca de entrada, ou seja, recebem muitos links.",
        "- Emissores: subreddits com alta forca de saida, ou seja, apontam muito para outros.",
        "- Pontes: subreddits com alto betweenness em subgrafos, pois conectam partes da rede.",
        "",
        "No relatorio final, evite dizer que centralidade prova importancia social absoluta. O correto e dizer que ela indica importancia dentro da modelagem escolhida. Se os nos, arestas ou filtros mudam, a interpretacao tambem muda.",
        "",
        "## 11. Comandos para reproduzir",
        "",
        "```powershell",
        "python Projeto_CR\\src\\analyze_reddit_igraph.py",
        "python Projeto_CR\\src\\analyze_reddit_igraph.py --top-edges 1000 --top-n 15",
        "```",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Reddit network with igraph.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--top-edges", type=int, default=500)
    parser.add_argument("--top-n", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    edges = load_edges(args.input)
    graph = build_graph(edges)
    full = analyze_full_graph(graph, edges, args.top_n)
    filtered = analyze_filtered_graph(edges, args.top_edges, args.top_n)

    output = REPORTS_DIR / "modelagem_rede_reddit_igraph.md"
    write_report(output, args.input, full, filtered)

    payload = {"full_graph": full, "filtered_graph": filtered}
    output.with_suffix(".json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(output)
    print(output.with_suffix(".json"))


if __name__ == "__main__":
    main()
