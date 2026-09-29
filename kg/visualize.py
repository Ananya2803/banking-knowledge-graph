"""Draw a client's neighbourhood as an interactive HTML graph (PyVis)."""

from pathlib import Path

from pyvis.network import Network

from kg.build_graph import node_id

COLORS = {
    "Client": "#4C78A8", "Account": "#F58518", "Loan": "#E45756",
    "Card": "#72B7B2", "District": "#54A24B", "Bank": "#B279A2",
}


def client_subgraph(G, client_id, hops=2):
    """The client plus everything within `hops` steps.

    District and Bank nodes are hubs (thousands of links), so we stop there
    instead of pulling in every other client in the same district.
    """
    start = node_id("Client", client_id)
    keep, frontier = {start}, {start}
    for _ in range(hops):
        nxt = set()
        for n in frontier:
            if G.nodes[n]["type"] in ("District", "Bank") and n != start:
                continue  # don't expand through hubs
            nxt |= set(G.successors(n)) | set(G.predecessors(n))
        frontier = nxt - keep
        keep |= nxt
    return G.subgraph(keep)


def district_subgraph(G, district_id):
    """One district, the clients who live there, and their accounts, loans, cards and banks."""
    district = node_id("District", district_id)
    keep = {district}
    for client in G.predecessors(district):
        if G.nodes[client]["type"] != "Client":
            continue
        keep.add(client)
        for n in G.successors(client):  # accounts and cards
            if G.nodes[n]["type"] == "Account":
                keep.add(n)
                keep |= {x for x in G.successors(n) if G.nodes[x]["type"] != "District"}  # loans, banks
            elif G.nodes[n]["type"] == "Card":
                keep.add(n)
    return G.subgraph(keep)


def save_html(sub, filename, highlight=None, edge_labels=True, out_dir="output"):
    """Write a subgraph as an interactive HTML page. Defaulted loans are drawn black."""
    net = Network(height="800px", width="100%", directed=True, cdn_resources="remote")
    for n, d in sub.nodes(data=True):
        details = "\n".join(f"{k}: {v}" for k, v in d.items())
        color = "#000000" if d.get("defaulted") else COLORS[d["type"]]
        net.add_node(n, label=n, title=details, color=color, size=30 if n == highlight else 15)
    for u, v, d in sub.edges(data=True):
        net.add_edge(u, v, label=d["type"] if edge_labels else None,
                     title=str({k: val for k, val in d.items()}))

    Path(out_dir).mkdir(exist_ok=True)
    path = Path(out_dir) / filename
    net.write_html(str(path), notebook=False)
    return path


def draw(G, client_id):
    return save_html(client_subgraph(G, client_id), f"client_{client_id}.html",
                     highlight=node_id("Client", client_id))


def draw_district(G, district_id):
    # Edge labels are hidden here (hover an edge to see its type); ~150 labels are unreadable.
    return save_html(district_subgraph(G, district_id), f"district_{district_id}.html",
                     highlight=node_id("District", district_id), edge_labels=False)
