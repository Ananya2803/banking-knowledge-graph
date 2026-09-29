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


def draw(G, client_id, out_dir="output"):
    sub = client_subgraph(G, client_id)
    net = Network(height="700px", width="100%", directed=True, cdn_resources="remote")
    for n, d in sub.nodes(data=True):
        details = "\n".join(f"{k}: {v}" for k, v in d.items())
        color = "#000000" if d.get("defaulted") else COLORS[d["type"]]
        net.add_node(n, label=n, title=details, color=color, size=25 if n == node_id("Client", client_id) else 15)
    for u, v, d in sub.edges(data=True):
        net.add_edge(u, v, label=d["type"], title=str({k: val for k, val in d.items() if k != "type"}))

    Path(out_dir).mkdir(exist_ok=True)
    path = Path(out_dir) / f"client_{client_id}.html"
    net.write_html(str(path), notebook=False)
    return path
