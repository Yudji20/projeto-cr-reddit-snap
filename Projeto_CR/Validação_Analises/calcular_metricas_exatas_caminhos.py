"""
Calcula metricas exatas de caminhos para relatorio.

Por padrao, calcula na maior componente fraca da camada escolhida. Isso evita
misturar distancias infinitas de um grafo desconexo com metricas finitas.

Saidas:
    Projeto_CR/reports/exact_path_metrics_<layer>_<scope>.json
    Projeto_CR/reports/exact_path_metrics_<layer>_<scope>_nodes.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path

import duckdb
import igraph as ig


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "processed" / "reddit_graph.duckdb"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula diametro, proximidade, radialidade e excentricidade exatos."
    )
    parser.add_argument(
        "--layer",
        choices=["combined", "title", "body"],
        default="combined",
        help="Camada do grafo usada no calculo.",
    )
    parser.add_argument(
        "--scope",
        choices=["largest-component", "all-components"],
        default="largest-component",
        help=(
            "largest-component calcula metricas finitas na maior componente; "
            "all-components calcula cada componente separadamente e agrega."
        ),
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=96,
        help="Quantidade de vertices por lote no calculo exato de radialidade.",
    )
    parser.add_argument(
        "--min-component-size",
        type=int,
        default=2,
        help="Menor componente incluida quando --scope all-components.",
    )
    parser.add_argument(
        "--component-rank",
        type=int,
        default=None,
        help=(
            "Calcula apenas a componente nessa posicao por tamanho, onde 1 e a maior. "
            "Util para teste rapido antes do job completo."
        ),
    )
    parser.add_argument(
        "--max-components",
        type=int,
        default=None,
        help="Limita quantas componentes serao calculadas quando --scope all-components.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Quantidade de vertices nos rankings do JSON.",
    )
    return parser.parse_args()


def fetch_edges(db_path: Path, layer: str) -> list[tuple[str, str, int]]:
    con = duckdb.connect(str(db_path), read_only=True)
    table_exists = con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = 'edges_by_layer'
        """
    ).fetchone()[0]
    if table_exists:
        query = """
            SELECT source, target, weight
            FROM edges_by_layer
            WHERE layer = ? AND source != target
        """
        rows = con.execute(query, [layer]).fetchall()
    elif layer == "combined":
        rows = con.execute(
            """
            SELECT source, target, weight
            FROM edges_combined
            WHERE source != target
            """
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT source, target, SUM(weight)::INTEGER AS weight
            FROM edges_raw
            WHERE layer = ? AND source != target
            GROUP BY source, target
            """,
            [layer],
        ).fetchall()
    con.close()
    return [(str(source), str(target), int(weight)) for source, target, weight in rows]


def build_graph(edges: list[tuple[str, str, int]]) -> ig.Graph:
    directed = ig.Graph.TupleList(
        edges,
        directed=True,
        vertex_name_attr="name",
        edge_attrs=["weight"],
    )
    return directed.as_undirected(combine_edges={"weight": "sum"})


def finite(value: float | int | None) -> float:
    if value is None:
        return 0.0
    value = float(value)
    return value if math.isfinite(value) else 0.0


def describe(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "mean": 0.0, "max": 0.0}
    return {
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def component_subgraphs(
    graph: ig.Graph,
    scope: str,
    min_component_size: int,
    component_rank: int | None,
    max_components: int | None,
) -> list[ig.Graph]:
    components = graph.connected_components()
    ordered_components = sorted(
        [component for component in components if len(component) >= min_component_size],
        key=len,
        reverse=True,
    )

    if component_rank is not None:
        if component_rank < 1 or component_rank > len(ordered_components):
            raise ValueError(
                f"component-rank deve ficar entre 1 e {len(ordered_components)} "
                f"para esta camada."
            )
        return [graph.subgraph(ordered_components[component_rank - 1])]

    if scope == "largest-component":
        return [graph.subgraph(ordered_components[0])]

    subgraphs = []
    for component in ordered_components:
        subgraphs.append(graph.subgraph(component))
        if max_components is not None and len(subgraphs) >= max_components:
            break
    return subgraphs


def exact_radiality(
    graph: ig.Graph,
    diameter: int,
    batch_size: int,
) -> tuple[list[float], list[float]]:
    """Retorna radialidade normalizada e radialidade bruta.

    radialidade_bruta(v) = soma(D + 1 - d(v,u)) / (n - 1)
    radialidade_normalizada(v) = radialidade_bruta(v) / D

    D e o diametro da componente e d(v,u) e a distancia geodesica exata.
    """
    node_count = graph.vcount()
    if node_count <= 1 or diameter <= 0:
        return [0.0] * node_count, [0.0] * node_count

    radiality_raw = [0.0] * node_count
    normalized_denominator = max(1, diameter)
    vertex_ids = list(range(node_count))

    for start in range(0, node_count, batch_size):
        batch = vertex_ids[start : start + batch_size]
        distances = graph.distances(source=batch)
        for row_index, source in enumerate(batch):
            total = 0.0
            for distance in distances[row_index]:
                if distance <= 0 or not math.isfinite(distance):
                    continue
                total += diameter + 1 - distance
            radiality_raw[source] = finite(total / (node_count - 1))

    radiality_normalized = [
        finite(value / normalized_denominator)
        for value in radiality_raw
    ]
    return radiality_normalized, radiality_raw


def top_rows(rows: list[dict[str, object]], field: str, top_n: int) -> list[dict[str, object]]:
    return sorted(rows, key=lambda row: float(row[field]), reverse=True)[:top_n]


def compute_component_metrics(
    graph: ig.Graph,
    component_rank: int,
    batch_size: int,
    top_n: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    started = time.perf_counter()
    node_count = graph.vcount()
    edge_count = graph.ecount()
    diameter = int(graph.diameter(directed=False, unconn=False))
    closeness = [finite(value) for value in graph.closeness(mode="all", normalized=True)]
    eccentricity = [finite(value) for value in graph.eccentricity(mode="all")]
    radiality, radiality_raw = exact_radiality(graph, diameter=diameter, batch_size=batch_size)

    node_rows = []
    for index, vertex in enumerate(graph.vs):
        node_rows.append(
            {
                "component_rank": component_rank,
                "node": vertex["name"],
                "closeness": closeness[index],
                "radiality": radiality[index],
                "radiality_raw": radiality_raw[index],
                "eccentricity": eccentricity[index],
            }
        )

    summary = {
        "component_rank": component_rank,
        "node_count": node_count,
        "edge_count": edge_count,
        "diameter": diameter,
        "closeness": describe(closeness),
        "radiality": describe(radiality),
        "radiality_raw": describe(radiality_raw),
        "eccentricity": describe(eccentricity),
        "top_closeness": top_rows(node_rows, "closeness", top_n),
        "top_radiality": top_rows(node_rows, "radiality", top_n),
        "top_eccentricity": top_rows(node_rows, "eccentricity", top_n),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    return summary, node_rows


def write_node_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "component_rank",
        "node",
        "closeness",
        "radiality",
        "radiality_raw",
        "eccentricity",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    edges = fetch_edges(args.db, args.layer)
    graph = build_graph(edges)
    components = graph.connected_components()
    component_sizes = sorted(components.sizes(), reverse=True)
    selected = component_subgraphs(
        graph,
        scope=args.scope,
        min_component_size=args.min_component_size,
        component_rank=args.component_rank,
        max_components=args.max_components,
    )

    all_node_rows: list[dict[str, object]] = []
    component_summaries = []
    for loop_rank, component_graph in enumerate(selected, start=1):
        rank = args.component_rank if args.component_rank is not None else loop_rank
        print(
            f"Componente {rank}: "
            f"{component_graph.vcount()} vertices, {component_graph.ecount()} arestas"
        )
        summary, node_rows = compute_component_metrics(
            component_graph,
            component_rank=rank,
            batch_size=args.batch_size,
            top_n=args.top_n,
        )
        component_summaries.append(summary)
        all_node_rows.extend(node_rows)

    rank_suffix = f"_rank{args.component_rank}" if args.component_rank is not None else ""
    output_stem = f"exact_path_metrics_{args.layer}_{args.scope}{rank_suffix}"
    json_path = args.output_dir / f"{output_stem}.json"
    csv_path = args.output_dir / f"{output_stem}_nodes.csv"

    payload = {
        "layer": args.layer,
        "scope": args.scope,
        "component_rank": args.component_rank,
        "max_components": args.max_components,
        "method": "exact_unweighted_shortest_paths",
        "db": str(args.db),
        "graph": {
            "node_count": graph.vcount(),
            "edge_count": graph.ecount(),
            "component_count": len(component_sizes),
            "component_sizes_top10": component_sizes[:10],
            "global_diameter_note": (
                "infinite_or_undefined_for_disconnected_graph"
                if len(component_sizes) > 1
                else "finite_connected_graph"
            ),
        },
        "radiality_formula": {
            "raw": "sum(D + 1 - d(v,u)) / (n - 1)",
            "normalized": "raw / D",
            "D": "component diameter",
            "d(v,u)": "exact unweighted shortest-path distance",
        },
        "components": component_summaries,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "node_csv": str(csv_path),
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_node_csv(csv_path, all_node_rows)

    print(json.dumps({"json": str(json_path), "csv": str(csv_path)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
