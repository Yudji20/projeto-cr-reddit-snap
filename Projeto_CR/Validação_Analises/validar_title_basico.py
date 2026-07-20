from pathlib import Path
import json
import pandas as pd

root = Path("..").resolve()

edges = pd.read_csv(root / "data/processed/reddit_body_edges_gephi.csv")

summary = json.loads(
    (root / "app/visualization/public/graph-data-summary.json")
    .read_text(encoding="utf-8")
)

print("Arestas no CSV:", len(edges))
print("Arestas no SaaS:", summary["edgeCount"]["title"])

print("Source vazios:", edges["Source"].isna().sum())
print("Target vazios:", edges["Target"].isna().sum())

peso_ok = (edges["weight"] == edges["positive"] + edges["negative"]).all()
print("weight = positive + negative:", peso_ok)

print("Tipos encontrados:", edges["Type"].unique())