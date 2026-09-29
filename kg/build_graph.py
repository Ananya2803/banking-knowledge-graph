"""Turn the bank CSVs into a knowledge graph (NetworkX).

Nodes                         Edges
-----                         -----
Client   (gender, birth_year) Client  -[HOLDS {role}]->          Account
Account  (opened, frequency)  Client  -[LIVES_IN]->              District
Loan     (amount, status)     Client  -[HAS_CARD]->              Card
Card     (type, issued)       Account -[HAS_LOAN]->              Loan
District (region, salary...)  Account -[BRANCH_IN]->             District
Bank     (recipient bank)     Account -[PAYS {amount, purposes}]-> Bank

Node ids are prefixed with their type, e.g. "client:42", so ids never collide.
"""

from pathlib import Path

import networkx as nx
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def node_id(kind, key):
    return f"{kind.lower()}:{key}"


def load_tables(data_dir=DATA_DIR):
    names = ["clients", "accounts", "account_holders", "loans", "cards", "payment_orders", "districts"]
    missing = [n for n in names if not (data_dir / f"{n}.csv").exists()]
    if missing:
        raise FileNotFoundError(f"Missing {missing} in {data_dir}. Run: python main.py download")
    return {n: pd.read_csv(data_dir / f"{n}.csv") for n in names}


def add_nodes(G, df, kind, key):
    for row in df.to_dict("records"):
        G.add_node(node_id(kind, row.pop(key)), type=kind, **row)


def build_graph(data_dir=DATA_DIR):
    t = load_tables(data_dir)
    G = nx.DiGraph()

    # 1. Entities
    add_nodes(G, t["districts"], "District", "district_id")
    add_nodes(G, t["clients"].drop(columns="district_id"), "Client", "client_id")
    add_nodes(G, t["accounts"].drop(columns="district_id"), "Account", "account_id")
    add_nodes(G, t["loans"].drop(columns="account_id"), "Loan", "loan_id")
    add_nodes(G, t["cards"].drop(columns="disp_id"), "Card", "card_id")
    for bank in t["payment_orders"]["bank_to"].unique():
        G.add_node(node_id("Bank", bank), type="Bank")

    # 2. Relationships
    for r in t["clients"].itertuples():
        G.add_edge(node_id("Client", r.client_id), node_id("District", r.district_id), type="LIVES_IN")

    for r in t["accounts"].itertuples():
        G.add_edge(node_id("Account", r.account_id), node_id("District", r.district_id), type="BRANCH_IN")

    for r in t["account_holders"].itertuples():
        G.add_edge(node_id("Client", r.client_id), node_id("Account", r.account_id), type="HOLDS", role=r.role)

    for r in t["loans"].itertuples():
        G.add_edge(node_id("Account", r.account_id), node_id("Loan", r.loan_id), type="HAS_LOAN")

    # A card belongs to an account holder (disp_id), so link it to that client.
    cards = t["cards"].merge(t["account_holders"], on="disp_id")
    for r in cards.itertuples():
        G.add_edge(node_id("Client", r.client_id), node_id("Card", r.card_id), type="HAS_CARD")

    # One PAYS edge per (account, bank): total monthly amount + what the payments are for.
    pays = t["payment_orders"].groupby(["account_id", "bank_to"]).agg(
        amount=("amount", "sum"), purposes=("purpose", lambda p: sorted(set(p)))
    )
    for (account_id, bank), r in pays.iterrows():
        G.add_edge(node_id("Account", account_id), node_id("Bank", bank), type="PAYS",
                   amount=round(r.amount, 2), purposes=r.purposes)

    return G


def summary(G):
    """Count nodes and edges by type."""
    nodes = pd.Series([d["type"] for _, d in G.nodes(data=True)]).value_counts()
    edges = pd.Series([d["type"] for *_, d in G.edges(data=True)]).value_counts()
    return nodes, edges
