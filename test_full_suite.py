import requests
import json
import time

BASE = "https://bup-gridwise.onrender.com"

def run_suite():
    print("=" * 80)
    print("STARTING COMPREHENSIVE LIVE TEST SUITE ON RENDER DEPLOYMENT")
    print(f"Target: {BASE}")
    print("=" * 80)

    # 1. GET /
    t0 = time.time()
    r_root = requests.get(f"{BASE}/", timeout=10)
    lat_root = (time.time() - t0) * 1000
    print(f"1. GET /                   -> Status {r_root.status_code} ({lat_root:.1f}ms) | Content: {r_root.text[:45]}...")
    assert r_root.status_code == 200, f"Root failed: {r_root.status_code}"

    # 2. GET /health
    t0 = time.time()
    r_health = requests.get(f"{BASE}/health", timeout=10)
    lat_health = (time.time() - t0) * 1000
    print(f"2. GET /health             -> Status {r_health.status_code} ({lat_health:.1f}ms) | Body: {r_health.json()}")
    assert r_health.status_code == 200 and r_health.json() == {"status": "ok"}

    # 3. GET /docs
    t0 = time.time()
    r_docs = requests.get(f"{BASE}/docs", timeout=10)
    lat_docs = (time.time() - t0) * 1000
    print(f"3. GET /docs (Swagger UI)  -> Status {r_docs.status_code} ({lat_docs:.1f}ms)")
    assert r_docs.status_code == 200

    # 4. POST /optimize-energy (400 Bad Request validation)
    t0 = time.time()
    r_bad = requests.post(f"{BASE}/optimize-energy", json={"invalid": "payload"}, timeout=10)
    lat_bad = (time.time() - t0) * 1000
    print(f"4. POST /optimize-energy   -> Status {r_bad.status_code} ({lat_bad:.1f}ms) | Bad Request correctly caught")
    assert r_bad.status_code == 400

    # 5. POST /optimize-energy (All 10 Public Sample Cases)
    with open("BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json", "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    print("-" * 80)
    print("5. EVALUATING ALL 10 PRELI SAMPLE CASES ON LIVE SERVER:")
    latencies = []
    all_passed = True

    for idx, case in enumerate(sample_data["cases"]):
        cid = case["id"]
        label = case["label"]
        inp = case["input"]
        exp = case.get("expected_output", {})

        t1 = time.time()
        resp = requests.post(f"{BASE}/optimize-energy", json=inp, timeout=20)
        lat = (time.time() - t1) * 1000
        latencies.append(lat)

        if resp.status_code != 200:
            print(f"   [FAIL] {cid}: HTTP {resp.status_code}")
            all_passed = False
            continue

        body = resp.json()
        cost = body.get("total_cost_bdt", 0)
        exp_cost = exp.get("total_cost_bdt")
        cost_match = abs(cost - exp_cost) < 0.5 if exp_cost is not None else True

        plan = body.get("hourly_plan", [])
        plan_ok = len(plan) == 24

        final_bat = plan[-1]["battery_energy_after_kwh"] if plan_ok else 0
        init_bat = inp["battery"]["initial_energy_kwh"]
        neutral = abs(final_bat - init_bat) < 0.05

        status = "PASS" if (cost_match and plan_ok and neutral) else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"   [{status}] {cid:9s} ({label:34s}) | Latency: {lat:5.1f}ms | Cost: {cost:8.2f} BDT (Ref: {exp_cost})")

    # 6. Novel AI / Unseen Operator Note Test
    print("-" * 80)
    print("6. EVALUATING DYNAMIC / NOVEL OPERATOR NOTES:")
    custom_inp = json.loads(json.dumps(sample_data["cases"][0]["input"]))
    custom_inp["scenario_id"] = "AI-TEST-CUSTOM"
    custom_inp["operator_notes"] = [
        "Solar generation degraded by 20% all day due to thick fog",
        "Keep battery reserve at 30 kWh between 18:00 and 22:00 for campus event",
        "Campus will hold a cultural evening program today"
    ]
    t2 = time.time()
    r_ai = requests.post(f"{BASE}/optimize-energy", json=custom_inp, timeout=20)
    ai_lat = (time.time() - t2) * 1000
    print(f"   Custom Request -> HTTP {r_ai.status_code} | Latency: {ai_lat:.1f}ms")
    assert r_ai.status_code == 200, f"Custom note test failed: {r_ai.status_code}"

    res = r_ai.json()
    for d in res.get("directive_interpretation", []):
        print(f"   - Note #{d['note_index']}: Applies={d['applies']}, Type={d['directive_type']}, Adj={d.get('structured_adjustment')}")
    print(f"   - Optimized Schedule Cost: {res['total_cost_bdt']:.2f} BDT")

    print("=" * 80)
    p95 = sorted(latencies)[int(0.95 * len(latencies))]
    avg_lat = sum(latencies) / len(latencies)
    print(f"OVERALL EVALUATION RESULT : {'100% PERFECT PASS' if all_passed else 'SOME FAILED'}")
    print(f"Average Request Latency   : {avg_lat:.1f}ms")
    print(f"P95 Latency               : {p95:.1f}ms (Competition Rubric Limit: 5000.0ms)")
    print("=" * 80)

if __name__ == "__main__":
    run_suite()
