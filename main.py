"""Command-line entry point.

    python main.py download            # fetch + clean the dataset into data/
    python main.py stats               # node / edge counts
    python main.py customer 2          # customer 360 view of client 2
    python main.py risk                # default rate by region and by account type
    python main.py leads               # cross-sell leads
    python main.py path client:1 client:2
    python main.py draw 2              # output/client_2.html
    python main.py neo4j               # CSVs for neo4j/load.cypher
"""

import argparse
import json

from kg import queries
from kg.build_graph import build_graph, summary


def main():
    parser = argparse.ArgumentParser(description="Banking knowledge graph (Berka dataset)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("download")
    sub.add_parser("stats")
    sub.add_parser("customer").add_argument("client_id", type=int)
    sub.add_parser("risk")
    sub.add_parser("leads")
    p = sub.add_parser("path")
    p.add_argument("source")
    p.add_argument("target")
    sub.add_parser("draw").add_argument("client_id", type=int)
    sub.add_parser("neo4j")
    args = parser.parse_args()

    if args.command == "download":
        from kg import download
        download.main()
        return

    G = build_graph()

    if args.command == "stats":
        nodes, edges = summary(G)
        print(f"{G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges\n")
        print(nodes.to_string(), "\n")
        print(edges.to_string())

    elif args.command == "customer":
        print(json.dumps(queries.customer_360(G, args.client_id), indent=2, default=str))

    elif args.command == "risk":
        print("Default rate by region (%)\n")
        print(queries.risk_by_region(G).to_string(), "\n")
        print("Default rate: single-holder vs joint accounts (%)\n")
        print(queries.risk_by_account_holders(G).to_string())

    elif args.command == "leads":
        leads = queries.cross_sell_leads(G)
        print(leads["offer"].value_counts().to_string(), "\n")
        print(leads.groupby("offer").head(3).to_string(index=False))

    elif args.command == "path":
        print("\n".join(queries.explain_connection(G, args.source, args.target)))

    elif args.command == "draw":
        from kg.visualize import draw
        print(f"Saved {draw(G, args.client_id)} - open it in a browser")

    elif args.command == "neo4j":
        from kg.export_neo4j import export
        print("Wrote neo4j/import/:", ", ".join(export(G)))


if __name__ == "__main__":
    main()
