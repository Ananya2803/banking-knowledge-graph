"""Load the knowledge graph into Neo4j and run the Cypher queries in neo4j/queries.cypher.

Works with Neo4j Aura (free cloud) or a local Neo4j. Put the connection in a .env file:

    NEO4J_URI=neo4j+s://<id>.databases.neo4j.io
    NEO4J_USERNAME=...
    NEO4J_PASSWORD=...
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

from kg.queries import props

QUERIES_FILE = Path(__file__).resolve().parent.parent / "neo4j" / "queries.cypher"
BATCH = 2000


def connect():
    load_dotenv()
    try:
        uri, user, password = (os.environ[k] for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"))
    except KeyError as missing:
        raise SystemExit(f"Set {missing} in .env (see README)") from None
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver


def plain(value):
    """numpy/pandas scalars -> plain Python values the driver accepts."""
    return value.item() if hasattr(value, "item") else value


def run_batched(driver, cypher, rows):
    for i in range(0, len(rows), BATCH):
        driver.execute_query(cypher, rows=rows[i:i + BATCH])


def load(G):
    """Copy every node and relationship of G into Neo4j (replacing what we loaded before)."""
    labels = sorted({d["type"] for _, d in G.nodes(data=True)})
    with connect() as driver:
        # Start clean, but only delete our own node labels.
        driver.execute_query(f"MATCH (n) WHERE n:{' OR n:'.join(labels)} DETACH DELETE n")

        for label in labels:
            # A uniqueness constraint also gives a fast index on id.
            driver.execute_query(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE")
            rows = [{"id": n, "props": {k: plain(v) for k, v in props(d).items()}}
                    for n, d in G.nodes(data=True) if d["type"] == label]
            run_batched(driver, f"UNWIND $rows AS r MERGE (n:{label} {{id: r.id}}) SET n += r.props", rows)
            print(f"  {label:<9} {len(rows):>6,} nodes")

        edges_by_type = {}
        for u, v, d in G.edges(data=True):
            edges_by_type.setdefault((d["type"], G.nodes[u]["type"], G.nodes[v]["type"]), []).append(
                {"source": u, "target": v, "props": {k: plain(x) for k, x in props(d).items()}})
        for (rel, src, dst), rows in sorted(edges_by_type.items()):
            run_batched(driver, f"""
                UNWIND $rows AS r
                MATCH (a:{src} {{id: r.source}}), (b:{dst} {{id: r.target}})
                MERGE (a)-[e:{rel}]->(b) SET e += r.props""", rows)
            print(f"  {rel:<9} {len(rows):>6,} relationships  ({src} -> {dst})")


def read_queries(path=QUERIES_FILE):
    """Split queries.cypher into (title, cypher) pairs. Each query starts with a '// title' line."""
    queries = []
    for block in path.read_text().split(";"):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        titles = [l[2:].strip() for l in lines if l.startswith("//")]
        cypher = "\n".join(l for l in lines if not l.startswith("//"))
        if cypher:
            queries.append((titles[-1] if titles else "query", cypher))
    return queries


def run_queries():
    with connect() as driver:
        for title, cypher in read_queries():
            records, _, keys = driver.execute_query(cypher)
            print(f"\n{title}\n{'-' * len(title)}")
            print(" | ".join(keys))
            for r in records:
                print(" | ".join(str(r[k]) for k in keys))
