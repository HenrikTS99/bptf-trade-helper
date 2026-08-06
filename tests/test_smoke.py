async def test_dashboard_renders(client):
    # sanity check
    res = await client.get("/")
    assert res.status_code == 200
    assert "Only Beaten" in res.text
