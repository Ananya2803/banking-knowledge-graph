"""Business questions answered by walking the knowledge graph.

Every function takes the graph built by build_graph() and only uses nodes and
edges -- no table joins -- to show how relationships answer lending questions.
"""

import networkx as nx
import pandas as pd

from kg.build_graph import node_id


def out_nbrs(G, node, edge_type):
    """Nodes reached from `node` over outgoing edges of `edge_type`."""
    return [v for v in G.successors(node) if G.edges[node, v]["type"] == edge_type]


def in_nbrs(G, node, edge_type):
    """Nodes that point to `node` over edges of `edge_type`."""
    return [u for u in G.predecessors(node) if G.edges[u, node]["type"] == edge_type]


def key(node):
    """'client:42' -> 42"""
    return int(node.split(":")[1])


def key_str(node):
    """'bank:AB' -> 'AB'"""
    return node.split(":")[1]


def props(attrs):
    """Node/edge attributes without the internal 'type' field."""
    return {k: v for k, v in attrs.items() if k != "type"}


def is_defaulter(G, client):
    """True if any account the client holds has a defaulted loan."""
    return any(
        G.nodes[loan]["defaulted"]
        for account in out_nbrs(G, client, "HOLDS")
        for loan in out_nbrs(G, account, "HAS_LOAN")
    )


# 1. Customer 360 ---------------------------------------------------------------

def customer_360(G, client_id):
    """Everything the bank knows about one client, gathered from its neighbourhood."""
    client = node_id("Client", client_id)
    if client not in G:
        raise KeyError(f"No client with id {client_id}")

    district = out_nbrs(G, client, "LIVES_IN")[0]
    accounts = []
    for account in out_nbrs(G, client, "HOLDS"):
        co_holders = [key(c) for c in in_nbrs(G, account, "HOLDS") if c != client]
        accounts.append({
            "account_id": key(account),
            "role": G.edges[client, account]["role"],
            "opened": G.nodes[account]["opened"],
            "co_holders": co_holders,
            "loans": [{"loan_id": key(l), **props(G.nodes[l])} for l in out_nbrs(G, account, "HAS_LOAN")],
            "standing_orders": [
                {"bank": key_str(b), **props(G.edges[account, b])} for b in out_nbrs(G, account, "PAYS")
            ],
        })

    return {
        "client_id": client_id,
        **props(G.nodes[client]),
        "district": G.nodes[district]["name"],
        "region": G.nodes[district]["region"],
        "accounts": accounts,
        "cards": [G.nodes[c]["card_type"] for c in out_nbrs(G, client, "HAS_CARD")],
        "has_defaulted": is_defaulter(G, client),
    }


# 2. Credit risk by region --------------------------------------------------------

def risk_by_region(G):
    """Loan default rate per region: Loan <-HAS_LOAN- Account -BRANCH_IN-> District."""
    rows = []
    for loan, data in G.nodes(data=True):
        if data["type"] != "Loan":
            continue
        account = in_nbrs(G, loan, "HAS_LOAN")[0]
        district = out_nbrs(G, account, "BRANCH_IN")[0]
        rows.append({"region": G.nodes[district]["region"], "defaulted": data["defaulted"]})

    df = pd.DataFrame(rows)
    out = df.groupby("region")["defaulted"].agg(loans="count", defaults="sum", default_rate="mean")
    out["default_rate"] = (out["default_rate"] * 100).round(1)
    return out.sort_values("default_rate", ascending=False)


# 3. Risk by relationship: single vs joint accounts --------------------------------

def risk_by_account_holders(G):
    """Does having a second person on the account change default risk?

    The number of HOLDS edges into an account is a feature that only
    exists because we modelled relationships.
    """
    rows = []
    for loan, data in G.nodes(data=True):
        if data["type"] != "Loan":
            continue
        account = in_nbrs(G, loan, "HAS_LOAN")[0]
        holders = len(in_nbrs(G, account, "HOLDS"))
        rows.append({"account": "joint" if holders > 1 else "single holder", "defaulted": data["defaulted"]})

    df = pd.DataFrame(rows)
    out = df.groupby("account")["defaulted"].agg(loans="count", defaults="sum", default_rate="mean")
    out["default_rate"] = (out["default_rate"] * 100).round(1)
    return out


# 4. Cross-sell leads ---------------------------------------------------------------

def cross_sell_leads(G):
    """Product offers for clients in good standing, based on what they are connected to.

    - Credit card:      account owner with a loan, but no card.
    - Insurance:        pays an insurance premium by standing order (buys insurance elsewhere).
    - Loan refinance:   repays a loan by standing order, but that loan is not with us.
    Clients linked to a defaulted loan are never offered anything.
    """
    leads = []
    for client, data in G.nodes(data=True):
        if data["type"] != "Client" or is_defaulter(G, client):
            continue
        for account in out_nbrs(G, client, "HOLDS"):
            if G.edges[client, account]["role"] != "owner":
                continue
            has_loan = bool(out_nbrs(G, account, "HAS_LOAN"))
            purposes = {p for bank in out_nbrs(G, account, "PAYS") for p in G.edges[account, bank]["purposes"]}

            if has_loan and not out_nbrs(G, client, "HAS_CARD"):
                leads.append((key(client), "credit_card", "borrower in good standing without a card"))
            if "insurance" in purposes:
                leads.append((key(client), "insurance", "pays an insurance premium by standing order"))
            if "loan_repayment" in purposes and not has_loan:
                leads.append((key(client), "loan_refinance", "repays a loan that is not with us"))

    return pd.DataFrame(leads, columns=["client_id", "offer", "reason"])


# 5. How are two things connected? --------------------------------------------------

def explain_connection(G, source, target):
    """Shortest chain of relationships between two nodes, e.g. 'client:1' and 'client:2'."""
    path = nx.shortest_path(G.to_undirected(as_view=True), source, target)
    steps = []
    for a, b in zip(path, path[1:]):
        if G.has_edge(a, b):
            steps.append(f"{a} -[{G.edges[a, b]['type']}]-> {b}")
        else:
            steps.append(f"{a} <-[{G.edges[b, a]['type']}]- {b}")
    return steps
