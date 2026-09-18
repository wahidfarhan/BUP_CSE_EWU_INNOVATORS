import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api():
    print("Testing GET /health...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health failed: {resp.status_code}"
    assert resp.json() == {"status": "ok"}, f"Health body mismatch: {resp.json()}"
    print("GET /health -> PASS (200 OK, {'status': 'ok'})")

    print("\nTesting POST /optimize-energy with SAMPLE-01...")
    with open('BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    case_01 = data['cases'][0]['input']
    
    resp = client.post("/optimize-energy", json=case_01)
    assert resp.status_code == 200, f"Optimize failed: {resp.status_code}, {resp.text}"
    result = resp.json()
    assert result["scenario_id"] == "SAMPLE-01"
    assert len(result["directive_interpretation"]) == 2
    assert len(result["hourly_plan"]) == 24
    assert result["total_cost_bdt"] == 38365.0
    print("POST /optimize-energy -> PASS (200 OK, perfectly matched schema and results)")

    print("\nTesting Malformed Request (400 Bad Request)...")
    bad_resp = client.post("/optimize-energy", json={"invalid": "data"})
    assert bad_resp.status_code == 400
    print("Malformed Request -> PASS (400 Bad Request)")

    print("\nALL API ENDPOINT INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_api()
