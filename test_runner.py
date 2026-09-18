import json
import time
import math
from typing import Dict, Any, List

from app.models import OptimizeEnergyRequest, BatteryInput, HourInput
from app.interpreter import interpret_operator_notes
from app.guardrails import validate_and_guardrail_directives
from app.optimizer import solve_energy_schedule

def run_all_tests():
    print("=" * 70)
    print("RUNNING GRIDWISE SYSTEM VALIDATION ON PUBLIC SAMPLE CASES")
    print("=" * 70)

    with open('BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    cases = data['cases']
    total_cases = len(cases)
    passed_cases = 0
    total_time = 0.0

    for c in cases:
        c_id = c['id']
        label = c['label']
        inp = c['input']
        expected_out = c.get('expected_output', {})
        expected_directives = expected_out.get('directive_interpretation', [])
        expected_cost = expected_out.get('total_cost_bdt')

        # Convert to Pydantic request
        req = OptimizeEnergyRequest(
            scenario_id=inp['scenario_id'],
            operator_notes=inp['operator_notes'],
            hours=[HourInput(**h) for h in inp['hours']],
            battery=BatteryInput(**inp['battery'])
        )

        t0 = time.time()
        
        # 1. Interpretation
        raw_dirs = interpret_operator_notes(req.operator_notes, req.battery)
        
        # 2. Guardrails
        guarded_dirs = validate_and_guardrail_directives(raw_dirs, len(req.operator_notes), req.battery)
        
        # 3. Optimization
        hourly_plan, total_grid, total_cost, peak_grid, summary = solve_energy_schedule(
            hours_data=req.hours,
            battery=req.battery,
            directives=guarded_dirs
        )
        
        elapsed = time.time() - t0
        total_time += elapsed

        # Check Directives
        dir_ok = True
        for i, exp_d in enumerate(expected_directives):
            actual_d = guarded_dirs[i]
            if actual_d.directive_type != exp_d['directive_type']:
                print(f"  [!] {c_id} Note {i}: Type mismatch: got {actual_d.directive_type}, expected {exp_d['directive_type']}")
                dir_ok = False
            if actual_d.applies != exp_d['applies']:
                print(f"  [!] {c_id} Note {i}: Applies mismatch: got {actual_d.applies}, expected {exp_d['applies']}")
                dir_ok = False
            
            exp_adj = exp_d.get('structured_adjustment')
            act_adj = actual_d.structured_adjustment
            if exp_adj is not None:
                if act_adj is None:
                    print(f"  [!] {c_id} Note {i}: Adjustment missing")
                    dir_ok = False
                else:
                    if act_adj.get('hours') != exp_adj.get('hours'):
                        print(f"  [!] {c_id} Note {i}: Hours mismatch: got {act_adj.get('hours')}, expected {exp_adj.get('hours')}")
                        dir_ok = False
                    for key in ['factor', 'minimum_energy_kwh', 'max_grid_kwh']:
                        if key in exp_adj:
                            if abs(act_adj.get(key, -999) - exp_adj[key]) > 0.05:
                                print(f"  [!] {c_id} Note {i}: Value mismatch for {key}: got {act_adj.get(key)}, expected {exp_adj[key]}")
                                dir_ok = False

        # Check Energy Constraints
        constraints_ok = True
        curr_bat = req.battery.initial_energy_kwh
        for h_idx, entry in enumerate(hourly_plan):
            h_input = req.hours[h_idx]
            # Energy balance: Grid + SolarUsed + Discharge = Demand + Charge
            discharge = entry.battery_kwh if entry.battery_action == "discharge" else 0.0
            charge = entry.battery_kwh if entry.battery_action == "charge" else 0.0
            
            balance_diff = abs((entry.grid_kwh + entry.solar_used_kwh + discharge) - (h_input.demand_kwh + charge))
            if balance_diff > 0.05:
                print(f"  [!] {c_id} Hour {h_idx}: Energy balance violated! Diff: {balance_diff}")
                constraints_ok = False
                break

            # Battery state update check
            if entry.battery_action == "charge":
                curr_bat += charge
            elif entry.battery_action == "discharge":
                curr_bat -= discharge
            
            if abs(curr_bat - entry.battery_energy_after_kwh) > 0.05:
                print(f"  [!] {c_id} Hour {h_idx}: Battery state transition violated!")
                constraints_ok = False
                break

        # End of day neutrality
        if abs(hourly_plan[-1].battery_energy_after_kwh - req.battery.initial_energy_kwh) > 0.05:
            print(f"  [!] {c_id}: Neutrality violated! Final: {hourly_plan[-1].battery_energy_after_kwh}, Initial: {req.battery.initial_energy_kwh}")
            constraints_ok = False

        # Cost optimality comparison
        cost_diff = total_cost - expected_cost if expected_cost is not None else 0.0
        
        status = "PASSED" if (dir_ok and constraints_ok and abs(cost_diff) <= 0.5) else "FAILED"
        if status == "PASSED":
            passed_cases += 1

        print(f"[{status}] {c_id} ({label}) - Time: {elapsed*1000:.1f}ms | Directives: {'OK' if dir_ok else 'FAIL'} | Constraints: {'OK' if constraints_ok else 'FAIL'} | Cost: {total_cost:.2f} BDT (Ref: {expected_cost})")

    print("=" * 70)
    print(f"RESULTS: {passed_cases}/{total_cases} CASES PASSED ({passed_cases/total_cases*100:.0f}%)")
    print(f"Average latency per request: {total_time/total_cases*1000:.1f}ms")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
