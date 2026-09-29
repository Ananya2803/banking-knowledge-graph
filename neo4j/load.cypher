// Load the knowledge graph into Neo4j.
// 1. python main.py neo4j                       (writes neo4j/import/*.csv)
// 2. copy neo4j/import/*.csv into your Neo4j "import" folder
// 3. run this file in Neo4j Browser / cypher-shell

// ---------- Constraints (also create indexes on id) ----------
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Client)   REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Account)  REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Loan)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Card)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:District) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Bank)     REQUIRE n.id IS UNIQUE;

// ---------- Nodes ----------
LOAD CSV WITH HEADERS FROM 'file:///District.csv' AS r
MERGE (d:District {id: r.id})
SET d.name = r.name, d.region = r.region, d.inhabitants = toInteger(r.inhabitants),
    d.avg_salary = toInteger(r.avg_salary), d.unemployment_rate = toFloat(r.unemployment_rate);

LOAD CSV WITH HEADERS FROM 'file:///Client.csv' AS r
MERGE (c:Client {id: r.id})
SET c.gender = r.gender, c.birth_year = toInteger(r.birth_year);

LOAD CSV WITH HEADERS FROM 'file:///Account.csv' AS r
MERGE (a:Account {id: r.id})
SET a.statement_frequency = r.statement_frequency, a.opened = date(r.opened);

LOAD CSV WITH HEADERS FROM 'file:///Loan.csv' AS r
MERGE (l:Loan {id: r.id})
SET l.date = date(r.date), l.amount = toInteger(r.amount), l.duration_months = toInteger(r.duration_months),
    l.monthly_payment = toFloat(r.monthly_payment), l.status = r.status, l.defaulted = (r.defaulted = 'True');

LOAD CSV WITH HEADERS FROM 'file:///Card.csv' AS r
MERGE (c:Card {id: r.id})
SET c.card_type = r.card_type, c.issued = date(r.issued);

LOAD CSV WITH HEADERS FROM 'file:///Bank.csv' AS r
MERGE (:Bank {id: r.id});

// ---------- Relationships ----------
LOAD CSV WITH HEADERS FROM 'file:///LIVES_IN.csv' AS r
MATCH (c:Client {id: r.source}), (d:District {id: r.target})
MERGE (c)-[:LIVES_IN]->(d);

LOAD CSV WITH HEADERS FROM 'file:///BRANCH_IN.csv' AS r
MATCH (a:Account {id: r.source}), (d:District {id: r.target})
MERGE (a)-[:BRANCH_IN]->(d);

LOAD CSV WITH HEADERS FROM 'file:///HOLDS.csv' AS r
MATCH (c:Client {id: r.source}), (a:Account {id: r.target})
MERGE (c)-[:HOLDS {role: r.role}]->(a);

LOAD CSV WITH HEADERS FROM 'file:///HAS_LOAN.csv' AS r
MATCH (a:Account {id: r.source}), (l:Loan {id: r.target})
MERGE (a)-[:HAS_LOAN]->(l);

LOAD CSV WITH HEADERS FROM 'file:///HAS_CARD.csv' AS r
MATCH (c:Client {id: r.source}), (k:Card {id: r.target})
MERGE (c)-[:HAS_CARD]->(k);

LOAD CSV WITH HEADERS FROM 'file:///PAYS.csv' AS r
MATCH (a:Account {id: r.source}), (b:Bank {id: r.target})
MERGE (a)-[:PAYS {amount: toFloat(r.amount), purposes: split(r.purposes, '|')}]->(b);
