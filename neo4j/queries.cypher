// The same business questions as kg/queries.py, written in Cypher.

// 1. Customer 360: one client and everything around them
MATCH (c:Client {id: 'client:2'})-[r]-(n)
OPTIONAL MATCH (n:Account)-[r2]-(m) WHERE m <> c
RETURN c, r, n, r2, m;

// 2. Default rate by region
MATCH (l:Loan)<-[:HAS_LOAN]-(:Account)-[:BRANCH_IN]->(d:District)
RETURN d.region AS region,
       count(l) AS loans,
       sum(CASE WHEN l.defaulted THEN 1 ELSE 0 END) AS defaults,
       round(100.0 * avg(CASE WHEN l.defaulted THEN 1 ELSE 0 END), 1) AS default_rate
ORDER BY default_rate DESC;

// 3. Single-holder vs joint accounts
MATCH (l:Loan)<-[:HAS_LOAN]-(a:Account)
WITH l, COUNT { (:Client)-[:HOLDS]->(a) } AS holders
RETURN CASE WHEN holders > 1 THEN 'joint' ELSE 'single holder' END AS account,
       count(l) AS loans,
       round(100.0 * avg(CASE WHEN l.defaulted THEN 1 ELSE 0 END), 1) AS default_rate;

// 4. Cross-sell: borrowers in good standing without a credit card
MATCH (c:Client)-[:HOLDS {role: 'owner'}]->(:Account)-[:HAS_LOAN]->(l:Loan)
WHERE NOT l.defaulted AND NOT (c)-[:HAS_CARD]->(:Card)
RETURN c.id AS client, 'credit_card' AS offer
LIMIT 25;

// 5. How are two entities connected?
MATCH p = shortestPath((a {id: 'client:1'})-[*..8]-(b {id: 'loan:5314'}))
RETURN p;
