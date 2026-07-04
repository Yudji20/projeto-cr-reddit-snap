"""
Generate practical graph visualizations for the Reddit SNAP hyperlink network.

Inputs:
    Projeto_CR/data/processed/reddit_title_edges_gephi.csv

Outputs:
    Projeto_CR/results/figures/reddit_title_top_edges.png
    Projeto_CR/results/figures/reddit_title_ego_network.png
    Projeto_CR/results/figures/reddit_title_distributions.png
    Projeto_CR/results/interactive/reddit_title_top_edges.html
    Projeto_CR/results/figures/reddit_title_visual_summary.md
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from pyvis.network import Network


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "reddit_title_edges_gephi.csv"
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"
INTERACTIVE_DIR = PROJECT_ROOT / "results" / "interactive"


def load_edges(path: Path) -> pd.DataFrame:
    edges = pd.read_csv(path)
    required = {"Source", "Target", "weight", "positive", "negative"}
    missing = required - set(edges.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns: {missing_cols}")

    edges["weight"] = edges["weight"].astype(int)
    edges["positive"] = edges["positive"].astype(int)
    edges["negative"] = edges["negative"].astype(int)
    edges["sentiment_balance"] = (
        (edges["positive"] - edges["negative"]) / edges["weight"].clip(lower=1)
    )
    return edges


def build_digraph(edges: pd.DataFrame) -> nx.DiGraph:
    graph = nx.from_pandas_edgelist(
        edges,
        source="Source",
        target="Target",
        edge_attr=[
            "weight",
            "positive",
            "negative",
            "sentiment_balance",
            "first_seen",
            "last_seen",
        ],
        create_using=nx.DiGraph,
    )
    return graph


def node_strengths(edges: pd.DataFrame) -> pd.DataFrame:
    out_strength = edges.groupby("Source")["weight"].sum().rename("out_strength")
    in_strength = edges.groupby("Target")["weight"].sum().rename("in_strength")
    nodes = pd.concat([in_strength, out_strength], axis=1).fillna(0)
    nodes["total_strength"] = nodes["in_strength"] + nodes["out_strength"]
    nodes["balance_in_minus_out"] = nodes["in_strength"] - nodes["out_strength"]
    return nodes.sort_values("total_strength", ascending=False)


def make_top_edge_subgraph(
    edges: pd.DataFrame, min_weight: int, top_edges: int
) -> tuple[nx.DiGraph, pd.DataFrame]:
    filtered = edges[edges["weight"] >= min_weight].copy()
    if len(filtered) > top_edges:
        filtered = filtered.nlargest(top_edges, "weight").copy()
    elif len(filtered) < min(80, top_edges):
        filtered = edges.nlargest(top_edges, "weight").copy()

    graph = build_digraph(filtered)
    return graph, filtered


def scaled_node_size(value: float) -> float:
    return 80 + 75 * math.log1p(value)


def scaled_edge_width(value: float) -> float:
    return 0.4 + 0.9 * math.log1p(value)


def plot_top_edges(graph: nx.DiGraph, edges: pd.DataFrame, output: Path) -> None:
    strengths = node_strengths(edges)
    strength_map = strengths["total_strength"].to_dict()
    balance_map = strengths["balance_in_minus_out"].to_dict()

    plt.figure(figsize=(15, 11))
    ax = plt.gca()
    ax.set_title(
        "Reddit hyperlink network: principais arestas por peso",
        fontsize=15,
        pad=14,
    )

    pos = nx.spring_layout(graph, seed=42, weight="weight", k=0.38, iterations=90)
    node_sizes = [scaled_node_size(strength_map.get(node, 1)) for node in graph.nodes]
    node_colors = [balance_map.get(node, 0) for node in graph.nodes]
    edge_widths = [
        scaled_edge_width(data.get("weight", 1)) for _, _, data in graph.edges(data=True)
    ]
    edge_colors = [
        data.get("sentiment_balance", 0) for _, _, data in graph.edges(data=True)
    ]

    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=8,
        width=edge_widths,
        edge_color=edge_colors,
        edge_cmap=plt.cm.RdBu,
        edge_vmin=-1,
        edge_vmax=1,
        alpha=0.42,
        connectionstyle="arc3,rad=0.06",
    )
    nodes = nx.draw_networkx_nodes(
        graph,
        pos,
        ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        cmap=plt.cm.PiYG,
        alpha=0.88,
        linewidths=0.35,
        edgecolors="#1f2933",
    )

    label_nodes = strengths.head(22).index.intersection(list(graph.nodes))
    labels = {node: node for node in label_nodes}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=8, ax=ax)

    cbar = plt.colorbar(nodes, ax=ax, shrink=0.68)
    cbar.set_label("Forca de entrada - forca de saida")
    ax.text(
        0.01,
        0.02,
        "Tamanho do no: forca ponderada total. Cor da aresta: balanco de sentimento.",
        transform=ax.transAxes,
        fontsize=9,
        color="#374151",
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output, dpi=180)
    plt.close()


def choose_ego_center(edges: pd.DataFrame, requested: str | None) -> str:
    nodes = node_strengths(edges)
    if requested:
        all_nodes = set(edges["Source"]).union(edges["Target"])
        if requested not in all_nodes:
            raise ValueError(f"Node '{requested}' was not found in the edge list.")
        return requested
    return str(nodes.index[0])


def make_ego_edges(edges: pd.DataFrame, center: str, per_side: int) -> pd.DataFrame:
    incoming = (
        edges[edges["Target"] == center].nlargest(per_side, "weight").copy()
    )
    outgoing = (
        edges[edges["Source"] == center].nlargest(per_side, "weight").copy()
    )
    return pd.concat([incoming, outgoing], ignore_index=True).drop_duplicates(
        subset=["Source", "Target"]
    )


def plot_ego_network(edges: pd.DataFrame, center: str, output: Path) -> None:
    graph = build_digraph(edges)
    strengths = node_strengths(edges)
    strength_map = strengths["total_strength"].to_dict()

    incoming_nodes = sorted({u for u, v in graph.edges if v == center and u != center})
    outgoing_nodes = sorted({v for u, v in graph.edges if u == center and v != center})
    both = set(incoming_nodes).intersection(outgoing_nodes)

    pos: dict[str, tuple[float, float]] = {center: (0.0, 0.0)}
    for i, node in enumerate(incoming_nodes):
        y = 1.0 - 2.0 * i / max(1, len(incoming_nodes) - 1)
        pos[node] = (-1.0, y)
    for i, node in enumerate(outgoing_nodes):
        y = 1.0 - 2.0 * i / max(1, len(outgoing_nodes) - 1)
        pos[node] = (1.0, y)
    for i, node in enumerate(sorted(both)):
        y = 1.0 - 2.0 * i / max(1, len(both) - 1)
        pos[node] = (0.0, y)

    plt.figure(figsize=(13, 9))
    ax = plt.gca()
    ax.set_title(f"Rede ego: vizinhanca ponderada de {center}", fontsize=15, pad=14)

    edge_widths = [
        scaled_edge_width(data.get("weight", 1)) for _, _, data in graph.edges(data=True)
    ]
    edge_colors = [
        data.get("sentiment_balance", 0) for _, _, data in graph.edges(data=True)
    ]
    node_colors = [
        "#111827" if node == center else "#2a9d8f" if node in both else "#5b8def"
        for node in graph.nodes
    ]
    node_sizes = [
        950 if node == center else scaled_node_size(strength_map.get(node, 1))
        for node in graph.nodes
    ]

    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=10,
        width=edge_widths,
        edge_color=edge_colors,
        edge_cmap=plt.cm.RdBu,
        edge_vmin=-1,
        edge_vmax=1,
        alpha=0.55,
        connectionstyle="arc3,rad=0.08",
    )
    nx.draw_networkx_nodes(
        graph,
        pos,
        ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        alpha=0.92,
        linewidths=0.45,
        edgecolors="#111827",
    )
    nx.draw_networkx_labels(graph, pos, font_size=8, ax=ax)
    ax.text(-1.1, 1.12, "Entram no centro", fontsize=10, weight="bold")
    ax.text(0.72, 1.12, "Saem do centro", fontsize=10, weight="bold")
    ax.text(
        0.01,
        0.02,
        "Azul: no aparece em um lado. Verde: no entra e sai. Preto: subreddit central.",
        transform=ax.transAxes,
        fontsize=9,
        color="#374151",
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output, dpi=180)
    plt.close()


def plot_distributions(edges: pd.DataFrame, graph: nx.DiGraph, output: Path) -> None:
    strengths = node_strengths(edges)
    weak_components = sorted(
        (len(c) for c in nx.weakly_connected_components(graph)), reverse=True
    )

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    fig.suptitle("Distribuicoes estruturais da rede agregada", fontsize=15)

    axes[0].hist(strengths["in_strength"], bins=60, color="#5b8def")
    axes[0].set_title("Forca de entrada")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Soma dos pesos recebidos")
    axes[0].set_ylabel("Quantidade de subreddits (log)")

    axes[1].hist(strengths["out_strength"], bins=60, color="#2a9d8f")
    axes[1].set_title("Forca de saida")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Soma dos pesos enviados")

    axes[2].hist(edges["weight"], bins=60, color="#e76f51")
    axes[2].set_title("Peso das arestas")
    axes[2].set_yscale("log")
    axes[2].set_xlabel("Quantidade de hyperlinks agregados")

    note = (
        f"Componentes fracas: {len(weak_components)} | "
        f"maior componente: {weak_components[0]:,} nos"
    ).replace(",", ".")
    fig.text(0.5, 0.02, note, ha="center", fontsize=9, color="#374151")
    plt.tight_layout(rect=(0, 0.04, 1, 0.93))
    plt.savefig(output, dpi=180)
    plt.close()


def write_interactive_html(edges: pd.DataFrame, output: Path) -> None:
    graph = build_digraph(edges)
    strengths = node_strengths(edges)
    strength_map = strengths["total_strength"].to_dict()

    net = Network(
        height="850px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#111827",
        cdn_resources="in_line",
    )
    net.barnes_hut(gravity=-4200, central_gravity=0.18, spring_length=140)

    for node in graph.nodes:
        strength = strength_map.get(node, 1)
        net.add_node(
            node,
            label=node,
            value=max(1, math.log1p(strength)),
            title=f"{node}<br>forca total: {int(strength)}",
        )

    for source, target, data in graph.edges(data=True):
        weight = int(data.get("weight", 1))
        balance = float(data.get("sentiment_balance", 0))
        color = "#3b82f6" if balance >= 0 else "#ef4444"
        net.add_edge(
            source,
            target,
            value=max(1, math.log1p(weight)),
            title=(
                f"{source} -> {target}<br>"
                f"peso: {weight}<br>"
                f"positivas: {data.get('positive', 0)} | "
                f"negativas: {data.get('negative', 0)}"
            ),
            color=color,
            arrows="to",
        )

    net.set_options(
        """
        {
          "nodes": {
            "shape": "dot",
            "font": { "size": 18, "face": "Arial" },
            "borderWidth": 1
          },
          "edges": {
            "smooth": { "type": "dynamic" },
            "font": { "size": 10, "align": "middle" }
          },
          "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true
          },
          "physics": {
            "stabilization": { "iterations": 180 }
          }
        }
        """
    )
    html = net.generate_html(notebook=False)
    output.write_text(html, encoding="utf-8")


def write_summary(
    full_edges: pd.DataFrame,
    full_graph: nx.DiGraph,
    top_edges: pd.DataFrame,
    center: str,
    output: Path,
    generated_files: list[Path],
) -> None:
    strengths = node_strengths(full_edges)
    weak_components = sorted(
        (len(c) for c in nx.weakly_connected_components(full_graph)), reverse=True
    )
    strongly_components_count = nx.number_strongly_connected_components(full_graph)
    top_nodes = strengths.head(12).reset_index().rename(columns={"index": "subreddit"})

    table_rows = [
        "| subreddit | in_strength | out_strength | total_strength |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in top_nodes.itertuples(index=False):
        table_rows.append(
            "| "
            f"{row.subreddit} | "
            f"{int(row.in_strength)} | "
            f"{int(row.out_strength)} | "
            f"{int(row.total_strength)} |"
        )

    payload = {
        "full_graph": {
            "nodes": full_graph.number_of_nodes(),
            "edges": full_graph.number_of_edges(),
            "weak_components": len(weak_components),
            "largest_weak_component_nodes": weak_components[0],
            "strong_components": strongly_components_count,
            "positive_links": int(full_edges["positive"].sum()),
            "negative_links": int(full_edges["negative"].sum()),
        },
        "visualized_subgraph": {
            "nodes": int(len(set(top_edges["Source"]).union(top_edges["Target"]))),
            "edges": int(len(top_edges)),
            "min_weight": int(top_edges["weight"].min()),
            "max_weight": int(top_edges["weight"].max()),
            "ego_center": center,
        },
    }

    lines = [
        "# Resumo das visualizacoes geradas",
        "",
        "## Grafo completo",
        "",
        f"- Nos: {payload['full_graph']['nodes']}",
        f"- Arestas agregadas: {payload['full_graph']['edges']}",
        f"- Componentes fracas: {payload['full_graph']['weak_components']}",
        (
            "- Maior componente fraca: "
            f"{payload['full_graph']['largest_weak_component_nodes']} nos"
        ),
        f"- Componentes fortemente conexas: {payload['full_graph']['strong_components']}",
        f"- Hyperlinks positivos/neutros: {payload['full_graph']['positive_links']}",
        f"- Hyperlinks negativos: {payload['full_graph']['negative_links']}",
        "",
        "## Subgrafo visualizado",
        "",
        f"- Nos no subgrafo: {payload['visualized_subgraph']['nodes']}",
        f"- Arestas no subgrafo: {payload['visualized_subgraph']['edges']}",
        (
            "- Faixa de peso das arestas: "
            f"{payload['visualized_subgraph']['min_weight']} a "
            f"{payload['visualized_subgraph']['max_weight']}"
        ),
        f"- Centro da rede ego: `{center}`",
        "",
        "## Subreddits com maior forca ponderada",
        "",
        "\n".join(table_rows),
        "",
        "## Arquivos",
        "",
    ]
    lines.extend(f"- `{path.as_posix()}`" for path in generated_files)
    lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")
    output.with_suffix(".json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize the processed Reddit hyperlink graph."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--min-weight", type=int, default=20)
    parser.add_argument("--top-edges", type=int, default=350)
    parser.add_argument("--ego-center", default=None)
    parser.add_argument("--ego-per-side", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    INTERACTIVE_DIR.mkdir(parents=True, exist_ok=True)

    edges = load_edges(args.input)
    full_graph = build_digraph(edges)
    top_graph, top_edges = make_top_edge_subgraph(
        edges, min_weight=args.min_weight, top_edges=args.top_edges
    )
    center = choose_ego_center(edges, args.ego_center)
    ego_edges = make_ego_edges(edges, center=center, per_side=args.ego_per_side)

    top_png = FIGURES_DIR / "reddit_title_top_edges.png"
    ego_png = FIGURES_DIR / "reddit_title_ego_network.png"
    distributions_png = FIGURES_DIR / "reddit_title_distributions.png"
    interactive_html = INTERACTIVE_DIR / "reddit_title_top_edges.html"
    summary_md = FIGURES_DIR / "reddit_title_visual_summary.md"

    plot_top_edges(top_graph, top_edges, top_png)
    plot_ego_network(ego_edges, center, ego_png)
    plot_distributions(edges, full_graph, distributions_png)
    write_interactive_html(top_edges, interactive_html)
    write_summary(
        full_edges=edges,
        full_graph=full_graph,
        top_edges=top_edges,
        center=center,
        output=summary_md,
        generated_files=[
            top_png,
            ego_png,
            distributions_png,
            interactive_html,
            summary_md,
        ],
    )

    print("Generated:")
    for path in [
        top_png,
        ego_png,
        distributions_png,
        interactive_html,
        summary_md,
        summary_md.with_suffix(".json"),
    ]:
        print(path)


if __name__ == "__main__":
    main()
