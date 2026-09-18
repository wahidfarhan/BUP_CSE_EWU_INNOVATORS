import math
from typing import List, Dict, Any, Optional
from app.models import DirectiveInterpretation, BatteryInput

ALLOWED_DIRECTIVES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op"
}

def check_directive_alignment(raw_type: str, text: str) -> bool:
    """Returns False if raw_type has zero semantic relevance to text, indicating misassigned note."""
    lower = text.lower()
    if raw_type == "solar_reduction":
        return any(w in lower for w in ["solar", "photovoltaic", "pv", "generation", "sun", "panel", "array"])
    if raw_type == "no_charge_window":
        return any(w in lower for w in ["charge", "charging", "replenish", "put energy", "store energy", "inflow", "fill", "put any energy"])
    if raw_type == "no_discharge_window":
        return any(w in lower for w in ["discharge", "discharging", "outflow", "drain", "draw from", "supply energy", "provide energy", "feed power"])
    if raw_type == "max_grid_window":
        return any(w in lower for w in ["grid", "import", "feeder", "transformer", "substation", "utility", "intake"])
    if raw_type == "minimum_battery_reserve":
        return any(w in lower for w in ["reserve", "stored", "at least", "minimum", "buffer", "maintain", "hold", "soc"])
    if raw_type == "no_op":
        has_operational = any(w in lower for w in ["solar", "photovoltaic", "battery", "charge", "discharge", "grid", "reserve", "feeder", "transformer"])
        return not has_operational
    return True

def sanitize_hours(raw_hours: Any) -> List[int]:
    """Ensures hours are unique integers in range 0..23, sorted ascending."""
    if not isinstance(raw_hours, list):
        return []
    valid_hours = set()
    for h in raw_hours:
        try:
            h_int = int(h)
            if 0 <= h_int <= 23:
                valid_hours.add(h_int)
        except (ValueError, TypeError):
            continue
    return sorted(list(valid_hours))

def validate_and_guardrail_directives(
    raw_directives: List[Dict[str, Any]],
    num_notes: int,
    battery: BatteryInput,
    operator_notes: Optional[List[str]] = None
) -> List[DirectiveInterpretation]:
    """
    Validates and normalizes directive interpretations according to Section 08 Guardrails.
    Returns a clean, strictly compliant list of DirectiveInterpretation objects.
    """
    from app.interpreter import deterministic_semantic_parser

    cleaned: List[DirectiveInterpretation] = []
    
    # Map by note_index if available
    dir_by_index: Dict[int, Dict[str, Any]] = {}
    for item in raw_directives:
        if isinstance(item, dict):
            idx = item.get("note_index")
            if isinstance(idx, int) and 0 <= idx < num_notes:
                dir_by_index[idx] = item

    for idx in range(num_notes):
        item = dir_by_index.get(idx)
        if not item and idx < len(raw_directives) and isinstance(raw_directives[idx], dict):
            item = raw_directives[idx]

        # Verify semantic alignment with the actual note text if available
        if operator_notes and idx < len(operator_notes):
            note_text = operator_notes[idx]
            current_type = str(item.get("directive_type", "")).strip().lower() if item else ""
            if not item or not check_directive_alignment(current_type, note_text):
                # Hallucination or note misalignment detected; re-parse directly from note text
                fallback_parsed = deterministic_semantic_parser([note_text], battery)[0]
                fallback_parsed["note_index"] = idx
                item = fallback_parsed
            else:
                # Check for uncaptured compound constraints in the note text
                lower_note = note_text.lower()
                adj = item.get("structured_adjustment") or {}
                if "stored in the battery" in lower_note or "keep at least" in lower_note or "reserve" in lower_note:
                    if "minimum_energy_kwh" not in adj and current_type != "minimum_battery_reserve":
                        sec_parsed = deterministic_semantic_parser([note_text], battery)[0]
                        sec_adj = sec_parsed.get("structured_adjustment") or {}
                        if "minimum_energy_kwh" in sec_adj:
                            adj["minimum_energy_kwh"] = sec_adj["minimum_energy_kwh"]
                            item["structured_adjustment"] = adj
                if any(w in lower_note for w in ["grid import", "grid imports", "max grid", "transformer limit"]):
                    if "max_grid_kwh" not in adj and current_type != "max_grid_window":
                        sec_parsed = deterministic_semantic_parser([note_text], battery)[0]
                        sec_adj = sec_parsed.get("structured_adjustment") or {}
                        if "max_grid_kwh" in sec_adj:
                            adj["max_grid_kwh"] = sec_adj["max_grid_kwh"]
                            adj["max_grid_hours"] = sec_adj.get("hours") or sec_adj.get("max_grid_hours")
                            item["structured_adjustment"] = adj
        
        if not item:
            cleaned.append(DirectiveInterpretation(
                note_index=idx,
                applies=False,
                directive_type="no_op",
                structured_adjustment=None,
                explanation="No valid directive extracted; defaulted to no_op."
            ))
            continue

        raw_type = str(item.get("directive_type", "no_op")).strip().lower()
        if raw_type not in ALLOWED_DIRECTIVES:
            raw_type = "no_op"
        
        raw_adj = item.get("structured_adjustment")
        raw_exp = str(item.get("explanation", "")).strip() or "Standard interpretation."

        if raw_type == "no_op":
            cleaned.append(DirectiveInterpretation(
                note_index=idx,
                applies=False,
                directive_type="no_op",
                structured_adjustment=None,
                explanation=raw_exp
            ))
            continue

        # Non-no_op directives must have applies = True and a valid structured_adjustment dictionary
        if not isinstance(raw_adj, dict):
            # Missing adjustment dictionary -> safe fallback to no_op
            cleaned.append(DirectiveInterpretation(
                note_index=idx,
                applies=False,
                directive_type="no_op",
                structured_adjustment=None,
                explanation="Missing adjustment structure; safely treated as no_op."
            ))
            continue

        hours = sanitize_hours(raw_adj.get("hours"))
        if not hours and raw_type != "minimum_battery_reserve":
            # Empty hours window means directive cannot apply meaningfully -> fallback to no_op
            cleaned.append(DirectiveInterpretation(
                note_index=idx,
                applies=False,
                directive_type="no_op",
                structured_adjustment=None,
                explanation="No valid operating hours identified; treated as no_op."
            ))
            continue

        adj: Dict[str, Any] = {}
        if hours and (raw_type != "minimum_battery_reserve" or len(hours) < 24):
            adj["hours"] = hours

        if raw_type == "solar_reduction":
            try:
                factor = float(raw_adj.get("factor", 1.0))
                if math.isnan(factor) or math.isinf(factor):
                    factor = 1.0
                factor = max(0.0, min(1.0, factor))
            except (ValueError, TypeError):
                factor = 1.0
            adj["factor"] = round(factor, 4)

        elif raw_type == "minimum_battery_reserve":
            try:
                min_kwh = float(raw_adj.get("minimum_energy_kwh", battery.minimum_energy_kwh))
                if math.isnan(min_kwh) or math.isinf(min_kwh):
                    min_kwh = battery.minimum_energy_kwh
                min_kwh = max(0.0, min(battery.capacity_kwh, min_kwh))
            except (ValueError, TypeError):
                min_kwh = battery.minimum_energy_kwh
            adj["minimum_energy_kwh"] = round(min_kwh, 2)

        elif raw_type == "max_grid_window":
            try:
                max_grid = float(raw_adj.get("max_grid_kwh", 1e6))
                if math.isnan(max_grid) or math.isinf(max_grid) or max_grid < 0:
                    max_grid = 0.0
            except (ValueError, TypeError):
                max_grid = 0.0
            adj["max_grid_kwh"] = round(max_grid, 2)

        elif raw_type in ("no_charge_window", "no_discharge_window"):
            pass  # Only "hours" is required

        # Preserve validated secondary constraints for the optimizer if present
        if "no_charge_hours" in raw_adj:
            nc_hours = sanitize_hours(raw_adj.get("no_charge_hours"))
            if nc_hours:
                adj["no_charge_hours"] = nc_hours
        if "no_discharge_hours" in raw_adj:
            nd_hours = sanitize_hours(raw_adj.get("no_discharge_hours"))
            if nd_hours:
                adj["no_discharge_hours"] = nd_hours
        if "max_grid_kwh" in raw_adj and raw_type != "max_grid_window":
            try:
                mg_val = float(raw_adj["max_grid_kwh"])
                if not (math.isnan(mg_val) or math.isinf(mg_val) or mg_val < 0):
                    adj["max_grid_kwh"] = round(mg_val, 2)
                    if "max_grid_hours" in raw_adj:
                        adj["max_grid_hours"] = sanitize_hours(raw_adj["max_grid_hours"])
            except (ValueError, TypeError):
                pass

        cleaned.append(DirectiveInterpretation(
            note_index=idx,
            applies=True,
            directive_type=raw_type,
            structured_adjustment=adj,
            explanation=raw_exp
        ))

    return cleaned
