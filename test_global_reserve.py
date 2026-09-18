import json
from app.models import OptimizeEnergyRequest
from app.interpreter import interpret_operator_notes
from app.guardrails import validate_and_guardrail_directives
from app.optimizer import solve_energy_schedule

def test_global_reserve():
    with open("BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json", "r") as f:
        data = json.load(f)

    base_case = data["cases"][0]["input"]
    notes = [
        "Reduce solar generation by 50% between 10 AM and noon.",
        "Keep at least 60 kWh stored in the battery throughout the day.",
        "The cafeteria is serving biryani today."
    ]
    base_case["operator_notes"] = notes
    req = OptimizeEnergyRequest(**base_case)

    raw = interpret_operator_notes(req.operator_notes, req.battery)
    cleaned = validate_and_guardrail_directives(raw, len(req.operator_notes), req.battery)

    # Note 0
    assert cleaned[0].directive_type == "solar_reduction"
    assert cleaned[0].applies is True
    assert cleaned[0].structured_adjustment["hours"] == [10, 11]
    assert cleaned[0].structured_adjustment["factor"] == 0.5

    # Note 1
    assert cleaned[1].directive_type == "minimum_battery_reserve"
    assert cleaned[1].applies is True
    assert "hours" not in cleaned[1].structured_adjustment, "Global reserve must NOT have hours field"
    assert cleaned[1].structured_adjustment["minimum_energy_kwh"] == 60.0

    # Note 2
    assert cleaned[2].directive_type == "no_op"
    assert cleaned[2].applies is False
    assert cleaned[2].structured_adjustment is None

    # Optimizer solve
    hourly_plan, grid, cost, peak, summary = solve_energy_schedule(req.hours, req.battery, cleaned)
    for h in hourly_plan:
        assert h.battery_energy_after_kwh >= 60.0 - 1e-4, f"Hour {h.hour} fell below 60 kWh: {h.battery_energy_after_kwh}"

    print("[PASSED] Global minimum battery reserve test passed! Battery never dropped below 60 kWh.")

if __name__ == "__main__":
    test_global_reserve()
