from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root():
    b = client.get("/").json()
    assert b["coverage"]["deals"] == 25 and b["coverage"]["completed_deals"] == 23
    assert abs(b["coverage"]["completed_usd_mn"] - 6035.0) < 1


def test_deals_filters():
    assert client.get("/deals").json()["count"] == 25
    assert client.get("/deals", params={"instrument": "Green loan"}).json()["count"] == 7
    assert client.get("/deals", params={"issuer_type": "Municipal"}).json()["count"] == 3
    assert client.get("/deals", params={"issuer": "larsen"}).json()["count"] == 2
    b = client.get("/deals", params={"since": "2026-01-01"}).json()
    assert all(d["date"] >= "2026-01-01" for d in b["deals"])
    assert client.get("/deals", params={"instrument": "Bogus"}).status_code == 422


def test_sort_by_size():
    b = client.get("/deals", params={"sort": "usd_mn", "status": "Signed"}).json()
    sizes = [d["amount"]["usd_mn"] for d in b["deals"]]
    assert sizes == sorted(sizes, reverse=True) and sizes[0] == 800.0


def test_deal_lookup():
    d = client.get("/deals/rec-2409").json()
    assert d["amount"]["usd_mn"] == 500 and d["pricing"] == "4.75% fixed"
    assert client.get("/deals/NOPE").status_code == 404


def test_summary_matches_workbook():
    b = client.get("/summary").json()
    assert b["completed_deals"] == 23
    inst = {r["key"]: r for r in b["by_instrument"]}
    assert round(inst["Green bond"]["usd_mn"]) == 3120
    assert round(inst["Sustainability-linked loan"]["usd_mn"]) == 1050
    assert abs(sum(r["share"] for r in b["by_issuer_type"]) - 1) < 1e-3
    assert b["largest_deal"]["deal_id"] == "SOV-2301"


def test_excluded_statuses_not_counted():
    b = client.get("/deals", params={"status": "Scheduled"}).json()
    assert b["deals"][0]["counted_in_totals"] is False


def test_issuers():
    b = client.get("/issuers").json()
    assert b["issuers"][0]["issuer"] == "Government of India"
    lt = next(i for i in b["issuers"] if i["issuer"] == "Larsen & Toubro")
    assert lt["deals"] == 2


def test_sovereign():
    a = client.get("/sovereign/auctions").json()
    assert a["count"] == 9 and a["outstanding_inr_bn_aug_2026"] == 877
    g = client.get("/sovereign/greenium").json()
    assert [o["greenium_bps"] for o in g["observations"]] == [6, 6, 4]
    assert len(g["weak_auctions"]) == 4


def test_sll_kpis():
    b = client.get("/sll/kpis").json()
    assert b["count"] == 3 and b["with_named_kpis"] == 2
    jk = next(d for d in b["deals"] if d["issuer"].startswith("JK Tyre"))
    assert jk["kpis_named"] is False


def test_every_get_endpoint_without_params():
    for path in ["/", "/health", "/deals", "/deals/REC-2409", "/summary", "/issuers",
                 "/sovereign/auctions", "/sovereign/greenium", "/sll/kpis", "/fx"]:
        assert client.get(path).status_code == 200, path
