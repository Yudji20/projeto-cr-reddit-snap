from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

import duckdb
import igraph as ig


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = PROJECT_ROOT / "app" / "visualization" / "public"
DB_PATH = PROJECT_ROOT / "data" / "processed" / "reddit_graph.duckdb"
REPORT_DIR = PROJECT_ROOT / "reports"
LAYERS = ("combined", "title", "body")
SCOPES = ("full", "largest_component")
SAMPLE_SIZE = 64


NUMERIC_FIELDS = [
    "node_count",
    "edge_count",
    "total_weight",
    "average_degree",
    "density_directed",
    "reciprocity",
    "weak_component_count",
    "largest_weak_component_nodes",
    "largest_weak_component_share",
    "vertex_connectivity",
    "edge_connectivity",
    "articulation_point_count",
    "avg_clustering",
    "avg_shortest_path",
    "diameter",
    "modularity",
    "community_count",
    "avg_degree_centrality",
    "avg_betweenness_centrality",
    "avg_closeness_centrality",
    "avg_eigenvector_centrality",
    "avg_pagerank_centrality",
    "avg_radiality",
    "avg_eccentricity",
]
TEXT_FIELDS = ["path_metric_method", "centrality_method"]


def finite_float(value: float | int | None) -> float:
    if value is None:
        return 0.0
    value = float(value)
    return value if math.isfinite(value) else 0.0


def average(values: list[float]) -> float:
    return finite_float(sum(values) / len(values)) if values else 0.0


def fetch_edges(layer: str) -> list[tuple[str, str, int]]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT source, target, weight
            FROM edges_by_layer
            WHERE layer = ?
            ORDER BY source, target
            """,
            [layer],
        ).fetchall()
    finally:
        con.close()
    return [(str(source), str(target), int(weight)) for source, target, weight in rows]


def fetch_combined_membership() -> dict[str, int]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute("SELECT node, community_id FROM nodes").fetchall()
    finally:
        con.close()
    return {str(node): int(community_id) for node, community_id in rows}


def build_graph(edges: list[tuple[str, str, int]]) -> tuple[ig.Graph, ig.Graph]:
    directed = ig.Graph.TupleList(
        edges,
        directed=True,
        vertex_name_attr="name",
        edge_attrs=["weight"],
    )
    undirected = directed.as_undirected(combine_edges={"weight": "sum"})
    return directed, undirected


def largest_component_edges(edges: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    if not edges:
        return []
    _, undirected = build_graph(edges)
    components = undirected.connected_components()
    component_sizes = components.sizes()
    if not component_sizes:
        return []
    largest_component_id = max(
        range(len(component_sizes)),
        key=lambda component_id: component_sizes[component_id],
    )
    largest_nodes = {
        vertex["name"]
        for index, vertex in enumerate(undirected.vs)
        if components.membership[index] == largest_component_id
    }
    return [
        (source, target, weight)
        for source, target, weight in edges
        if source in largest_nodes and target in largest_nodes
    ]


def reciprocal_edge_share(edges: list[tuple[str, str, int]]) -> float:
    pairs = {(source, target) for source, target, _ in edges}
    reciprocated = sum(1 for source, target in pairs if (target, source) in pairs)
    return reciprocated / len(pairs) if pairs else 0.0


def sampled_path_metrics(graph: ig.Graph, sample_size: int) -> tuple[float, int, str]:
    node_count = graph.vcount()
    if node_count <= 1:
        return 0.0, 0, "trivial"
    if node_count <= 2500:
        average_path = graph.average_path_length(directed=False, unconn=False)
        diameter = graph.diameter(directed=False, unconn=False)
        return finite_float(average_path), int(diameter), "exact"

    degrees = graph.degree()
    ranked = sorted(range(node_count), key=lambda index: degrees[index], reverse=True)
    top_count = max(1, sample_size // 2)
    sources = ranked[:top_count]
    stride = max(1, node_count // max(1, sample_size - len(sources)))
    sources.extend(range(0, node_count, stride))
    sources = list(dict.fromkeys(sources))[:sample_size]

    distance_sum = 0.0
    distance_count = 0
    diameter_lower_bound = 0
    for source in sources:
        distances = graph.distances(source=[source])[0]
        for distance in distances:
            if distance <= 0 or not math.isfinite(distance):
                continue
            distance_sum += distance
            distance_count += 1
            diameter_lower_bound = max(diameter_lower_bound, int(distance))

    return (
        finite_float(distance_sum / distance_count if distance_count else 0.0),
        diameter_lower_bound,
        f"sampled_{len(sources)}",
    )


def centrality_sources(graph: ig.Graph, sample_size: int) -> list[int]:
    node_count = graph.vcount()
    if node_count == 0:
        return []
    degrees = graph.degree()
    ranked = sorted(range(node_count), key=lambda index: degrees[index], reverse=True)
    top_count = max(1, sample_size // 2)
    sources = ranked[:top_count]
    stride = max(1, node_count // max(1, sample_size - len(sources)))
    sources.extend(range(0, node_count, stride))
    return list(dict.fromkeys(sources))[:sample_size]


def sampled_distance_profiles(
    graph: ig.Graph,
    sources: list[int],
    diameter: int,
) -> tuple[list[float], list[float], list[float]]:
    node_count = graph.vcount()
    if node_count == 0:
        return [], [], []

    distance_sum = [0.0] * node_count
    distance_count = [0] * node_count
    eccentricity = [0.0] * node_count
    for source in sources:
        distances = graph.distances(source=[source])[0]
        for target, distance in enumerate(distances):
            if distance <= 0 or not math.isfinite(distance):
                continue
            distance_sum[target] += distance
            distance_count[target] += 1
            eccentricity[target] = max(eccentricity[target], float(distance))

    closeness = []
    radiality = []
    normalized_diameter = max(1, diameter)
    for index in range(node_count):
        if distance_count[index] == 0 or distance_sum[index] <= 0:
            closeness.append(0.0)
            radiality.append(0.0)
            continue
        avg_distance = distance_sum[index] / distance_count[index]
        closeness.append(finite_float(distance_count[index] / distance_sum[index]))
        radiality.append(
            finite_float(max(0.0, (normalized_diameter + 1 - avg_distance) / normalized_diameter))
        )
    return closeness, radiality, eccentricity


def calculate_metrics(
    layer: str,
    scope: str,
    source_edges: list[tuple[str, str, int]],
    combined_membership: dict[str, int],
) -> dict[str, object]:
    started = time.perf_counter()
    edges = largest_component_edges(source_edges) if scope == "largest_component" else source_edges
    directed, undirected = build_graph(edges)
    node_count = directed.vcount()
    edge_count = directed.ecount()
    total_weight = int(sum(weight for _, _, weight in edges))

    components = undirected.connected_components()
    component_sizes = components.sizes()
    largest_component_nodes = max(component_sizes) if component_sizes else 0
    giant = components.giant() if largest_component_nodes else ig.Graph()
    avg_path, diameter, path_method = sampled_path_metrics(giant, SAMPLE_SIZE)

    if len(component_sizes) == 1 and node_count > 1:
        try:
            vertex_connectivity = int(undirected.vertex_connectivity())
        except Exception:
            vertex_connectivity = 0
        try:
            edge_connectivity = int(undirected.edge_connectivity())
        except Exception:
            edge_connectivity = 0
    else:
        vertex_connectivity = 0
        edge_connectivity = 0
    try:
        articulation_point_count = len(undirected.articulation_points())
    except Exception:
        articulation_point_count = 0

    degree_values = undirected.degree()
    degree_centrality = [
        finite_float(value / (node_count - 1)) if node_count > 1 else 0.0
        for value in degree_values
    ]
    pagerank = directed.pagerank(weights="weight")
    try:
        eigenvector = undirected.eigenvector_centrality(weights="weight", scale=True)
    except Exception:
        eigenvector = [0.0] * node_count
    try:
        local_clustering = undirected.transitivity_local_undirected(mode="zero")
        betweenness_proxy = [
            finite_float(degree_centrality[index] * (1 - local_clustering[index]))
            for index in range(node_count)
        ]
    except Exception:
        betweenness_proxy = degree_centrality

    sources = centrality_sources(undirected, SAMPLE_SIZE)
    closeness, radiality, eccentricity = sampled_distance_profiles(
        undirected,
        sources=sources,
        diameter=diameter,
    )
    centrality_method = (
        f"degree_exact;pagerank_weighted;"
        f"eigenvector_weighted;betweenness_proxy_degree_clustering;"
        f"distance_{path_method}"
    )

    clustering = finite_float(undirected.transitivity_avglocal_undirected(mode="zero"))
    if layer == "combined" and combined_membership:
        membership = [combined_membership.get(vertex["name"], -1) for vertex in undirected.vs]
        community_count = len(set(membership) - {-1})
        modularity = undirected.modularity(membership, weights=undirected.es["weight"])
    else:
        random.seed(f"{layer}:{scope}:community_leiden")
        ig.set_random_number_generator(random)
        communities = undirected.community_leiden(weights="weight", objective_function="modularity")
        community_count = len(set(communities.membership))
        modularity = undirected.modularity(communities.membership, weights=undirected.es["weight"])

    return {
        "layer": layer,
        "scope": scope,
        "node_count": int(node_count),
        "edge_count": int(edge_count),
        "total_weight": total_weight,
        "average_degree": finite_float((2 * edge_count) / node_count if node_count else 0.0),
        "density_directed": finite_float(edge_count / (node_count * (node_count - 1)) if node_count > 1 else 0.0),
        "reciprocity": finite_float(reciprocal_edge_share(edges)),
        "weak_component_count": int(len(component_sizes)),
        "largest_weak_component_nodes": int(largest_component_nodes),
        "largest_weak_component_share": finite_float(largest_component_nodes / node_count if node_count else 0.0),
        "vertex_connectivity": int(vertex_connectivity),
        "edge_connectivity": int(edge_connectivity),
        "articulation_point_count": int(articulation_point_count),
        "avg_clustering": clustering,
        "avg_shortest_path": avg_path,
        "diameter": int(diameter),
        "modularity": finite_float(modularity),
        "community_count": int(community_count),
        "path_metric_method": path_method,
        "avg_degree_centrality": average(degree_centrality),
        "avg_betweenness_centrality": average(betweenness_proxy),
        "avg_closeness_centrality": average(closeness),
        "avg_eigenvector_centrality": average([finite_float(value) for value in eigenvector]),
        "avg_pagerank_centrality": average([finite_float(value) for value in pagerank]),
        "avg_radiality": average(radiality),
        "avg_eccentricity": average(eccentricity),
        "centrality_method": centrality_method,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def fmt(value: object, digits: int = 12) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def diff_status(saas: object, recalculated: object, tolerance: float = 1e-9) -> str:
    if isinstance(saas, (int, float)) and isinstance(recalculated, (int, float)):
        return "OK" if abs(float(saas) - float(recalculated)) <= tolerance else "DIVERGE"
    return "OK" if saas == recalculated else "DIVERGE"


def metric_label(field: str) -> str:
    labels = {
        "node_count": "Vertices",
        "edge_count": "Arestas",
        "total_weight": "Peso total",
        "average_degree": "Grau medio",
        "density_directed": "Densidade",
        "reciprocity": "Reciprocidade",
        "weak_component_count": "Numero de componentes conexas",
        "largest_weak_component_nodes": "Vertices na maior componente",
        "largest_weak_component_share": "Participacao da maior componente",
        "vertex_connectivity": "Conectividade de vertices",
        "edge_connectivity": "Conectividade de arestas",
        "articulation_point_count": "Pontos de articulacao",
        "avg_clustering": "Clustering medio",
        "avg_shortest_path": "Caminho medio",
        "diameter": "Diametro",
        "modularity": "Modularidade",
        "community_count": "Comunidades",
        "avg_degree_centrality": "Centralidade de grau media",
        "avg_betweenness_centrality": "Centralidade de intermediacao media",
        "avg_closeness_centrality": "Centralidade de proximidade media",
        "avg_eigenvector_centrality": "Centralidade de autovetor media",
        "avg_pagerank_centrality": "PageRank medio",
        "avg_radiality": "Radialidade media",
        "avg_eccentricity": "Excentricidade media",
        "path_metric_method": "Metodo de caminhos",
        "centrality_method": "Metodo de centralidade",
    }
    return labels.get(field, field)


def write_report(expected: list[dict[str, object]], calculated: dict[str, dict[str, object]]) -> None:
    expected_by_key = {
        f"{row['layer']}:{row.get('scope', 'full')}": row
        for row in expected
    }
    lines = [
        "# Validacao das metricas do SaaS",
        "",
        "Fonte SaaS local: `Projeto_CR/app/visualization/public/graph-structural-metrics.json`.",
        "",
        f"Fonte recalculada: `{DB_PATH.as_posix()}`, tabela `edges_by_layer`.",
        "",
        "Esta validacao cobre dois escopos: `full` e `largest_component`.",
        "No escopo `largest_component`, o grafo e segmentado antes do calculo; portanto `sampled_64`, centralidades medias, conectividade, caminho medio e diametro sao calculados somente na componente gigante.",
        "",
        "## Formulas",
        "",
        "| Metrica | Forma de calculo |",
        "| --- | --- |",
        "| Vertices | `n = |V|` no escopo analisado. |",
        "| Arestas | `m = |E|` no escopo analisado. |",
        "| Peso total | Soma dos pesos das arestas do escopo. |",
        "| Densidade | `m / (n * (n - 1))` para grafo dirigido sem laco. |",
        "| Grau medio | `2m / n`. |",
        "| Reciprocidade | Fracao de arestas `i -> j` que possuem volta `j -> i`. |",
        "| Componentes fracas | Componentes conexas ignorando a direcao. |",
        "| Conectividade de vertices | `vertex_connectivity(G)` no grafo nao dirigido do escopo. |",
        "| Conectividade de arestas | `edge_connectivity(G)` no grafo nao dirigido do escopo. |",
        "| Pontos de articulacao | Vertices cuja remocao aumenta o numero de componentes conexas do escopo. |",
        "| Caminho medio e diametro | Exatos ate 2.500 vertices; acima disso usam amostra deterministica de 64 fontes (`sampled_64`). |",
        "| Centralidades medias | Media aritmetica das centralidades dos vertices do escopo. |",
        "",
    ]

    all_ok = True
    for layer in LAYERS:
        for scope in SCOPES:
            key = f"{layer}:{scope}"
            expected_row = expected_by_key[key]
            calculated_row = calculated[key]
            lines.extend([f"## Camada {layer} / {scope}", ""])
            lines.append("| Metrica | SaaS | Recalculado | Status |")
            lines.append("| --- | ---: | ---: | --- |")
            for field in [*NUMERIC_FIELDS, *TEXT_FIELDS]:
                status = diff_status(expected_row[field], calculated_row[field], tolerance=5e-7)
                all_ok = all_ok and status == "OK"
                lines.append(
                    f"| {metric_label(field)} | {fmt(expected_row[field])} | {fmt(calculated_row[field])} | {status} |"
                )
            lines.append("")
            lines.append(f"Tempo de recalc.: {calculated_row['elapsed_seconds']} s.")
            lines.append("")

    output_md = REPORT_DIR / "validacao_metricas_saas.md"
    output_json = REPORT_DIR / "validacao_metricas_saas.json"
    output_md.write_text("\n".join(lines), encoding="utf-8")
    output_json.write_text(
        json.dumps(
            {
                "all_ok": all_ok,
                "expected_saas": expected,
                "calculated": calculated,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"all_ok": all_ok, "markdown": str(output_md), "json": str(output_json)}, indent=2))


def main() -> None:
    expected = json.loads((PUBLIC_DIR / "graph-structural-metrics.json").read_text(encoding="utf-8"))
    combined_membership = fetch_combined_membership()
    calculated = {}
    for layer in LAYERS:
        edges = fetch_edges(layer)
        for scope in SCOPES:
            print(f"Calculando {layer}/{scope}...")
            calculated[f"{layer}:{scope}"] = calculate_metrics(
                layer,
                scope,
                edges,
                combined_membership,
            )
    write_report(expected, calculated)


if __name__ == "__main__":
    main()
