"""
Build a DuckDB graph store for the Reddit SNAP SaaS.

Inputs:
    Projeto_CR/data/processed/reddit_title_edges_gephi.csv
    Projeto_CR/data/processed/reddit_body_edges_gephi.csv

Output:
    Projeto_CR/data/processed/reddit_graph.duckdb

The database keeps title/body layers, combined edges, node metrics,
community assignments and layout coordinates for the full graph view.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import igraph as ig
import pandas as pd

try:
    import duckdb
except ImportError as exc:  # pragma: no cover - handled for CLI users
    raise SystemExit(
        "Missing dependency: duckdb. Install it with `python -m pip install duckdb`."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TITLE = PROJECT_ROOT / "data" / "processed" / "reddit_title_edges_gephi.csv"
DEFAULT_BODY = PROJECT_ROOT / "data" / "processed" / "reddit_body_edges_gephi.csv"
DEFAULT_DB = PROJECT_ROOT / "data" / "processed" / "reddit_graph.duckdb"
DEFAULT_SUMMARY = PROJECT_ROOT / "reports" / "duckdb_graph_store_summary.md"
DEFAULT_PATH_SAMPLE_SIZE = 64
DEFAULT_TOP_CONNECTIONS = 8
DEFAULT_CENTRALITY_CUTOFF = 4


def load_layer(path: Path, layer: str) -> pd.DataFrame:
    edges = pd.read_csv(path)
    required = {"Source", "Target", "weight", "positive", "negative", "first_seen", "last_seen"}
    missing = required - set(edges.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"{path} is missing required columns: {missing_text}")

    normalized = pd.DataFrame(
        {
            "layer": layer,
            "source": edges["Source"].astype(str).str.lower(),
            "target": edges["Target"].astype(str).str.lower(),
            "weight": edges["weight"].astype(int),
            "positive": edges["positive"].astype(int),
            "negative": edges["negative"].astype(int),
            "first_seen": pd.to_datetime(edges["first_seen"], errors="coerce"),
            "last_seen": pd.to_datetime(edges["last_seen"], errors="coerce"),
        }
    )
    normalized = normalized[normalized["source"] != normalized["target"]].copy()
    return normalized


def create_base_tables(con: duckdb.DuckDBPyConnection, title: Path, body: Path) -> None:
    title_edges = load_layer(title, "title")
    body_edges = load_layer(body, "body")
    raw_edges = pd.concat([title_edges, body_edges], ignore_index=True)

    con.register("raw_edges_df", raw_edges)
    con.execute("CREATE OR REPLACE TABLE edges_raw AS SELECT * FROM raw_edges_df")
    con.unregister("raw_edges_df")

    con.execute(
        """
        CREATE OR REPLACE TABLE edges_combined AS
        SELECT
          source,
          target,
          SUM(weight)::INTEGER AS weight,
          SUM(CASE WHEN layer = 'title' THEN weight ELSE 0 END)::INTEGER AS title_weight,
          SUM(CASE WHEN layer = 'body' THEN weight ELSE 0 END)::INTEGER AS body_weight,
          SUM(positive)::INTEGER AS positive,
          SUM(negative)::INTEGER AS negative,
          MIN(first_seen) AS first_seen,
          MAX(last_seen) AS last_seen,
          CASE
            WHEN SUM(weight) = 0 THEN 0
            ELSE (SUM(positive) - SUM(negative))::DOUBLE / SUM(weight)
          END AS sentiment_balance
        FROM edges_raw
        GROUP BY source, target
        """
    )

    create_edges_by_layer(con)


def create_edges_by_layer(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE edges_by_layer AS
        SELECT
          'combined' AS layer,
          source,
          target,
          weight,
          positive,
          negative,
          first_seen,
          last_seen,
          sentiment_balance
        FROM edges_combined
        UNION ALL
        SELECT
          layer,
          source,
          target,
          SUM(weight)::INTEGER AS weight,
          SUM(positive)::INTEGER AS positive,
          SUM(negative)::INTEGER AS negative,
          MIN(first_seen) AS first_seen,
          MAX(last_seen) AS last_seen,
          CASE
            WHEN SUM(weight) = 0 THEN 0
            ELSE (SUM(positive) - SUM(negative))::DOUBLE / SUM(weight)
          END AS sentiment_balance
        FROM edges_raw
        GROUP BY layer, source, target
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE node_strengths AS
        WITH incoming AS (
          SELECT target AS node, SUM(weight) AS in_strength
          FROM edges_combined
          GROUP BY target
        ),
        outgoing AS (
          SELECT source AS node, SUM(weight) AS out_strength
          FROM edges_combined
          GROUP BY source
        ),
        in_degree AS (
          SELECT target AS node, COUNT(*) AS in_degree
          FROM edges_combined
          GROUP BY target
        ),
        out_degree AS (
          SELECT source AS node, COUNT(*) AS out_degree
          FROM edges_combined
          GROUP BY source
        ),
        all_nodes AS (
          SELECT source AS node FROM edges_combined
          UNION
          SELECT target AS node FROM edges_combined
        )
        SELECT
          all_nodes.node,
          COALESCE(in_degree.in_degree, 0)::INTEGER AS in_degree,
          COALESCE(out_degree.out_degree, 0)::INTEGER AS out_degree,
          COALESCE(incoming.in_strength, 0)::INTEGER AS in_strength,
          COALESCE(outgoing.out_strength, 0)::INTEGER AS out_strength,
          (COALESCE(incoming.in_strength, 0) + COALESCE(outgoing.out_strength, 0))::INTEGER
            AS total_strength
        FROM all_nodes
        LEFT JOIN incoming USING (node)
        LEFT JOIN outgoing USING (node)
        LEFT JOIN in_degree USING (node)
        LEFT JOIN out_degree USING (node)
        """
    )


def fallback_layout(names: list[str], communities: dict[str, int]) -> dict[str, tuple[float, float]]:
    grouped: dict[int, list[str]] = {}
    for name in names:
        grouped.setdefault(communities.get(name, -1), []).append(name)

    community_ids = sorted(grouped, key=lambda community_id: len(grouped[community_id]), reverse=True)
    anchor_points = [
        (0.0, 0.0),
        (36.0, 3.0),
        (-35.0, 2.0),
        (2.0, 34.0),
        (0.0, -35.0),
        (55.0, 31.0),
        (-55.0, 30.0),
        (55.0, -30.0),
        (-55.0, -31.0),
        (78.0, 0.0),
        (-78.0, 0.0),
        (2.0, 63.0),
        (4.0, -64.0),
        (96.0, 38.0),
        (-96.0, 38.0),
        (96.0, -38.0),
        (-96.0, -38.0),
    ]
    golden_angle = math.pi * (3 - math.sqrt(5))
    positions: dict[str, tuple[float, float]] = {}

    for community_index, community_id in enumerate(community_ids):
        if community_index < len(anchor_points):
            center_x, center_y = anchor_points[community_index]
        else:
            outer_index = community_index - len(anchor_points) + 1
            radius = 115.0 + 3.8 * math.sqrt(outer_index)
            angle = outer_index * golden_angle
            center_x = radius * math.cos(angle)
            center_y = radius * math.sin(angle)

        members = grouped[community_id]
        local_radius = max(0.6, math.sqrt(len(members)) * 0.18)

        for member_index, name in enumerate(members):
            local_angle = 2 * math.pi * member_index / max(1, len(members))
            ring = 0.35 + 0.65 * math.sqrt((member_index + 1) / max(1, len(members)))
            positions[name] = (
                center_x + local_radius * ring * math.cos(local_angle),
                center_y + local_radius * ring * math.sin(local_angle),
            )

    return positions


def compute_graph_metrics(
    con: duckdb.DuckDBPyConnection,
    skip_layout: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    edges = con.execute(
        "SELECT source, target, weight, positive, negative FROM edges_combined"
    ).fetchdf()
    nodes = con.execute("SELECT * FROM node_strengths").fetchdf()

    tuples = list(edges[["source", "target", "weight"]].itertuples(index=False, name=None))
    directed = ig.Graph.TupleList(
        tuples,
        directed=True,
        vertex_name_attr="name",
        edge_attrs=["weight"],
    )
    directed.es["distance"] = [1 / max(1, weight) for weight in directed.es["weight"]]

    pagerank = directed.pagerank(weights="weight")
    undirected = directed.as_undirected(combine_edges={"weight": "sum", "distance": "min"})
    communities = undirected.community_leiden(weights="weight", objective_function="modularity")
    membership_by_name = {
        vertex["name"]: int(communities.membership[index])
        for index, vertex in enumerate(undirected.vs)
    }

    names = [vertex["name"] for vertex in directed.vs]
    pagerank_by_name = {
        vertex["name"]: float(pagerank[index])
        for index, vertex in enumerate(directed.vs)
    }

    if skip_layout:
        positions = fallback_layout(names, membership_by_name)
    else:
        try:
            layout = undirected.layout_lgl()
            positions = {
                vertex["name"]: (float(layout[index][0]), float(layout[index][1]))
                for index, vertex in enumerate(undirected.vs)
            }
        except Exception:
            positions = fallback_layout(names, membership_by_name)

    metrics = nodes.copy()
    metrics["pagerank"] = metrics["node"].map(pagerank_by_name).fillna(0.0)
    metrics["community_id"] = metrics["node"].map(membership_by_name).fillna(-1).astype(int)
    metrics["x"] = metrics["node"].map(lambda node: positions.get(node, (0.0, 0.0))[0])
    metrics["y"] = metrics["node"].map(lambda node: positions.get(node, (0.0, 0.0))[1])
    metrics["role"] = metrics.apply(classify_role, axis=1)

    community_summary = build_community_summary(metrics, edges)
    return metrics, community_summary


def classify_role(row: pd.Series) -> str:
    in_strength = int(row["in_strength"])
    out_strength = int(row["out_strength"])
    pagerank = float(row["pagerank"])

    if pagerank >= 0.001 and in_strength > 0 and out_strength > 0:
        return "hub"
    if out_strength >= 2 * max(1, in_strength):
        return "emissor"
    if in_strength >= 2 * max(1, out_strength):
        return "receptor"
    return "misto"


def build_community_summary(nodes: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    community_by_node = dict(zip(nodes["node"], nodes["community_id"]))
    edge_communities = edges.copy()
    edge_communities["source_community_id"] = edge_communities["source"].map(community_by_node)
    edge_communities["target_community_id"] = edge_communities["target"].map(community_by_node)
    edge_communities["is_internal"] = (
        edge_communities["source_community_id"] == edge_communities["target_community_id"]
    )

    base = (
        nodes.groupby("community_id")
        .agg(
            node_count=("node", "count"),
            total_strength=("total_strength", "sum"),
            avg_pagerank=("pagerank", "mean"),
            center_x=("x", "mean"),
            center_y=("y", "mean"),
        )
        .reset_index()
    )

    internal = (
        edge_communities[edge_communities["is_internal"]]
        .groupby("source_community_id")["weight"]
        .sum()
        .rename("internal_weight")
        .reset_index()
        .rename(columns={"source_community_id": "community_id"})
    )
    external = (
        edge_communities[~edge_communities["is_internal"]]
        .groupby("source_community_id")["weight"]
        .sum()
        .rename("outgoing_external_weight")
        .reset_index()
        .rename(columns={"source_community_id": "community_id"})
    )

    top_nodes = (
        nodes.sort_values(["community_id", "total_strength"], ascending=[True, False])
        .groupby("community_id")["node"]
        .apply(lambda values: ", ".join(values.head(8)))
        .rename("top_nodes")
        .reset_index()
    )

    summary = base.merge(internal, on="community_id", how="left")
    summary = summary.merge(external, on="community_id", how="left")
    summary = summary.merge(top_nodes, on="community_id", how="left")
    summary["internal_weight"] = summary["internal_weight"].fillna(0).astype(int)
    summary["outgoing_external_weight"] = summary["outgoing_external_weight"].fillna(0).astype(int)
    summary["label"] = summary["community_id"].map(lambda value: f"community_{int(value):03d}")
    return summary.sort_values("node_count", ascending=False)


def persist_metrics(
    con: duckdb.DuckDBPyConnection,
    nodes: pd.DataFrame,
    communities: pd.DataFrame,
) -> None:
    con.register("nodes_metrics_df", nodes)
    con.execute("CREATE OR REPLACE TABLE nodes AS SELECT * FROM nodes_metrics_df")
    con.unregister("nodes_metrics_df")

    con.register("communities_df", communities)
    con.execute("CREATE OR REPLACE TABLE communities AS SELECT * FROM communities_df")
    con.unregister("communities_df")

    con.execute(
        """
        CREATE OR REPLACE TABLE graph_stats AS
        WITH layer_edges AS (
          SELECT
            layer,
            COUNT(*) AS edges,
            SUM(weight)::INTEGER AS total_weight,
            SUM(positive)::INTEGER AS positive_links,
            SUM(negative)::INTEGER AS negative_links
          FROM edges_raw
          GROUP BY layer
        ),
        layer_nodes AS (
          SELECT layer, COUNT(DISTINCT node) AS nodes
          FROM (
            SELECT layer, source AS node FROM edges_raw
            UNION ALL
            SELECT layer, target AS node FROM edges_raw
          )
          GROUP BY layer
        )
        SELECT
          'combined' AS layer,
          (SELECT COUNT(*) FROM nodes) AS nodes,
          (SELECT COUNT(*) FROM edges_combined) AS edges,
          (SELECT SUM(weight) FROM edges_combined)::INTEGER AS total_weight,
          (SELECT SUM(positive) FROM edges_combined)::INTEGER AS positive_links,
          (SELECT SUM(negative) FROM edges_combined)::INTEGER AS negative_links,
          (SELECT COUNT(*) FROM communities) AS communities
        UNION ALL
        SELECT
          layer_edges.layer,
          layer_nodes.nodes,
          layer_edges.edges,
          layer_edges.total_weight,
          layer_edges.positive_links,
          layer_edges.negative_links,
          NULL::BIGINT AS communities
        FROM layer_edges
        JOIN layer_nodes USING (layer)
        """
    )


def create_node_analysis_tables(
    con: duckdb.DuckDBPyConnection,
    top_connections: int = DEFAULT_TOP_CONNECTIONS,
    sample_size: int = DEFAULT_PATH_SAMPLE_SIZE,
    centrality_cutoff: int = DEFAULT_CENTRALITY_CUTOFF,
) -> None:
    create_edges_by_layer(con)
    con.execute(
        """
        CREATE OR REPLACE TABLE node_layer_metrics AS
        WITH layer_nodes AS (
          SELECT layer, source AS node FROM edges_by_layer
          UNION
          SELECT layer, target AS node FROM edges_by_layer
        ),
        incoming AS (
          SELECT
            layer,
            target AS node,
            COUNT(*)::INTEGER AS in_degree,
            SUM(weight)::INTEGER AS in_strength
          FROM edges_by_layer
          GROUP BY layer, target
        ),
        outgoing AS (
          SELECT
            layer,
            source AS node,
            COUNT(*)::INTEGER AS out_degree,
            SUM(weight)::INTEGER AS out_strength
          FROM edges_by_layer
          GROUP BY layer, source
        ),
        incident_sentiment AS (
          SELECT
            layer,
            node,
            SUM(positive)::INTEGER AS positive_links,
            SUM(negative)::INTEGER AS negative_links
          FROM (
            SELECT layer, source AS node, positive, negative FROM edges_by_layer
            UNION ALL
            SELECT layer, target AS node, positive, negative FROM edges_by_layer
          )
          GROUP BY layer, node
        )
        SELECT
          layer_nodes.layer,
          layer_nodes.node,
          COALESCE(nodes.community_id, -1)::INTEGER AS community_id,
          COALESCE(nodes.role, 'misto') AS role,
          COALESCE(nodes.pagerank, 0)::DOUBLE AS pagerank,
          COALESCE(incoming.in_degree, 0)::INTEGER AS in_degree,
          COALESCE(outgoing.out_degree, 0)::INTEGER AS out_degree,
          (COALESCE(incoming.in_degree, 0) + COALESCE(outgoing.out_degree, 0))::INTEGER AS total_degree,
          COALESCE(incoming.in_strength, 0)::INTEGER AS in_strength,
          COALESCE(outgoing.out_strength, 0)::INTEGER AS out_strength,
          (COALESCE(incoming.in_strength, 0) + COALESCE(outgoing.out_strength, 0))::INTEGER AS total_strength,
          COALESCE(incident_sentiment.positive_links, 0)::INTEGER AS positive_links,
          COALESCE(incident_sentiment.negative_links, 0)::INTEGER AS negative_links,
          CASE
            WHEN COALESCE(incident_sentiment.positive_links, 0) + COALESCE(incident_sentiment.negative_links, 0) = 0
              THEN 0
            ELSE COALESCE(incident_sentiment.negative_links, 0)::DOUBLE /
              (COALESCE(incident_sentiment.positive_links, 0) + COALESCE(incident_sentiment.negative_links, 0))
          END AS negative_share
        FROM layer_nodes
        LEFT JOIN nodes ON nodes.node = layer_nodes.node
        LEFT JOIN incoming ON incoming.layer = layer_nodes.layer AND incoming.node = layer_nodes.node
        LEFT JOIN outgoing ON outgoing.layer = layer_nodes.layer AND outgoing.node = layer_nodes.node
        LEFT JOIN incident_sentiment
          ON incident_sentiment.layer = layer_nodes.layer
          AND incident_sentiment.node = layer_nodes.node
        """
    )

    create_node_centrality_metrics(con, sample_size=sample_size, centrality_cutoff=centrality_cutoff)
    con.execute(
        """
        CREATE OR REPLACE TABLE node_layer_metrics AS
        SELECT
          node_layer_metrics.*,
          COALESCE(node_centrality_metrics.degree_centrality, 0)::DOUBLE AS degree_centrality,
          COALESCE(node_centrality_metrics.betweenness_centrality, 0)::DOUBLE AS betweenness_centrality,
          COALESCE(node_centrality_metrics.closeness_centrality, 0)::DOUBLE AS closeness_centrality,
          COALESCE(node_centrality_metrics.eigenvector_centrality, 0)::DOUBLE AS eigenvector_centrality,
          COALESCE(node_centrality_metrics.pagerank_centrality, node_layer_metrics.pagerank, 0)::DOUBLE AS pagerank_centrality,
          COALESCE(node_centrality_metrics.radiality, 0)::DOUBLE AS radiality,
          COALESCE(node_centrality_metrics.eccentricity, 0)::DOUBLE AS eccentricity,
          COALESCE(node_centrality_metrics.centrality_method, 'unavailable') AS centrality_method,
          COALESCE(node_centrality_metrics.centrality_sample_size, 0)::INTEGER AS centrality_sample_size,
          COALESCE(node_centrality_metrics.centrality_cutoff, 0)::INTEGER AS centrality_cutoff
        FROM node_layer_metrics
        LEFT JOIN node_centrality_metrics
          ON node_layer_metrics.layer = node_centrality_metrics.layer
          AND node_layer_metrics.node = node_centrality_metrics.node
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE node_top_connections AS
        WITH directional_edges AS (
          SELECT
            layer,
            source AS node,
            target AS neighbor,
            'outgoing' AS direction,
            weight,
            positive,
            negative,
            sentiment_balance,
            first_seen,
            last_seen
          FROM edges_by_layer
          UNION ALL
          SELECT
            layer,
            target AS node,
            source AS neighbor,
            'incoming' AS direction,
            weight,
            positive,
            negative,
            sentiment_balance,
            first_seen,
            last_seen
          FROM edges_by_layer
        ),
        ranked AS (
          SELECT
            *,
            ROW_NUMBER() OVER (
              PARTITION BY layer, node, direction
              ORDER BY weight DESC, neighbor
            ) AS rank
          FROM directional_edges
        )
        SELECT
          ranked.layer,
          ranked.node,
          ranked.direction,
          ranked.rank::INTEGER AS rank,
          ranked.neighbor,
          COALESCE(nodes.community_id, -1)::INTEGER AS neighbor_community_id,
          COALESCE(nodes.role, 'misto') AS neighbor_role,
          ranked.weight::INTEGER AS weight,
          ranked.positive::INTEGER AS positive,
          ranked.negative::INTEGER AS negative,
          ranked.sentiment_balance,
          ranked.first_seen,
          ranked.last_seen
        FROM ranked
        LEFT JOIN nodes ON nodes.node = ranked.neighbor
        WHERE ranked.rank <= ?
        ORDER BY ranked.layer, ranked.node, ranked.direction, ranked.rank
        """,
        [top_connections],
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


def normalized_betweenness(values: list[float], node_count: int) -> list[float]:
    denominator = ((node_count - 1) * (node_count - 2)) / 2 if node_count > 2 else 1
    return [finite_float(value / denominator) for value in values]


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


def compute_layer_node_centralities(
    layer: str,
    edges: pd.DataFrame,
    sample_size: int,
    centrality_cutoff: int,
) -> list[dict[str, object]]:
    if edges.empty:
        return []

    tuples = list(edges[["source", "target", "weight"]].itertuples(index=False, name=None))
    directed = ig.Graph.TupleList(
        tuples,
        directed=True,
        vertex_name_attr="name",
        edge_attrs=["weight"],
    )
    undirected = directed.as_undirected(combine_edges={"weight": "sum"})
    node_count = undirected.vcount()
    edge_count = undirected.ecount()
    if node_count == 0:
        return []

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
        betweenness = [
            finite_float(degree_centrality[index] * (1 - local_clustering[index]))
            for index in range(node_count)
        ]
    except Exception:
        betweenness = degree_centrality

    components = undirected.connected_components()
    giant = components.giant() if components else ig.Graph()
    _, sampled_diameter, path_method = sampled_path_metrics(giant, sample_size)
    sources = centrality_sources(undirected, sample_size)
    closeness, radiality, eccentricity = sampled_distance_profiles(
        undirected,
        sources=sources,
        diameter=sampled_diameter,
    )
    method = (
        f"degree_exact;pagerank_weighted;"
        f"eigenvector_weighted;betweenness_proxy_degree_clustering;"
        f"distance_{path_method}"
    )

    return [
        {
            "layer": layer,
            "node": vertex["name"],
            "degree_centrality": degree_centrality[index],
            "betweenness_centrality": finite_float(betweenness[index]),
            "closeness_centrality": finite_float(closeness[index]),
            "eigenvector_centrality": finite_float(eigenvector[index]),
            "pagerank_centrality": finite_float(pagerank[index]),
            "radiality": finite_float(radiality[index]),
            "eccentricity": finite_float(eccentricity[index]),
            "centrality_method": method,
            "centrality_sample_size": int(len(sources)),
            "centrality_cutoff": int(centrality_cutoff),
            "centrality_node_count": int(node_count),
            "centrality_edge_count": int(edge_count),
        }
        for index, vertex in enumerate(undirected.vs)
    ]


def create_node_centrality_metrics(
    con: duckdb.DuckDBPyConnection,
    sample_size: int = DEFAULT_PATH_SAMPLE_SIZE,
    centrality_cutoff: int = DEFAULT_CENTRALITY_CUTOFF,
) -> pd.DataFrame:
    create_edges_by_layer(con)
    rows: list[dict[str, object]] = []
    for layer in ("combined", "title", "body"):
        edges = con.execute(
            """
            SELECT source, target, weight
            FROM edges_by_layer
            WHERE layer = ?
            """,
            [layer],
        ).fetchdf()
        rows.extend(
            compute_layer_node_centralities(
                layer=layer,
                edges=edges,
                sample_size=sample_size,
                centrality_cutoff=centrality_cutoff,
            )
        )

    centrality_metrics = pd.DataFrame(rows)
    con.register("node_centrality_metrics_df", centrality_metrics)
    con.execute(
        "CREATE OR REPLACE TABLE node_centrality_metrics AS SELECT * FROM node_centrality_metrics_df"
    )
    con.unregister("node_centrality_metrics_df")
    return centrality_metrics


def finite_float(value: float | int | None) -> float:
    if value is None:
        return 0.0
    value = float(value)
    return value if math.isfinite(value) else 0.0


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

    average = distance_sum / distance_count if distance_count else 0.0
    return finite_float(average), diameter_lower_bound, f"sampled_{len(sources)}"


def reciprocal_edge_share(edges: pd.DataFrame) -> float:
    if edges.empty:
        return 0.0
    pairs = set(zip(edges["source"], edges["target"]))
    reciprocated = sum(1 for source, target in pairs if (target, source) in pairs)
    return reciprocated / len(pairs) if pairs else 0.0


def compute_layer_structural_metrics(
    layer: str,
    edges: pd.DataFrame,
    combined_membership: dict[str, int],
    sample_size: int,
    scope: str = "full",
) -> dict[str, object]:
    if edges.empty:
        return {
            "layer": layer,
            "scope": scope,
            "node_count": 0,
            "edge_count": 0,
            "total_weight": 0,
            "average_degree": 0.0,
            "density_directed": 0.0,
            "reciprocity": 0.0,
            "weak_component_count": 0,
            "largest_weak_component_nodes": 0,
            "largest_weak_component_share": 0.0,
            "vertex_connectivity": 0,
            "edge_connectivity": 0,
            "avg_clustering": 0.0,
            "avg_shortest_path": 0.0,
            "diameter": 0,
            "modularity": 0.0,
            "community_count": 0,
            "path_metric_method": "empty",
            "avg_degree_centrality": 0.0,
            "avg_betweenness_centrality": 0.0,
            "avg_closeness_centrality": 0.0,
            "avg_eigenvector_centrality": 0.0,
            "avg_pagerank_centrality": 0.0,
            "avg_radiality": 0.0,
            "avg_eccentricity": 0.0,
            "centrality_method": "empty",
        }

    tuples = list(edges[["source", "target", "weight"]].itertuples(index=False, name=None))
    directed = ig.Graph.TupleList(
        tuples,
        directed=True,
        vertex_name_attr="name",
        edge_attrs=["weight"],
    )
    undirected = directed.as_undirected(combine_edges={"weight": "sum"})
    node_count = directed.vcount()
    edge_count = directed.ecount()
    total_weight = int(edges["weight"].sum())
    average_degree = (2 * edge_count) / node_count if node_count else 0.0
    density = edge_count / (node_count * (node_count - 1)) if node_count > 1 else 0.0

    components = undirected.connected_components()
    component_sizes = components.sizes()
    largest_component_nodes = max(component_sizes) if component_sizes else 0
    giant = components.giant() if largest_component_nodes else ig.Graph()
    avg_path, diameter, path_method = sampled_path_metrics(giant, sample_size)
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

    clustering = finite_float(undirected.transitivity_avglocal_undirected(mode="zero"))

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
        betweenness = [
            finite_float(degree_centrality[index] * (1 - local_clustering[index]))
            for index in range(node_count)
        ]
    except Exception:
        betweenness = degree_centrality

    sources = centrality_sources(undirected, sample_size)
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
        "average_degree": finite_float(average_degree),
        "density_directed": finite_float(density),
        "reciprocity": finite_float(reciprocal_edge_share(edges)),
        "weak_component_count": int(len(component_sizes)),
        "largest_weak_component_nodes": int(largest_component_nodes),
        "largest_weak_component_share": finite_float(largest_component_nodes / node_count if node_count else 0),
        "vertex_connectivity": vertex_connectivity,
        "edge_connectivity": edge_connectivity,
        "avg_clustering": clustering,
        "avg_shortest_path": avg_path,
        "diameter": int(diameter),
        "modularity": finite_float(modularity),
        "community_count": int(community_count),
        "path_metric_method": path_method,
        "avg_degree_centrality": average_values(degree_centrality),
        "avg_betweenness_centrality": average_values(betweenness),
        "avg_closeness_centrality": average_values(closeness),
        "avg_eigenvector_centrality": average_values(
            [finite_float(value) for value in eigenvector]
        ),
        "avg_pagerank_centrality": average_values(
            [finite_float(value) for value in pagerank]
        ),
        "avg_radiality": average_values(radiality),
        "avg_eccentricity": average_values(eccentricity),
        "centrality_method": centrality_method,
    }


def average_values(values: list[float]) -> float:
    return finite_float(sum(values) / len(values)) if values else 0.0


def largest_component_edges(edges: pd.DataFrame) -> pd.DataFrame:
    if edges.empty:
        return edges

    tuples = list(edges[["source", "target", "weight"]].itertuples(index=False, name=None))
    directed = ig.Graph.TupleList(
        tuples,
        directed=True,
        vertex_name_attr="name",
        edge_attrs=["weight"],
    )
    undirected = directed.as_undirected(combine_edges={"weight": "sum"})
    components = undirected.connected_components()
    if not components:
        return edges.iloc[0:0].copy()

    component_sizes = components.sizes()
    largest_component_id = max(
        range(len(component_sizes)),
        key=lambda component_id: component_sizes[component_id],
    )
    largest_nodes = {
        vertex["name"]
        for index, vertex in enumerate(undirected.vs)
        if components.membership[index] == largest_component_id
    }
    return edges[
        edges["source"].isin(largest_nodes)
        & edges["target"].isin(largest_nodes)
    ].copy()


def create_structural_metrics_table(
    con: duckdb.DuckDBPyConnection,
    sample_size: int = DEFAULT_PATH_SAMPLE_SIZE,
) -> pd.DataFrame:
    create_edges_by_layer(con)
    combined_membership = dict(
        con.execute("SELECT node, community_id FROM nodes").fetchall()
    )
    rows = []
    for layer in ("combined", "title", "body"):
        edges = con.execute(
            """
            SELECT source, target, weight
            FROM edges_by_layer
            WHERE layer = ?
            """,
            [layer],
        ).fetchdf()
        rows.append(
            compute_layer_structural_metrics(
                layer=layer,
                edges=edges,
                combined_membership=combined_membership,
                sample_size=sample_size,
                scope="full",
            )
        )
        rows.append(
            compute_layer_structural_metrics(
                layer=layer,
                edges=largest_component_edges(edges),
                combined_membership=combined_membership,
                sample_size=sample_size,
                scope="largest_component",
            )
        )

    metrics = pd.DataFrame(rows)
    con.register("graph_structural_metrics_df", metrics)
    con.execute(
        "CREATE OR REPLACE TABLE graph_structural_metrics AS SELECT * FROM graph_structural_metrics_df"
    )
    con.unregister("graph_structural_metrics_df")
    return metrics


def create_analysis_tables(
    con: duckdb.DuckDBPyConnection,
    sample_size: int = DEFAULT_PATH_SAMPLE_SIZE,
    top_connections: int = DEFAULT_TOP_CONNECTIONS,
    centrality_cutoff: int = DEFAULT_CENTRALITY_CUTOFF,
) -> pd.DataFrame:
    create_node_analysis_tables(
        con,
        top_connections=top_connections,
        sample_size=sample_size,
        centrality_cutoff=centrality_cutoff,
    )
    return create_structural_metrics_table(con, sample_size=sample_size)


def write_summary(
    con: duckdb.DuckDBPyConnection,
    output: Path,
    db_path: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    stats = con.execute("SELECT * FROM graph_stats ORDER BY layer").fetchdf()
    top_communities = con.execute(
        """
        SELECT community_id, label, node_count, internal_weight, top_nodes
        FROM communities
        ORDER BY node_count DESC
        LIMIT 12
        """
    ).fetchdf()
    structural_metrics = con.execute(
        """
        SELECT
          layer,
          scope,
          average_degree,
          density_directed,
          reciprocity,
          weak_component_count,
          largest_weak_component_share,
          vertex_connectivity,
          edge_connectivity,
          avg_clustering,
          avg_shortest_path,
          diameter,
          modularity,
          avg_betweenness_centrality,
          avg_closeness_centrality,
          avg_eigenvector_centrality,
          avg_radiality,
          avg_eccentricity,
          path_metric_method
        FROM graph_structural_metrics
        ORDER BY layer, scope
        """
    ).fetchdf()

    lines = [
        "# DuckDB graph store",
        "",
        f"Banco gerado: `{db_path.as_posix()}`",
        "",
        "## Estatisticas",
        "",
        "| camada | vertices | arestas | peso total | positivos/neutros | negativos | comunidades |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in stats.itertuples(index=False):
        communities = "" if pd.isna(row.communities) else int(row.communities)
        lines.append(
            "| "
            f"{row.layer} | {int(row.nodes)} | {int(row.edges)} | "
            f"{int(row.total_weight)} | {int(row.positive_links)} | "
            f"{int(row.negative_links)} | {communities} |"
        )

    lines.extend(
        [
            "",
            "## Maiores comunidades",
            "",
            "| id | rotulo | vertices | peso interno | top subreddits |",
            "| ---: | --- | ---: | ---: | --- |",
        ]
    )
    for row in top_communities.itertuples(index=False):
        lines.append(
            "| "
            f"{int(row.community_id)} | {row.label} | {int(row.node_count)} | "
            f"{int(row.internal_weight)} | {row.top_nodes} |"
        )

    lines.extend(
        [
            "",
            "## Metricas estruturais prontas",
            "",
            "| camada | escopo | grau medio | densidade | reciprocidade | componentes | maior componente | coesao V | coesao E | clustering | caminho | diametro | modularidade | intermed. media | proxim. media | autovetor medio | radial. media | excentr. media | metodo |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in structural_metrics.itertuples(index=False):
        lines.append(
            "| "
            f"{row.layer} | {row.scope} | {row.average_degree:.3f} | {row.density_directed:.6f} | "
            f"{row.reciprocity:.3f} | {int(row.weak_component_count)} | "
            f"{row.largest_weak_component_share:.3f} | {int(row.vertex_connectivity)} | "
            f"{int(row.edge_connectivity)} | {row.avg_clustering:.3f} | "
            f"{row.avg_shortest_path:.3f} | {int(row.diameter)} | {row.modularity:.3f} | "
            f"{row.avg_betweenness_centrality:.6f} | {row.avg_closeness_centrality:.3f} | "
            f"{row.avg_eigenvector_centrality:.3f} | {row.avg_radiality:.3f} | "
            f"{row.avg_eccentricity:.3f} | {row.path_metric_method} |"
        )

    lines.extend(
        [
            "",
            "## Uso no SaaS",
            "",
            "- `nodes` guarda comunidade, papel estrutural, PageRank e coordenadas `x`, `y`.",
            "- `edges_combined` guarda a rede combinada `title + body`.",
            "- `node_layer_metrics` guarda perfil numerico por subreddit e camada.",
            "- `node_top_connections` guarda as principais conexoes de entrada e saida por subreddit.",
            "- `node_centrality_metrics` guarda centralidades por subreddit e camada.",
            "- `graph_structural_metrics` guarda ordem, tamanho, coesoes, densidade, centralidades medias, componentes, clustering, caminho medio, diametro e modularidade.",
            "- `communities` guarda os agrupamentos para rotulos e contornos no mapa.",
            "- `graph_stats` guarda resumo para os cards do painel.",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build DuckDB tables for the full Reddit graph SaaS."
    )
    parser.add_argument("--title", type=Path, default=DEFAULT_TITLE)
    parser.add_argument("--body", type=Path, default=DEFAULT_BODY)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--skip-layout",
        action="store_true",
        help="Use a fast fallback layout grouped by community.",
    )
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Only refresh derived analysis tables in an existing DuckDB graph store.",
    )
    parser.add_argument(
        "--path-sample-size",
        type=int,
        default=DEFAULT_PATH_SAMPLE_SIZE,
        help="Number of source nodes used for sampled path metrics on large components.",
    )
    parser.add_argument(
        "--top-connections",
        type=int,
        default=DEFAULT_TOP_CONNECTIONS,
        help="Top incoming/outgoing connections stored per node and layer.",
    )
    parser.add_argument(
        "--centrality-cutoff",
        type=int,
        default=DEFAULT_CENTRALITY_CUTOFF,
        help="Shortest-path depth used for cutoff betweenness centrality on large graphs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(args.db))
    if args.analysis_only:
        structural_metrics = create_analysis_tables(
            con,
            sample_size=args.path_sample_size,
            top_connections=args.top_connections,
            centrality_cutoff=args.centrality_cutoff,
        )
        write_summary(con, args.summary, args.db)
        payload = {
            "database": str(args.db),
            "summary": str(args.summary),
            "analysisOnly": True,
            "structuralMetrics": structural_metrics.to_dict(orient="records"),
        }
        print(json.dumps(payload, indent=2))
        return

    create_base_tables(con, args.title, args.body)
    nodes, communities = compute_graph_metrics(con, skip_layout=args.skip_layout)
    persist_metrics(con, nodes, communities)
    structural_metrics = create_analysis_tables(
        con,
        sample_size=args.path_sample_size,
        top_connections=args.top_connections,
        centrality_cutoff=args.centrality_cutoff,
    )
    write_summary(con, args.summary, args.db)

    payload = {
        "database": str(args.db),
        "summary": str(args.summary),
        "nodes": int(len(nodes)),
        "communities": int(len(communities)),
        "structuralMetrics": structural_metrics.to_dict(orient="records"),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
