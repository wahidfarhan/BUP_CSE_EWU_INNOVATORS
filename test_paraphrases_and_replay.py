import requests
import json

BASE = "https://bup-gridwise.onrender.com"

def replay_and_verify(inp, res):
    """Independently verifies and replays the returned schedule from first principles."""
    hourly_plan = res["hourly_plan"]
    battery_in = inp["battery"]
    hours_in = inp["hours"]
    reported_cost = res["total_cost_bdt"]
    
    # 1. Schema check
    assert len(hourly_plan) == 24, "Hourly plan must have exactly 24 entries"
    
    # 2. Independent Energy Balance & Battery Replay
    curr_bat = battery_in["initial_energy_kwh"]
    calc_cost = 0.0
    calc_grid = 0.0
    
    for h in range(24):
        p = hourly_plan[h]
        d_in = hours_in[h]
        
        grid = p["grid_kwh"]
        solar_used = p["solar_used_kwh"]
        b_action = p["battery_action"]
        b_kwh = p["battery_kwh"]
        e_after = p["battery_energy_after_kwh"]
        
        # Action consistency
        ch = b_kwh if b_action == "charge" else 0.0
        dis = b_kwh if b_action == "discharge" else 0.0
        
        # Energy balance: Grid + SolarUsed + Discharge - Charge == Demand
        balance = (grid + solar_used + dis) - (d_in["demand_kwh"] + ch)
        assert abs(balance) < 0.01, f"Hour {h}: Energy balance violation: {balance}"
        
        # Battery state update
        curr_bat += (ch - dis)
        assert abs(curr_bat - e_after) < 0.01, f"Hour {h}: Battery state mismatch: {curr_bat} vs {e_after}"
        assert e_after <= battery_in["capacity_kwh"] + 0.01, f"Hour {h}: Battery capacity exceeded"
        assert e_after >= 0.0, f"Hour {h}: Negative battery energy"
        
        # Rate limits
        if ch > 0:
            assert ch <= battery_in["max_charge_kwh_per_hour"] + 0.01, f"Hour {h}: Max charge rate exceeded"
        if dis > 0:
            assert dis <= battery_in["max_discharge_kwh_per_hour"] + 0.01, f"Hour {h}: Max discharge rate exceeded"
            
        calc_cost += grid * d_in["tariff_bdt_per_kwh"]
        calc_grid += grid

    # 3. End-of-day neutrality
    assert abs(curr_bat - battery_in["initial_energy_kwh"]) < 0.01, f"Battery neutrality violated: final {curr_bat} != initial {battery_in['initial_energy_kwh']}"
    
    # 4. Total cost & grid check
    assert abs(calc_cost - reported_cost) < 0.5, f"Cost recalculation mismatch: calc {calc_cost} vs reported {reported_cost}"
    assert abs(calc_grid - res["total_grid_kwh"]) < 0.5, f"Total grid mismatch"
    
    return calc_cost

def run_tests():
    print("=" * 80)
    print("RUNNING ADVANCED PARAPHRASE & INDEPENDENT REPLAY VALIDATION ON RENDER")
    print("=" * 80)
    
    # Load base hours from SAMPLE-01
    with open("BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json") as f:
        sample_data = json.load(f)
    base_hours = sample_data["cases"][0]["input"]["hours"]
    
    # Test Case 1: The exact paraphrased notes from reviewer
    payload_1 = {
        "scenario_id": "REVIEWER-PARAPHRASE-CASE",
        "operator_notes": [
            "The photovoltaic system will undergo maintenance between 13:00 and 15:00, leaving approximately one quarter of forecast generation available.",
            "Keep 120 kWh stored in the battery throughout the 6-9 PM period.",
            "Battery charging must remain disabled from 14:00 through 16:00."
        ],
        "battery": {
            "capacity_kwh": 220.0,
            "initial_energy_kwh": 110.0,
            "minimum_energy_kwh": 40.0,
            "max_charge_kwh_per_hour": 50.0,
            "max_discharge_kwh_per_hour": 50.0
        },
        "hours": base_hours
    }
    
    print("\n[TEST 1] Testing Reviewer's Paraphrased Notes Against Render...")
    r1 = requests.post(f"{BASE}/optimize-energy", json=payload_1, timeout=20)
    print("Status:", r1.status_code)
    assert r1.status_code == 200, f"Failed: {r1.text}"
    res1 = r1.json()
    
    print("Extracted Directives:")
    for d in res1["directive_interpretation"]:
        print(f" - Note #{d['note_index']}: Type={d['directive_type']}, Applies={d['applies']}, Adj={d.get('structured_adjustment')}")
        print(f"   Explanation: {d.get('explanation')}")
        
    cost_1 = replay_and_verify(payload_1, res1)
    print(f"-> Independent Replay: 100% VALID! Recalculated Cost = {cost_1:.2f} BDT")
    
    # Verify exact extraction expected by reviewer:
    # 1. solar_reduction, hours [13, 14], factor 0.25
    d0 = res1["directive_interpretation"][0]
    assert d0["directive_type"] == "solar_reduction" and d0["applies"] is True
    assert d0["structured_adjustment"]["hours"] == [13, 14]
    assert abs(d0["structured_adjustment"]["factor"] - 0.25) < 0.01
    print("-> Note #0 Paraphrase Match: 100% EXACT ([13, 14], factor 0.25)")
    
    # 2. minimum_battery_reserve, hours [18, 19, 20], min 120
    d1 = res1["directive_interpretation"][1]
    assert d1["directive_type"] == "minimum_battery_reserve" and d1["applies"] is True
    assert d1["structured_adjustment"]["hours"] == [18, 19, 20]
    assert abs(d1["structured_adjustment"]["minimum_energy_kwh"] - 120.0) < 0.01
    print("-> Note #1 Paraphrase Match: 100% EXACT ([18, 19, 20], min 120 kWh)")
    
    # 3. no_charge_window, hours [14, 15]
    d2 = res1["directive_interpretation"][2]
    assert d2["directive_type"] == "no_charge_window" and d2["applies"] is True
    assert d2["structured_adjustment"]["hours"] == [14, 15]
    print("-> Note #2 Paraphrase Match: 100% EXACT ([14, 15], no_charge)")
    
    # Test Case 2: Only no_op notes
    payload_noop = {
        "scenario_id": "ALL-NO-OP-CASE",
        "operator_notes": [
            "Faculty meeting adjourned early at 15:30.",
            "Weather is slightly overcast but no rain is expected."
        ],
        "battery": {
            "capacity_kwh": 220.0,
            "initial_energy_kwh": 110.0,
            "minimum_energy_kwh": 40.0,
            "max_charge_kwh_per_hour": 50.0,
            "max_discharge_kwh_per_hour": 50.0
        },
        "hours": base_hours
    }
    print("\n[TEST 2] Testing Pure No-Op Notes...")
    r2 = requests.post(f"{BASE}/optimize-energy", json=payload_noop, timeout=20)
    assert r2.status_code == 200
    res2 = r2.json()
    for d in res2["directive_interpretation"]:
        assert d["directive_type"] == "no_op" and d["applies"] is False and d["structured_adjustment"] is None
    cost_2 = replay_and_verify(payload_noop, res2)
    print(f"-> All No-Op Notes: 100% Handled! Replayed Cost = {cost_2:.2f} BDT")
    
    print("\n" + "=" * 80)
    print("ALL ADVANCED PARAPHRASE AND REPLAY VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
