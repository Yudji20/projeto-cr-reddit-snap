"""
Export DuckDB graph data to static assets for the interactive web view.

Input:
    Projeto_CR/data/processed/reddit_graph.duckdb

Outputs:
    Projeto_CR/app/visualization/public/graph-data.json
    Projeto_CR/app/visualization/public/graph-data-summary.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "processed" / "reddit_graph.duckdb"
DEFAULT_PUBLIC = PROJECT_ROOT / "app" / "visualization" / "public"

COMMUNITY_PALETTE = [
    "#4f7cff",
    "#ef476f",
    "#06a77d",
    "#f59e0b",
    "#7c3aed",
    "#14b8a6",
    "#e11d48",
    "#2563eb",
    "#84cc16",
    "#f97316",
    "#0891b2",
    "#be185d",
    "#65a30d",
    "#9333ea",
    "#dc2626",
    "#0284c7",
]


LABEL_RULES = [
    ("gaming", {"gaming", "pcmasterrace", "games", "destinythegame", "ps4", "xboxone", "nintendo", "dota2", "leagueoflegends"}),
    ("news / politics", {"worldnews", "news", "politics", "sandersforpresident", "the_donald", "conspiracy"}),
    ("technology", {"android", "buildapc", "techsupport", "programming", "linux", "technology", "sysadmin"}),
    ("popular / memes", {"askreddit", "funny", "pics", "todayilearned", "videos", "bestof", "titlegore"}),
    ("controversial topics", {"subredditdrama", "drama", "kotakuinaction", "mensrights", "thebluepill", "srssucks"}),
    ("music / media", {"music", "hiphopheads", "electronicmusic", "television", "movies", "books"}),
    ("fiction / writing", {"writingprompts", "nosleep", "dnd", "rpg", "worldbuilding", "fantasy"}),
    ("adult communities", {"gonewild", "tipofmypenis", "gonewildaudio", "dirtypenpals", "gwabackstage"}),
    ("crypto / markets", {"bitcoin", "dogecoin", "cryptocurrency", "ethereum", "darknetmarkets", "buttcoin"}),
    ("europe", {"europe", "unitedkingdom", "france", "de", "sweden", "ireland"}),
    ("sports", {"nba", "nfl", "soccer", "hockey", "baseball", "mma", "fitness"}),
    ("science / health", {"science", "fitness", "drugs", "nofap", "vegan", "loseit"}),
]


def infer_label(top_nodes: str, fallback: str) -> str:
    names = {name.strip().lower() for name in top_nodes.split(",") if name.strip()}
    for label, keywords in LABEL_RULES:
        if names.intersection(keywords):
            return label
    return fallback


def scale_size(total_strength: int, pagerank: float) -> float:
    strength_part = math.log1p(max(0, total_strength)) * 0.95
    pagerank_part = math.sqrt(max(0.0, pagerank)) * 35
    return round(max(1.8, min(18.0, 1.6 + strength_part + pagerank_part)), 3)


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    return bool(
        con.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = ?
            LIMIT 1
            """,
            [table_name],
        ).fetchall()
    )


def clean_number(value):
    if value is None:
        return 0
    if isinstance(value, float) and not math.isfinite(value):
        return 0
    return value


def write_json_asset(path: Path, payload, *, compact: bool = False) -> None:
    temp_path = path.with_name(f"{path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        if compact:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"), default=clean_number)
        else:
            json.dump(payload, handle, ensure_ascii=False, indent=2, default=clean_number)
    temp_path.replace(path)


def export_assets(db_path: Path, public_dir: Path) -> dict:
    public_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=True)

    nodes_rows = con.execute(
        """
        WITH node_sentiment AS (
          SELECT
            node,
            SUM(positive)::INTEGER AS positive_links,
            SUM(negative)::INTEGER AS negative_links
          FROM (
            SELECT source AS node, positive, negative FROM edges_combined
            UNION ALL
            SELECT target AS node, positive, negative FROM edges_combined
          )
          GROUP BY node
        )
        SELECT
          nodes.node,
          nodes.community_id,
          nodes.role,
          nodes.in_degree,
          nodes.out_degree,
          nodes.in_strength,
          nodes.out_strength,
          nodes.total_strength,
          nodes.pagerank,
          nodes.x,
          nodes.y,
          COALESCE(node_sentiment.positive_links, 0) AS positive_links,
          COALESCE(node_sentiment.negative_links, 0) AS negative_links
        FROM nodes
        LEFT JOIN node_sentiment ON nodes.node = node_sentiment.node
        ORDER BY nodes.node
        """
    ).fetchall()

    communities_rows = con.execute(
        """
        SELECT
          community_id,
          label,
          node_count,
          internal_weight,
          outgoing_external_weight,
          top_nodes,
          center_x,
          center_y
        FROM communities
        ORDER BY node_count DESC
        """
    ).fetchall()

    node_index = {row[0]: index for index, row in enumerate(nodes_rows)}
    community_rank = {
        row[0]: rank
        for rank, row in enumerate(communities_rows)
    }
    community_display_labels = {
        row[0]: infer_label(row[5] or "", row[1])
        for row in communities_rows
    }

    nodes = []
    bounds = {
        "minX": float("inf"),
        "maxX": float("-inf"),
        "minY": float("inf"),
        "maxY": float("-inf"),
    }
    for row in nodes_rows:
        (
            node,
            community_id,
            role,
            in_degree,
            out_degree,
            in_strength,
            out_strength,
            total_strength,
            pagerank,
            x,
            y,
            positive_links,
            negative_links,
        ) = row
        signed_total = max(1, int(positive_links) + int(negative_links))
        negative_share = int(negative_links) / signed_total
        color = "#dc3558" if negative_share >= 0.28 else "#5376d9"
        size = scale_size(total_strength, pagerank)
        x = float(x)
        y = float(y)
        bounds["minX"] = min(bounds["minX"], x)
        bounds["maxX"] = max(bounds["maxX"], x)
        bounds["minY"] = min(bounds["minY"], y)
        bounds["maxY"] = max(bounds["maxY"], y)
        nodes.append(
            {
                "id": node,
                "community": int(community_id),
                "communityLabel": community_display_labels.get(community_id, f"community_{community_id:03d}"),
                "role": role,
                "inDegree": int(in_degree),
                "outDegree": int(out_degree),
                "inStrength": int(in_strength),
                "outStrength": int(out_strength),
                "totalStrength": int(total_strength),
                "pagerank": round(float(pagerank), 9),
                "positiveLinks": int(positive_links),
                "negativeLinks": int(negative_links),
                "negativeShare": round(negative_share, 5),
                "x": round(x, 6),
                "y": round(y, 6),
                "size": size,
                "color": color,
            }
        )

    def format_edge_date(value) -> str | None:
        if value is None:
            return None
        if hasattr(value, "date"):
            return value.date().isoformat()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)[:10]

    def fetch_edges(table: str) -> list[dict]:
        rows = con.execute(
            f"""
            SELECT source, target, weight, positive, negative, sentiment_balance, first_seen, last_seen
            FROM {table}
            WHERE source != target
            ORDER BY weight DESC
            """
        ).fetchall()
        edges = []
        for source, target, weight, positive, negative, sentiment_balance, first_seen, last_seen in rows:
            if source not in node_index or target not in node_index:
                continue
            edge = {
                "s": node_index[source],
                "t": node_index[target],
                "w": int(weight),
                "p": int(positive),
                "n": int(negative),
                "b": round(float(sentiment_balance), 5),
            }
            first_seen_text = format_edge_date(first_seen)
            last_seen_text = format_edge_date(last_seen)
            if first_seen_text is not None:
                edge["f"] = first_seen_text
            if last_seen_text is not None:
                edge["l"] = last_seen_text
            edges.append(edge)
        return edges

    layer_edges = {
        "combined": fetch_edges("edges_combined"),
        "title": fetch_edges("(SELECT source, target, weight, positive, negative, first_seen, last_seen, CASE WHEN weight = 0 THEN 0 ELSE (positive - negative)::DOUBLE / weight END AS sentiment_balance FROM edges_raw WHERE layer = 'title')"),
        "body": fetch_edges("(SELECT source, target, weight, positive, negative, first_seen, last_seen, CASE WHEN weight = 0 THEN 0 ELSE (positive - negative)::DOUBLE / weight END AS sentiment_balance FROM edges_raw WHERE layer = 'body')"),
    }

    communities = []
    for row in communities_rows:
        (
            community_id,
            stored_label,
            node_count,
            internal_weight,
            outgoing_external_weight,
            top_nodes,
            center_x,
            center_y,
        ) = row
        rank = community_rank[community_id]
        communities.append(
            {
                "id": int(community_id),
                "rank": rank,
                "label": community_display_labels[community_id],
                "storedLabel": stored_label,
                "nodeCount": int(node_count),
                "internalWeight": int(internal_weight),
                "outgoingExternalWeight": int(outgoing_external_weight),
                "topNodes": top_nodes,
                "x": round(float(center_x), 6),
                "y": round(float(center_y), 6),
                "color": COMMUNITY_PALETTE[rank % len(COMMUNITY_PALETTE)],
            }
        )

    stats = con.execute("SELECT * FROM graph_stats ORDER BY layer").fetchdf().to_dict(orient="records")
    structural_metrics = []
    structural_metrics_path = None
    structural_metrics_asset = None
    if table_exists(con, "graph_structural_metrics"):
        structural_metrics = (
            con.execute("SELECT * FROM graph_structural_metrics ORDER BY layer")
            .fetchdf()
            .to_dict(orient="records")
        )
        structural_metrics_path = public_dir / "graph-structural-metrics.json"
        structural_metrics_asset = structural_metrics_path.name
        write_json_asset(structural_metrics_path, structural_metrics)

    node_profile_paths = {}
    if table_exists(con, "node_layer_metrics") and table_exists(con, "node_top_connections"):
        metric_rows = con.execute(
            """
            SELECT
              layer,
              node,
              community_id,
              role,
              pagerank,
              in_degree,
              out_degree,
              total_degree,
              in_strength,
              out_strength,
              total_strength,
              positive_links,
              negative_links,
              negative_share,
              degree_centrality,
              betweenness_centrality,
              closeness_centrality,
              eigenvector_centrality,
              pagerank_centrality,
              radiality,
              eccentricity,
              centrality_method,
              centrality_sample_size,
              centrality_cutoff
            FROM node_layer_metrics
            ORDER BY layer, node
            """
        ).fetchall()
        connection_rows = con.execute(
            """
            SELECT
              layer,
              node,
              direction,
              rank,
              neighbor,
              neighbor_community_id,
              neighbor_role,
              weight,
              positive,
              negative,
              sentiment_balance,
              first_seen,
              last_seen
            FROM node_top_connections
            ORDER BY layer, node, direction, rank
            """
        ).fetchall()

        profiles_by_layer: dict[str, dict[str, dict]] = {}
        for row in metric_rows:
            (
                layer,
                node,
                community_id,
                role,
                pagerank,
                in_degree,
                out_degree,
                total_degree,
                in_strength,
                out_strength,
                total_strength,
                positive_links,
                negative_links,
                negative_share,
                degree_centrality,
                betweenness_centrality,
                closeness_centrality,
                eigenvector_centrality,
                pagerank_centrality,
                radiality,
                eccentricity,
                centrality_method,
                centrality_sample_size,
                centrality_cutoff,
            ) = row
            profiles_by_layer.setdefault(layer, {})[node] = {
                "node": node,
                "community": int(community_id),
                "communityLabel": community_display_labels.get(community_id, f"community_{community_id:03d}"),
                "role": role,
                "pagerank": round(float(pagerank or 0), 9),
                "inDegree": int(in_degree),
                "outDegree": int(out_degree),
                "totalDegree": int(total_degree),
                "inStrength": int(in_strength),
                "outStrength": int(out_strength),
                "totalStrength": int(total_strength),
                "positiveLinks": int(positive_links),
                "negativeLinks": int(negative_links),
                "negativeShare": round(float(negative_share or 0), 5),
                "degreeCentrality": round(float(degree_centrality or 0), 9),
                "betweennessCentrality": round(float(betweenness_centrality or 0), 9),
                "closenessCentrality": round(float(closeness_centrality or 0), 9),
                "eigenvectorCentrality": round(float(eigenvector_centrality or 0), 9),
                "pagerankCentrality": round(float(pagerank_centrality or 0), 9),
                "radiality": round(float(radiality or 0), 9),
                "eccentricity": round(float(eccentricity or 0), 3),
                "centralityMethod": centrality_method,
                "centralitySampleSize": int(centrality_sample_size or 0),
                "centralityCutoff": int(centrality_cutoff or 0),
                "topIncoming": [],
                "topOutgoing": [],
            }

        for row in connection_rows:
            (
                layer,
                node,
                direction,
                rank,
                neighbor,
                neighbor_community_id,
                neighbor_role,
                weight,
                positive,
                negative,
                sentiment_balance,
                first_seen,
                last_seen,
            ) = row
            profile = profiles_by_layer.get(layer, {}).get(node)
            if profile is None:
                continue
            bucket = "topIncoming" if direction == "incoming" else "topOutgoing"
            connection = {
                "rank": int(rank),
                "neighbor": neighbor,
                "neighborCommunity": int(neighbor_community_id),
                "neighborCommunityLabel": community_display_labels.get(
                    neighbor_community_id,
                    f"community_{neighbor_community_id:03d}",
                ),
                "neighborRole": neighbor_role,
                "weight": int(weight),
                "positive": int(positive),
                "negative": int(negative),
                "sentimentBalance": round(float(sentiment_balance or 0), 5),
            }
            first_seen_text = format_edge_date(first_seen)
            last_seen_text = format_edge_date(last_seen)
            if first_seen_text is not None:
                connection["firstSeen"] = first_seen_text
            if last_seen_text is not None:
                connection["lastSeen"] = last_seen_text
            profile[bucket].append(connection)

        for layer, profiles in profiles_by_layer.items():
            path = public_dir / f"node-profiles-{layer}.json"
            write_json_asset(path, profiles, compact=True)
            node_profile_paths[layer] = path.name

    data = {
        "meta": {
            "generatedFrom": str(db_path),
            "nodeCount": len(nodes),
            "edgeCount": {layer: len(edges) for layer, edges in layer_edges.items()},
            "communityCount": len(communities),
            "bounds": bounds,
        },
        "stats": stats,
        "structuralMetrics": structural_metrics,
        "nodes": nodes,
        "edges": layer_edges,
        "communities": communities,
    }

    core_path = public_dir / "graph-core.json"
    summary_path = public_dir / "graph-data-summary.json"
    edge_paths = {
        layer: public_dir / f"edges-{layer}.json"
        for layer in layer_edges
    }

    write_json_asset(
        core_path,
        {
            "meta": data["meta"],
            "stats": stats,
            "nodes": nodes,
            "communities": communities,
        },
        compact=True,
    )
    for layer, edges in layer_edges.items():
        write_json_asset(edge_paths[layer], edges, compact=True)

    write_json_asset(
        summary_path,
        {
            "nodeCount": len(nodes),
            "edgeCount": data["meta"]["edgeCount"],
            "communityCount": len(communities),
            "largestCommunities": communities[:20],
            "stats": stats,
            "structuralMetrics": structural_metrics,
            "analysisFiles": {
                "structuralMetrics": structural_metrics_asset,
                "nodeProfiles": node_profile_paths,
            },
        },
    )
    return {
        "core": str(core_path),
        "edgeFiles": {layer: str(path) for layer, path in edge_paths.items()},
        "summary": str(summary_path),
        "nodes": len(nodes),
        "edges": data["meta"]["edgeCount"],
        "communities": len(communities),
        "analysisFiles": {
            "structuralMetrics": structural_metrics_asset,
            "nodeProfiles": node_profile_paths,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export graph web assets from DuckDB.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--public-dir", type=Path, default=DEFAULT_PUBLIC)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = export_assets(args.db, args.public_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
