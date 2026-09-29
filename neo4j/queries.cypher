// The same business questions as kg/queries.py, written in Cypher.
// Run them all with `python main.py neo4j-query`, or paste one into the Neo4j Aura query editor.

// 0. What is in the graph?
MATCH (n)
RETURN labels(n)[0] AS label, count(*) AS nodes
ORDER BY nodes DESC;

// 1. Customer 360: client 2, their accounts, co-holders, loans and district
MATCH (c:Client {id: 'client:2'})-[h:HOLDS]->(a:Account)
MATCH (c)-[:LIVES_IN]->(d:District)
OPTIONAL MATCH (a)-[:HAS_LOAN]->(l:Loan)
OPTIONAL MATCH (other:Client)-[:HOLDS]->(a) WHERE other <> c
OPTIONAL MATCH (c)-[:HAS_CARD]->(card:Card)
RETURN c.id AS client, d.name AS district, a.id AS account, h.role AS role,
       collect(DISTINCT other.id) AS co_holders,
       collect(DISTINCT l.status) AS loans,
       collect(DISTINCT card.card_type) AS cards;

// 2. Default rate by region
MATCH (l:Loan)<-[:HAS_LOAN]-(:Account)-[:BRANCH_IN]->(d:District)
RETURN d.region AS region,
       count(l) AS loans,
       sum(CASE WHEN l.defaulted THEN 1 ELSE 0 END) AS defaults,
       round(100.0 * avg(CASE WHEN l.defaulted THEN 1.0 ELSE 0.0 END), 1) AS default_rate
ORDER BY default_rate DESC;

// 3. Single-holder vs joint accounts
MATCH (l:Loan)<-[:HAS_LOAN]-(a:Account)
WITH l, COUNT { (:Client)-[:HOLDS]->(a) } AS holders
RETURN CASE WHEN holders > 1 THEN 'joint' ELSE 'single holder' END AS account,
       count(l) AS loans,
       sum(CASE WHEN l.defaulted THEN 1 ELSE 0 END) AS defaults,
       round(100.0 * avg(CASE WHEN l.defaulted THEN 1.0 ELSE 0.0 END), 1) AS default_rate;

// 4. Cross-sell: borrowers in good standing without a credit card
MATCH (c:Client)-[:HOLDS {role: 'owner'}]->(:Account)-[:HAS_LOAN]->(l:Loan)
WHERE NOT l.defaulted AND NOT (c)-[:HAS_CARD]->(:Card)
RETURN count(DISTINCT c) AS credit_card_leads;

// 5. How is client 1 connected to loan 5314?
MATCH (a:Client {id: 'client:1'}), (b:Loan {id: 'loan:5314'})
MATCH p = shortestPath((a)-[*..8]-(b))
RETURN [n IN nodes(p) | n.id] AS path, [r IN relationships(p) | type(r)] AS via;
