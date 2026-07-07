"""
Build comparison graph examples for the web app.

Outputs:
    Projeto_CR/data/processed/comparison_graphs.duckdb
    Projeto_CR/app/visualization/public/comparison-datasets.json

The datasets are intentionally compact so the browser can compute
classification metrics quickly while still showing known graph structures.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import networkx as nx
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "processed" / "comparison_graphs.duckdb"
DEFAULT_PUBLIC = PROJECT_ROOT / "app" / "visualization" / "public"


def edge_frame(dataset_id: str, graph: nx.Graph) -> pd.DataFrame:
    rows = []
    for source, target, data in graph.edges(data=True):
      rows.append(
          {
              "dataset_id": dataset_id,
              "source": str(source).lower(),
              "target": str(target).lower(),
              "weight": int(data.get("weight", data.get("value", 1)) or 1),
          }
      )
    return pd.DataFrame(rows)


def graph_catalog() -> list[dict]:
    random_graph = nx.gnm_random_graph(180, 540, seed=42)
    small_world_graph = nx.watts_strogatz_graph(180, 8, 0.08, seed=42)
    scale_free_graph = nx.barabasi_albert_graph(180, 3, seed=42)

    karate = nx.karate_club_graph()
    karate = nx.relabel_nodes(karate, lambda node: f"karate_{node}")

    les_miserables = nx.les_miserables_graph()
    les_miserables = nx.relabel_nodes(les_miserables, lambda node: str(node).lower().replace(" ", "_"))

    return [
        {
            "id": "erdos_renyi_180",
            "name": "Erdos-Renyi G(n,m)",
            "model": "aleatoria",
            "source": "networkx.gnm_random_graph",
            "description": "Referencia sintetica com arestas distribuidas de forma uniforme.",
            "graph": random_graph,
        },
        {
            "id": "watts_strogatz_180",
            "name": "Watts-Strogatz",
            "model": "mundo pequeno",
            "source": "networkx.watts_strogatz_graph",
            "description": "Referencia sintetica com alto agrupamento e atalhos aleatorios.",
            "graph": small_world_graph,
        },
        {
            "id": "barabasi_albert_180",
            "name": "Barabasi-Albert",
            "model": "sem escala",
            "source": "networkx.barabasi_albert_graph",
            "description": "Referencia sintetica com ligacao preferencial e formacao de hubs.",
            "graph": scale_free_graph,
        },
        {
            "id": "zachary_karate",
            "name": "Zachary Karate Club",
            "model": "exemplo famoso",
            "source": "networkx.karate_club_graph",
            "description": "Rede social classica usada em deteccao de comunidades.",
            "graph": karate,
        },
        {
            "id": "les_miserables",
            "name": "Les Miserables",
            "model": "exemplo famoso",
            "source": "networkx.les_miserables_graph",
            "description": "Coocorrencia de personagens, exemplo conhecido em visualizacao de redes.",
            "graph": les_miserables,
        },
    ]


def build_store(db_path: Path, public_dir: Path) -> dict:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    catalog = graph_catalog()
    datasets = []
    edge_frames = []

    for item in catalog:
        graph = item["graph"]
        datasets.append(
            {
                "dataset_id": item["id"],
                "name": item["name"],
                "model": item["model"],
                "source": item["source"],
                "description": item["description"],
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges(),
            }
        )
        edge_frames.append(edge_frame(item["id"], graph))

    dataset_df = pd.DataFrame(datasets)
    edge_df = pd.concat(edge_frames, ignore_index=True)

    con = duckdb.connect(str(db_path))
    con.register("comparison_datasets_df", dataset_df)
    con.register("comparison_edges_df", edge_df)
    con.execute("CREATE OR REPLACE TABLE comparison_datasets AS SELECT * FROM comparison_datasets_df")
    con.execute("CREATE OR REPLACE TABLE comparison_edges AS SELECT * FROM comparison_edges_df")
    con.unregister("comparison_datasets_df")
    con.unregister("comparison_edges_df")
    con.close()

    payload = {
        "generatedFrom": str(db_path),
        "datasets": [],
    }
    for dataset in datasets:
        edges = edge_df[edge_df["dataset_id"] == dataset["dataset_id"]]
        payload["datasets"].append(
            {
                "id": dataset["dataset_id"],
                "name": dataset["name"],
                "model": dataset["model"],
                "source": dataset["source"],
                "description": dataset["description"],
                "nodeCount": int(dataset["node_count"]),
                "edgeCount": int(dataset["edge_count"]),
                "edges": edges[["source", "target", "weight"]].to_dict(orient="records"),
            }
        )

    json_path = public_dir / "comparison-datasets.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "database": str(db_path),
        "json": str(json_path),
        "datasets": len(datasets),
        "edges": int(len(edge_df)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build comparison graph examples.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--public-dir", type=Path, default=DEFAULT_PUBLIC)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_store(args.db, args.public_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
