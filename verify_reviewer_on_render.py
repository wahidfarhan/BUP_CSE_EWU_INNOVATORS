import requests
import json
import time

url = "https://bup-gridwise.onrender.com/optimize-energy"

with open("BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json", "r") as f:
    sample_data = json.load(f)

payload = sample_data["cases"][0]["input"]
payload["scenario_id"] = "REVIEWER-GLOBAL-RESERVE-TEST"
payload["operator_notes"] = [
    "Reduce solar generation by 50% between 10 AM and noon.",
    "Keep at least 60 kWh stored in the battery throughout the day.",
    "The cafeteria is serving biryani today."
]

print("Sending request to Render...")
for attempt in range(1, 10):
    try:
        t0 = time.time()
        resp = requests.post(url, json=payload, timeout=15.0)
        dt = time.time() - t0
        print(f"Attempt {attempt}: Status {resp.status_code} ({dt:.2f}s)")
        if resp.status_code == 200:
            res_json = resp.json()
            directives = res_json.get("directive_interpretation", [])
            hourly = res_json.get("hourly_plan", [])
            
            print("\nDIRECTIVE INTERPRETATION:")
            print(json.dumps(directives, indent=2))
            
            d1 = directives[1]
            if d1.get("directive_type") == "minimum_battery_reserve" and d1.get("applies") is True:
                min_kwh = d1.get("structured_adjustment", {}).get("minimum_energy_kwh")
                print(f"\n-> Directive #1 interpretation: {d1.get('directive_type')}, minimum_energy_kwh={min_kwh}")
                
                # Check battery minimum across all hours
                min_bat = min(h["battery_energy_after_kwh"] for h in hourly)
                print(f"-> Lowest battery level across 24h: {min_bat} kWh")
                
                hours_17_to_22 = [h for h in hourly if h["hour"] in [17, 18, 19, 20, 21, 22]]
                print("\nHours 17-22 Battery Energy:")
                for h in hours_17_to_22:
                    print(f"  Hour {h['hour']:02d}: battery={h['battery_energy_after_kwh']:.1f} kWh (action={h['battery_action']})")
                
                if min_bat >= 60.0:
                    print("\n*** ALL CHECKS PASSED PERFECTLY! Battery never fell below 60 kWh! ***")
                    break
                else:
                    print(f"Battery fell to {min_bat}, waiting for new deployment...")
            else:
                print(f"Old code still running (Note 1 returned {d1.get('directive_type')}), waiting for Render build...")
    except Exception as e:
        print(f"Attempt {attempt} error: {e}")
    time.sleep(15)
