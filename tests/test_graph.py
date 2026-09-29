import pytest

from kg import queries
from kg.build_graph import build_graph, summary


@pytest.fixture(scope="module")
def G():
    return build_graph()


def test_graph_has_every_row_from_the_dataset(G):
    nodes, edges = summary(G)
    assert nodes["Client"] == 5369
    assert nodes["Account"] == 4500
    assert nodes["Loan"] == 682
    assert edges["HOLDS"] == 5369  # one per account holder
    assert edges["HAS_LOAN"] == 682  # every loan belongs to an account


def test_every_loan_hangs_off_exactly_one_account(G):
    for n, d in G.nodes(data=True):
        if d["type"] == "Loan":
            assert len(queries.in_nbrs(G, n, "HAS_LOAN")) == 1


def test_customer_360_finds_joint_account_holder(G):
    view = queries.customer_360(G, 2)
    assert view["region"] == "Prague"
    assert view["accounts"][0]["co_holders"] == [3]
    assert view["accounts"][0]["loans"][0]["status"] == "finished_ok"


def test_customer_360_unknown_client(G):
    with pytest.raises(KeyError):
        queries.customer_360(G, 999999)


def test_risk_tables_cover_all_loans(G):
    assert queries.risk_by_region(G)["loans"].sum() == 682
    by_holders = queries.risk_by_account_holders(G)
    assert by_holders["loans"].sum() == 682
    assert by_holders.loc["joint", "defaults"] == 0


def test_no_leads_for_defaulters(G):
    leads = queries.cross_sell_leads(G)
    assert not leads.empty
    for client_id in leads["client_id"].unique():
        assert not queries.is_defaulter(G, f"client:{client_id}")


def test_explain_connection(G):
    assert queries.explain_connection(G, "client:2", "client:3") == [
        "client:2 -[HOLDS]-> account:2",
        "account:2 <-[HOLDS]- client:3",
    ]
