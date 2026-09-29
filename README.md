# Banking Knowledge Graph

A small knowledge graph of a real (anonymised) retail bank: its **clients, accounts, loans, cards, branches and payments**. It's used to answer lending questions: a customer 360 view, credit risk, and cross-sell leads.

Built with **Python + NetworkX**, with an optional export to **Neo4j / Cypher**.

## Dataset

[Berka / PKDD'99 Financial Dataset](https://web.archive.org/web/2007/http://lisp.vse.cz/pkdd99/berka.htm): real data from a Czech bank (1993–1998), released publicly for research.
`python main.py download` fetches it and translates the Czech codes into the clean English CSVs in [`data/`](data/). The large transactions table is not used.

## The graph

```mermaid
graph LR
    Client -- HOLDS {role} --> Account
    Client -- LIVES_IN --> District
    Client -- HAS_CARD --> Card
    Account -- HAS_LOAN --> Loan
    Account -- BRANCH_IN --> District
    Account -- "PAYS {amount, purposes}" --> Bank
```

| Nodes | Count | | Edges | Count |
|---|---:|---|---|---:|
| Client | 5,369 | | PAYS | 6,141 |
| Account | 4,500 | | HOLDS | 5,369 |
| Card | 892 | | LIVES_IN | 5,369 |
| Loan | 682 | | BRANCH_IN | 4,500 |
| District | 77 | | HAS_CARD | 892 |
| Bank | 13 | | HAS_LOAN | 682 |

**11,533 nodes and 22,953 edges, all in one connected graph.**

## Questions it answers

| # | Question | How (graph walk) |
|---|---|---|
| 1 | **Customer 360:** what do we know about client X? | Client → accounts → loans, cards, standing orders, co-holders, district |
| 2 | **Credit risk by region:** where do loans go bad? | Loan ← Account → District |
| 3 | **Does a joint account change risk?** | Count `HOLDS` edges into each loan's account |
| 4 | **Cross-sell:** who should we offer a card, insurance or refinance to? | Client's loans, cards and payment purposes; skip anyone linked to a default |
| 5 | **How are two entities connected?** | Shortest path between any two nodes |

### Key findings

**Joint accounts almost never default.** Loans on accounts with a second holder had **0 defaults out of 145**. Loans on single-holder accounts had **76 defaults out of 537 (14.2%)**. This signal only exists because the data is modelled as relationships.

| Account | Loans | Defaults | Default rate |
|---|---:|---:|---:|
| joint | 145 | 0 | 0.0% |
| single holder | 537 | 76 | 14.2% |

**Risk varies about 10× by region:** from 1.6% (north Bohemia) to 15.8% (west Bohemia).

**Cross-sell leads (clients in good standing only):** 522 insurance, 441 credit card, 35 loan refinance.

## Run it

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python main.py stats              # graph size
python main.py customer 2         # customer 360 for client 2
python main.py risk               # default rate by region / account type
python main.py leads              # cross-sell leads
python main.py path client:1 loan:5314
python main.py draw 2             # interactive graph -> output/client_2.html
pytest                            # tests
```

The data is already in `data/`. Run `python main.py download` only if you want to re-create it.

### Optional: Neo4j

```bash
python main.py neo4j              # writes neo4j/import/*.csv
```
Copy those CSVs into Neo4j's `import` folder, then run [`neo4j/load.cypher`](neo4j/load.cypher). [`neo4j/queries.cypher`](neo4j/queries.cypher) has the same questions in Cypher (Neo4j 5+).

## Project layout

```
kg/download.py      download + clean the dataset -> data/*.csv
kg/build_graph.py   CSVs -> NetworkX graph (nodes + relationships)
kg/queries.py       the business questions above
kg/visualize.py     interactive HTML view of one client (PyVis)
kg/export_neo4j.py  graph -> CSVs for Neo4j
main.py             command-line entry point
tests/              pytest checks against the real data
```
