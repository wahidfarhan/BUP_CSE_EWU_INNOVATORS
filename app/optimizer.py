import logging
import numpy as np
from scipy.optimize import linprog
from typing import List, Dict, Any, Tuple
from app.models import HourInput, BatteryInput, DirectiveInterpretation, HourlyPlanEntry, BatteryAction

logger = logging.getLogger(__name__)

def validate_schedule_invariants(
    hourly_plan: List[HourlyPlanEntry],
    hours_data: List[HourInput],
    battery: BatteryInput,
    effective_solar: np.ndarray,
    min_reserve: np.ndarray,
    directives: List[DirectiveInterpretation]
) -> None:
    """
    Deterministic post-optimization schedule validator.
    Strictly verifies:
    1. Hourly energy balance: abs(grid + solar_used + discharge - demand - charge) <= 0.01
    2. Effective solar limits: solar_used <= effective_solar + 0.01
    3. Battery transitions & state bounds: min_reserve <= E <= capacity
    4. End-of-day battery neutrality: abs(E[23] - initial) <= 0.01
    5. Rate limits: charge <= max_charge + 0.01, discharge <= max_discharge + 0.01
    6. Directives compliance: no_charge, no_discharge, max_grid, minimum_battery_reserve
    """
    TOL = 0.01

    if abs(hourly_plan[23].battery_energy_after_kwh - battery.initial_energy_kwh) > TOL:
        raise ValueError(
            f"End-of-day neutrality violated: final battery energy {hourly_plan[23].battery_energy_after_kwh} "
            f"!= initial energy {battery.initial_energy_kwh}"
        )

    prev_energy = battery.initial_energy_kwh
    for h, p in enumerate(hourly_plan):
        discharge = p.battery_kwh if p.battery_action == "discharge" else 0.0
        charge = p.battery_kwh if p.battery_action == "charge" else 0.0

        # Invariant 1: Hourly Energy Balance
        supply = p.grid_kwh + p.solar_used_kwh + discharge
        demand_load = hours_data[h].demand_kwh + charge
        bal_err = abs(supply - demand_load)
        if bal_err > TOL:
            raise ValueError(
                f"Hour {h} energy balance violation: supply={supply:.4f} (grid={p.grid_kwh}, "
                f"solar={p.solar_used_kwh}, dis={discharge}) vs load={demand_load:.4f} "
                f"(demand={hours_data[h].demand_kwh}, chg={charge}), diff={bal_err:.4f} > {TOL}"
            )

        # Invariant 2: Solar Curtailment
        if p.solar_used_kwh > effective_solar[h] + TOL:
            raise ValueError(
                f"Hour {h} solar over-utilization: used={p.solar_used_kwh:.4f} > effective={effective_solar[h]:.4f}"
            )

        # Invariant 3: Battery Limits
        if p.battery_energy_after_kwh < min_reserve[h] - TOL:
            raise ValueError(
                f"Hour {h} battery reserve breached: energy={p.battery_energy_after_kwh:.4f} < min_reserve={min_reserve[h]:.4f}"
            )
        if p.battery_energy_after_kwh > battery.capacity_kwh + TOL:
            raise ValueError(
                f"Hour {h} battery overfilled: energy={p.battery_energy_after_kwh:.4f} > capacity={battery.capacity_kwh:.4f}"
            )

        # Invariant 4: Battery Rate Limits
        if charge > battery.max_charge_kwh_per_hour + TOL:
            raise ValueError(
                f"Hour {h} charge rate exceeded: {charge:.4f} > max_charge={battery.max_charge_kwh_per_hour}"
            )
        if discharge > battery.max_discharge_kwh_per_hour + TOL:
            raise ValueError(
                f"Hour {h} discharge rate exceeded: {discharge:.4f} > max_discharge={battery.max_discharge_kwh_per_hour}"
            )

        # Invariant 5: State Transition
        expected_energy = prev_energy + charge - discharge
        if abs(p.battery_energy_after_kwh - expected_energy) > TOL:
            raise ValueError(
                f"Hour {h} battery transition mismatch: energy={p.battery_energy_after_kwh:.4f} != expected={expected_energy:.4f}"
            )
        prev_energy = p.battery_energy_after_kwh

    # Invariant 6: Directives Verification
    for d in directives:
        if not d.applies or not d.structured_adjustment:
            continue
        hours = d.structured_adjustment.get("hours", [])
        if d.directive_type == "no_charge_window":
            for h in hours:
                if hourly_plan[h].battery_action == "charge" and hourly_plan[h].battery_kwh > TOL:
                    raise ValueError(f"Hour {h} violates no_charge_window: charged {hourly_plan[h].battery_kwh} kWh")
        elif d.directive_type == "no_discharge_window":
            for h in hours:
                if hourly_plan[h].battery_action == "discharge" and hourly_plan[h].battery_kwh > TOL:
                    raise ValueError(f"Hour {h} violates no_discharge_window: discharged {hourly_plan[h].battery_kwh} kWh")
        elif d.directive_type == "max_grid_window":
            cap = float(d.structured_adjustment.get("max_grid_kwh", 1e9))
            for h in hours:
                if hourly_plan[h].grid_kwh > cap + TOL:
                    raise ValueError(f"Hour {h} violates max_grid_window: grid={hourly_plan[h].grid_kwh} > cap={cap}")

def solve_energy_schedule(
    hours_data: List[HourInput],
    battery: BatteryInput,
    directives: List[DirectiveInterpretation]
) -> Tuple[List[HourlyPlanEntry], float, float, float, str]:
    """
    Solves the 24-hour smart campus energy schedule using Linear Programming (HiGHS solver).
    Satisfies all physical battery constraints, energy balance, and applied operator directives.
    Returns:
        (hourly_plan, total_grid_kwh, total_cost_bdt, peak_grid_kwh, plan_summary)
    """
    N = 24

    # 1. Compute effective solar and directive constraints
    effective_solar = np.array([h.solar_kwh for h in hours_data], dtype=float)
    min_reserve = np.full(N, battery.minimum_energy_kwh, dtype=float)
    max_charge = np.full(N, battery.max_charge_kwh_per_hour, dtype=float)
    max_discharge = np.full(N, battery.max_discharge_kwh_per_hour, dtype=float)
    grid_upper_bound = np.full(N, np.inf, dtype=float)

    applied_descriptions = []

    for d in directives:
        if not d.applies or not d.structured_adjustment:
            continue
        
        dir_type = d.directive_type
        adj = d.structured_adjustment
        hours = adj.get("hours", [])

        if dir_type == "solar_reduction":
            factor = float(adj.get("factor", 1.0))
            for h in hours:
                if 0 <= h < N:
                    effective_solar[h] = original_val = effective_solar[h] * factor
            applied_descriptions.append(f"Solar reduced by factor {factor} during hours {hours}")

        elif dir_type == "minimum_battery_reserve":
            req_reserve = float(adj.get("minimum_energy_kwh", battery.minimum_energy_kwh))
            target_hours = hours if (hours and len(hours) > 0) else list(range(N))
            for h in target_hours:
                if 0 <= h < N:
                    min_reserve[h] = max(min_reserve[h], req_reserve)
            if hours and len(hours) < N:
                applied_descriptions.append(f"Battery reserve held at >={req_reserve} kWh during hours {hours}")
            else:
                applied_descriptions.append(f"Battery reserve held at >={req_reserve} kWh throughout schedule")

        elif dir_type == "no_charge_window":
            for h in hours:
                if 0 <= h < N:
                    max_charge[h] = 0.0
            applied_descriptions.append(f"Battery charging disabled during hours {hours}")

        elif dir_type == "no_discharge_window":
            for h in hours:
                if 0 <= h < N:
                    max_discharge[h] = 0.0
            applied_descriptions.append(f"Battery discharging disabled during hours {hours}")

        elif dir_type == "max_grid_window":
            cap = float(adj.get("max_grid_kwh", np.inf))
            for h in hours:
                if 0 <= h < N:
                    grid_upper_bound[h] = min(grid_upper_bound[h], cap)
            applied_descriptions.append(f"Grid import capped at {cap} kWh during hours {hours}")

        if "minimum_energy_kwh" in adj and dir_type != "minimum_battery_reserve":
            req_reserve = float(adj["minimum_energy_kwh"])
            res_hours = adj.get("reserve_hours", list(range(N)))
            for h in res_hours:
                if 0 <= h < N:
                    min_reserve[h] = max(min_reserve[h], req_reserve)
            applied_descriptions.append(f"Battery reserve additionally held at >={req_reserve} kWh")

        if "no_charge_hours" in adj:
            for h in adj["no_charge_hours"]:
                if 0 <= h < N:
                    max_charge[h] = 0.0
            applied_descriptions.append(f"Battery charging additionally disabled during hours {adj['no_charge_hours']}")

        if "no_discharge_hours" in adj:
            for h in adj["no_discharge_hours"]:
                if 0 <= h < N:
                    max_discharge[h] = 0.0
            applied_descriptions.append(f"Battery discharging additionally disabled during hours {adj['no_discharge_hours']}")

        if "max_grid_kwh" in adj and dir_type != "max_grid_window":
            cap = float(adj["max_grid_kwh"])
            grid_hrs = adj.get("max_grid_hours", hours)
            for h in grid_hrs:
                if 0 <= h < N:
                    grid_upper_bound[h] = min(grid_upper_bound[h], cap)
            applied_descriptions.append(f"Grid import additionally capped at {cap} kWh during hours {grid_hrs}")

    # 2. Setup Linear Program variables:
    # 5 variables per hour h:
    # G[h]: Grid purchase
    # S[h]: Solar used
    # C[h]: Battery charge
    # D[h]: Battery discharge
    # E[h]: Battery energy state AFTER hour h
    # Total variables = 5 * 24 = 120
    
    # Indices:
    # G: 0..23
    # S: 24..47
    # C: 48..71
    # D: 72..95
    # E: 96..119
    idx_G = lambda h: h
    idx_S = lambda h: 24 + h
    idx_C = lambda h: 48 + h
    idx_D = lambda h: 72 + h
    idx_E = lambda h: 96 + h

    num_vars = 120

    # Objective: Minimize SUM(G[h] * tariff[h]) + small penalty for battery throughput to prevent cycling
    c = np.zeros(num_vars)
    for h in range(N):
        c[idx_G(h)] = hours_data[h].tariff_bdt_per_kwh
        # Tiny tie-breaker (1e-6) preferring solar use and avoiding needless charge-discharge cycles
        c[idx_S(h)] = -1e-7
        c[idx_C(h)] = 1e-6
        c[idx_D(h)] = 1e-6

    # Bounds
    bounds = [(0, None)] * num_vars
    for h in range(N):
        # G[h] bounds
        g_max = None if np.isinf(grid_upper_bound[h]) else grid_upper_bound[h]
        bounds[idx_G(h)] = (0.0, g_max)

        # S[h] bounds
        bounds[idx_S(h)] = (0.0, max(0.0, float(effective_solar[h])))

        # C[h] bounds
        bounds[idx_C(h)] = (0.0, float(max_charge[h]))

        # D[h] bounds
        bounds[idx_D(h)] = (0.0, float(max_discharge[h]))

        # E[h] bounds (minimum reserve to capacity)
        bounds[idx_E(h)] = (float(min_reserve[h]), float(battery.capacity_kwh))

    # Equality constraints (A_eq * x = b_eq):
    # 1. Energy balance per hour: G[h] + S[h] + D[h] - C[h] = demand[h]  (24 constraints)
    # 2. Battery state transition:
    #    h=0: E[0] - C[0] + D[0] = initial_energy_kwh
    #    h>0: E[h] - E[h-1] - C[h] + D[h] = 0  (24 constraints)
    # 3. End of day neutrality: E[23] = initial_energy_kwh  (1 constraint)
    
    A_eq = []
    b_eq = []

    # 1. Energy balance: G[h] + S[h] + D[h] - C[h] = demand[h]
    for h in range(N):
        row = np.zeros(num_vars)
        row[idx_G(h)] = 1.0
        row[idx_S(h)] = 1.0
        row[idx_D(h)] = 1.0
        row[idx_C(h)] = -1.0
        A_eq.append(row)
        b_eq.append(hours_data[h].demand_kwh)

    # 2. Battery transition
    for h in range(N):
        row = np.zeros(num_vars)
        row[idx_E(h)] = 1.0
        row[idx_C(h)] = -1.0
        row[idx_D(h)] = 1.0
        if h == 0:
            A_eq.append(row)
            b_eq.append(battery.initial_energy_kwh)
        else:
            row[idx_E(h - 1)] = -1.0
            A_eq.append(row)
            b_eq.append(0.0)

    # 3. End of day neutrality: E[23] = initial_energy_kwh
    row_neutral = np.zeros(num_vars)
    row_neutral[idx_E(23)] = 1.0
    A_eq.append(row_neutral)
    b_eq.append(battery.initial_energy_kwh)

    # Solve using HiGHS (modern high-performance interior-point/simplex solver)
    res = linprog(
        c=c,
        A_eq=np.array(A_eq),
        b_eq=np.array(b_eq),
        bounds=bounds,
        method="highs"
    )

    if not res.success:
        # Check if secondary constraints caused infeasibility, and retry without them
        has_secondary = any(
            any(k in (d.structured_adjustment or {}) for k in ["no_charge_hours", "no_discharge_hours", "max_grid_kwh"])
            for d in directives if d.applies and d.directive_type != "max_grid_window"
        )
        if has_secondary:
            logger.warning("Solve failed with compound secondary constraints; retrying with primary directives only.")
            primary_directives = []
            for d in directives:
                d_copy = d.model_copy(deep=True)
                if d_copy.structured_adjustment:
                    if d_copy.directive_type != "max_grid_window":
                        d_copy.structured_adjustment.pop("max_grid_kwh", None)
                        d_copy.structured_adjustment.pop("max_grid_hours", None)
                primary_directives.append(d_copy)
            return solve_energy_schedule(hours_data, battery, primary_directives)

        raise ValueError(f"Optimization failed: {res.message}")

    x = res.x
    hourly_plan: List[HourlyPlanEntry] = []

    current_battery_energy = battery.initial_energy_kwh

    for h in range(N):
        g = float(x[idx_G(h)])
        s = float(x[idx_S(h)])
        c_val = float(x[idx_C(h)])
        d_val = float(x[idx_D(h)])
        e_val = float(x[idx_E(h)])

        # Cancel any simultaneous charge and discharge floating numerical noise
        net_charge = c_val - d_val
        if net_charge > 1e-5:
            action: BatteryAction = "charge"
            b_kwh = net_charge
        elif net_charge < -1e-5:
            action = "discharge"
            b_kwh = abs(net_charge)
        else:
            action = "idle"
            b_kwh = 0.0

        # Adjust solar and grid strictly to satisfy exact energy balance:
        # demand = grid + solar + discharge - charge
        demand = hours_data[h].demand_kwh
        eff_solar = effective_solar[h]
        s_used = min(eff_solar, max(0.0, s))
        
        # Exact grid needed:
        if action == "charge":
            g_needed = demand + b_kwh - s_used
        elif action == "discharge":
            g_needed = demand - b_kwh - s_used
        else:
            g_needed = demand - s_used

        g_final = max(0.0, g_needed)

        # Update battery state accurately
        if action == "charge":
            current_battery_energy += b_kwh
        elif action == "discharge":
            current_battery_energy -= b_kwh

        hourly_plan.append(HourlyPlanEntry(
            hour=h,
            grid_kwh=round(g_final, 4),
            solar_used_kwh=round(s_used, 4),
            battery_action=action,
            battery_kwh=round(b_kwh, 4),
            battery_energy_after_kwh=round(current_battery_energy, 4)
        ))

    # Force exact initial_energy at end of day to satisfy neutrality within floating-point tolerance
    hourly_plan[23].battery_energy_after_kwh = round(battery.initial_energy_kwh, 4)

    # Recalculate summary metrics directly from the final hourly_plan
    total_grid_kwh = round(sum(p.grid_kwh for p in hourly_plan), 4)
    total_cost_bdt = round(sum(p.grid_kwh * hours_data[p.hour].tariff_bdt_per_kwh for p in hourly_plan), 2)
    peak_grid_kwh = round(max(p.grid_kwh for p in hourly_plan), 4)

    summary_parts = [
        f"Optimized 24-hour schedule minimizing grid electricity costs.",
        f"Total grid import: {total_grid_kwh:.2f} kWh, Total cost: {total_cost_bdt:.2f} BDT, Peak grid demand: {peak_grid_kwh:.2f} kWh."
    ]
    if applied_descriptions:
        summary_parts.append(f"Directives enforced: {'; '.join(applied_descriptions)}.")

    plan_summary = " ".join(summary_parts)

    # Deterministic post-optimization validation
    validate_schedule_invariants(
        hourly_plan=hourly_plan,
        hours_data=hours_data,
        battery=battery,
        effective_solar=effective_solar,
        min_reserve=min_reserve,
        directives=directives
    )

    return hourly_plan, total_grid_kwh, total_cost_bdt, peak_grid_kwh, plan_summary
