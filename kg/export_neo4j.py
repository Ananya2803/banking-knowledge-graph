"""Export the graph as CSVs that neo4j/load.cypher imports into Neo4j.

One CSV per node type (Client.csv, Loan.csv, ...) and one per relationship
type (HOLDS.csv, PAYS.csv, ...). Node ids keep their "client:42" form.
"""

from pathlib import Path

import pandas as pd

from kg.queries import props

OUT_DIR = Path(__file__).resolve().parent.parent / "neo4j" / "import"


def export(G, out_dir=OUT_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build one table per type so each keeps its own column types (ints stay ints).
    node_types = {d["type"] for _, d in G.nodes(data=True)}
    for node_type in node_types:
        rows = [{"id": n, **props(d)} for n, d in G.nodes(data=True) if d["type"] == node_type]
        pd.DataFrame(rows).to_csv(out_dir / f"{node_type}.csv", index=False)

    edge_types = {d["type"] for *_, d in G.edges(data=True)}
    for edge_type in edge_types:
        rows = [{"source": u, "target": v, **props(d)} for u, v, d in G.edges(data=True) if d["type"] == edge_type]
        df = pd.DataFrame(rows)
        if "purposes" in df:
            df["purposes"] = df["purposes"].map("|".join)  # Cypher: split(row.purposes, '|')
        df.to_csv(out_dir / f"{edge_type}.csv", index=False)

    return sorted(p.name for p in out_dir.glob("*.csv"))
