from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"

FILES = {
    "title": RAW_DIR / "soc-redditHyperlinks-title.tsv",
    "body": RAW_DIR / "soc-redditHyperlinks-body.tsv",
}


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def inspect_file(path: Path) -> dict:
    source_nodes: set[str] = set()
    target_nodes: set[str] = set()
    sentiment_counts: Counter[str] = Counter()
    min_timestamp: datetime | None = None
    max_timestamp: datetime | None = None
    rows = 0

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = reader.fieldnames or []

        for row in reader:
            rows += 1
            source_nodes.add(row["SOURCE_SUBREDDIT"])
            target_nodes.add(row["TARGET_SUBREDDIT"])
            sentiment_counts[row["LINK_SENTIMENT"]] += 1

            timestamp = parse_timestamp(row["TIMESTAMP"])
            if min_timestamp is None or timestamp < min_timestamp:
                min_timestamp = timestamp
            if max_timestamp is None or timestamp > max_timestamp:
                max_timestamp = timestamp

    all_nodes = source_nodes | target_nodes

    return {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "size_bytes": path.stat().st_size,
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        "columns": columns,
        "rows": rows,
        "unique_source_subreddits": len(source_nodes),
        "unique_target_subreddits": len(target_nodes),
        "unique_total_subreddits": len(all_nodes),
        "sentiment_counts": dict(sorted(sentiment_counts.items())),
        "min_timestamp": min_timestamp.isoformat(sep=" ") if min_timestamp else None,
        "max_timestamp": max_timestamp.isoformat(sep=" ") if max_timestamp else None,
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    results = {name: inspect_file(path) for name, path in FILES.items()}

    output_path = REPORTS_DIR / "inspecao_inicial_raw.json"
    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

