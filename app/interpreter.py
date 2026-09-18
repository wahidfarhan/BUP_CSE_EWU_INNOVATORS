import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import requests

from app.models import DirectiveInterpretation, BatteryInput

logger = logging.getLogger(__name__)

# System prompt for LLMs to interpret operator notes
SYSTEM_PROMPT = """You are an expert energy grid operator assistant for a smart campus energy management system.
Your job is to read natural-language operator notes and convert each note into a structured directive.

Allowed directive types:
1. "solar_reduction":
   - Required structured_adjustment: {"hours": [int, ...], "factor": float}
   - factor is the usable solar fraction remaining (between 0.0 and 1.0).
   - e.g., "80% reduction" means factor = 0.2. "drop to 25%" or "roughly one-fourth" means factor = 0.25. "half" means factor = 0.5.
2. "minimum_battery_reserve":
   - Required structured_adjustment: {"hours": [int, ...], "minimum_energy_kwh": float}
   - If specified as percentage of capacity (e.g. 50% of capacity), compute (percent/100) * capacity_kwh.
3. "no_charge_window":
   - Required structured_adjustment: {"hours": [int, ...]}
4. "no_discharge_window":
   - Required structured_adjustment: {"hours": [int, ...]}
5. "max_grid_window":
   - Required structured_adjustment: {"hours": [int, ...], "max_grid_kwh": float}
6. "no_op":
   - Used for notes that do NOT affect the current 24-hour energy schedule (e.g., cafeteria menus, sports events, book returns, room bookings, notices).
   - For "no_op": applies MUST be false, structured_adjustment MUST be null.

CRITICAL TIME RULES:
- Time intervals are whole hours, START-INCLUSIVE and END-EXCLUSIVE.
- "1 PM to 3 PM" or "13:00 to 15:00" -> hours [13, 14]
- "noon until 2 PM" -> hours [12, 13]
- "10 AM until noon" -> hours [10, 11]
- "6 PM until 9 PM" -> hours [18, 19, 20]
- "6 PM until 10 PM" -> hours [18, 19, 20, 21]
- "7 PM until 9 PM" -> hours [19, 20]
- "7 PM until 10 PM" -> hours [19, 20, 21]
- "2 AM until 5 AM" -> hours [2, 3, 4]
- "hours" MUST be unique integers in ascending order.

OUTPUT JSON FORMAT:
Return a JSON array containing exactly one object per note in the exact order of the notes:
[
  {
    "note_index": 0,
    "applies": true or false,
    "directive_type": "one_of_allowed_types",
    "structured_adjustment": { ... } or null,
    "explanation": "Brief explanation"
  }
]
"""

def parse_time_window(text: str) -> List[int]:
    """Extracts start-inclusive, end-exclusive hours from natural text expressions."""
    text_lower = text.lower()

    # Match patterns like "from noon until 2 pm", "from 10 am until noon", "between 11 am and 2 pm", "from 6 pm until 9 pm", "13:00 and 15:00", "1-3 pm"
    
    def convert_hour(val: str, meridiem: Optional[str] = None) -> int:
        val = val.strip().lower()
        if val == "noon":
            return 12
        if val in ("midnight", "0"):
            return 0
        h = int(val)
        if meridiem:
            meridiem = meridiem.strip().lower()
            if "pm" in meridiem and h < 12:
                h += 12
            elif "am" in meridiem and h == 12:
                h = 0
        return h

    # Check 24-hour formats e.g. "between 13:00 and 15:00", "from 14:00 through 16:00"
    m_24 = re.search(r'(?:from|between)\s+(\d{1,2}):00\s+(?:to|until|and|through|till|-|–)\s+(\d{1,2}):00', text_lower)
    if m_24:
        start_h = int(m_24.group(1))
        end_h = int(m_24.group(2))
        return list(range(start_h, end_h))

    # Check "1-3 PM", "6-9 PM", "1 to 3 PM", "6 through 9 PM"
    m_hyphen = re.search(r'(\d{1,2})\s*(?:-|–|to|through|till)\s*(\d{1,2})\s*(am|pm)', text_lower)
    if m_hyphen:
        h1 = int(m_hyphen.group(1))
        h2 = int(m_hyphen.group(2))
        mer = m_hyphen.group(3)
        # Handle cases like 11 AM - 2 PM vs 1-3 PM
        start_h = convert_hour(str(h1), mer)
        end_h = convert_hour(str(h2), mer)
        if start_h > end_h:
            # e.g. 11 to 2 pm -> 11 am to 2 pm
            start_h = h1
        return list(range(start_h, end_h))

    # Check "from X (am/pm/noon) (to/until/and/through) Y (am/pm/noon)"
    # or "between X (am/pm/noon) and Y (am/pm/noon)"
    pattern = r'(?:from|between)\s+(\d{1,2}|noon|midnight)\s*(am|pm)?\s*(?:to|until|and|through|till|-|–)\s*(\d{1,2}|noon|midnight)\s*(am|pm)?'
    m = re.search(pattern, text_lower)
    if m:
        start_raw, start_mer, end_raw, end_mer = m.groups()
        if not start_mer and end_mer:
            # If start didn't specify meridiem, infer from context
            # e.g., "from 2 to 4 PM" -> both PM. "from 11 to 1 PM" -> 11 AM to 1 PM
            h_val = int(start_raw) if start_raw.isdigit() else 12
            if end_mer == "pm":
                if h_val < 12 and h_val > int(end_raw if end_raw.isdigit() else 12):
                    start_mer = "am"
                else:
                    start_mer = "pm"
            else:
                start_mer = end_mer

        start_h = convert_hour(start_raw, start_mer)
        end_h = convert_hour(end_raw, end_mer)
        if 0 <= start_h < end_h <= 24:
            return list(range(start_h, end_h))

    return []

def deterministic_semantic_parser(notes: List[str], battery: BatteryInput) -> List[Dict[str, Any]]:
    """High-precision fallback parser for operator notes in case LLM is unavailable."""
    results = []
    
    # Common distractors that clearly indicate no_op
    distractor_keywords = [
        "cafeteria", "menu", "sports", "registration", "book", "library",
        "seminar", "booking", "club", "notices", "holiday", "event",
        "conference", "catering", "bus", "transport"
    ]

    for idx, note in enumerate(notes):
        lower = note.lower()
        
        # Check if it's a distractor
        if any(dk in lower for dk in distractor_keywords):
            results.append({
                "note_index": idx,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": "Administrative note; no effect on energy scheduling."
            })
            continue

        hours = parse_time_window(note)

        # 1. Check solar reduction
        if any(w in lower for w in ["solar", "photovoltaic", "pv", "panel", "sun"]):
            factor = 1.0
            # Check percentages
            m_pct = re.search(r'(\d+(?:\.\d+)?)\s*%', lower)
            if m_pct:
                val = float(m_pct.group(1))
                if "reduction" in lower or "drop by" in lower or "decrease by" in lower:
                    factor = max(0.0, min(1.0, 1.0 - (val / 100.0)))
                else:
                    factor = max(0.0, min(1.0, val / 100.0))
            elif "half" in lower:
                factor = 0.5
            elif "one-fifth" in lower or "1/5" in lower:
                factor = 0.2
            elif "one-fourth" in lower or "quarter" in lower:
                factor = 0.25
            elif "one-third" in lower:
                factor = 0.3333

            results.append({
                "note_index": idx,
                "applies": True,
                "directive_type": "solar_reduction",
                "structured_adjustment": {
                    "hours": hours,
                    "factor": round(factor, 4)
                },
                "explanation": f"Solar output adjusted to {factor*100:.1f}% of forecast during scheduled window."
            })
            continue

        # 2. Check no_discharge_window
        if ("discharge" in lower or "discharging" in lower) and any(w in lower for w in [
            "not", "no", "disable", "avoid", "stop", "prohibit", "prevent", "protect",
            "maintenance", "isolated", "offline", "inspect", "check", "testing", "test", "outage",
            "unavailable", "circuit", "down"
        ]):
            results.append({
                "note_index": idx,
                "applies": True,
                "directive_type": "no_discharge_window",
                "structured_adjustment": {"hours": hours},
                "explanation": "Battery discharging is prohibited during this maintenance/testing window."
            })
            continue

        # 3. Check no_charge_window
        if not ("discharge" in lower or "discharging" in lower) and any(w in lower for w in ["charge", "charging", "charger"]) and any(w in lower for w in [
            "not", "no", "disable", "avoid", "stop", "prohibit", "prevent", "protect",
            "maintenance", "isolated", "offline", "inspect", "check", "repair", "service", "technician", "outage",
            "unavailable", "circuit", "down"
        ]):
            results.append({
                "note_index": idx,
                "applies": True,
                "directive_type": "no_charge_window",
                "structured_adjustment": {"hours": hours},
                "explanation": "Battery charging is disabled during this maintenance window."
            })
            continue

        # 4. Check minimum_battery_reserve
        if any(w in lower for w in ["reserve", "stored in the battery", "remain in the battery", "keep at least", "buffer", "maintains at least", "maintain at least", "hold at least", "minimum storage"]):
            min_energy = battery.minimum_energy_kwh
            m_pct = re.search(r'(\d+(?:\.\d+)?)\s*%', lower)
            m_kwh = re.search(r'(\d+(?:\.\d+)?)\s*kwh', lower)
            if m_pct and "capacity" in lower:
                pct = float(m_pct.group(1))
                min_energy = (pct / 100.0) * battery.capacity_kwh
            elif m_kwh:
                min_energy = float(m_kwh.group(1))

            results.append({
                "note_index": idx,
                "applies": True,
                "directive_type": "minimum_battery_reserve",
                "structured_adjustment": {
                    "hours": hours,
                    "minimum_energy_kwh": round(min_energy, 2)
                },
                "explanation": f"Maintain battery energy reserve at or above {min_energy} kWh."
            })
            continue

        # 5. Check max_grid_window
        if any(w in lower for w in ["grid import", "grid intake", "feeder", "transformer limit", "substation", "grid limit", "max grid"]):
            m_kwh = re.search(r'(\d+(?:\.\d+)?)\s*kwh', lower)
            max_grid = 1000.0
            if m_kwh:
                max_grid = float(m_kwh.group(1))

            results.append({
                "note_index": idx,
                "applies": True,
                "directive_type": "max_grid_window",
                "structured_adjustment": {
                    "hours": hours,
                    "max_grid_kwh": round(max_grid, 2)
                },
                "explanation": f"Grid import constrained to a maximum of {max_grid} kWh."
            })
            continue

        # Default fallback: no_op
        results.append({
            "note_index": idx,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "No operational energy constraint specified."
        })

    return results

def call_gemini_api(notes: List[str], battery: BatteryInput, api_key: str) -> Optional[List[Dict[str, Any]]]:
    """Invokes Gemini model via Google REST API with structured JSON output."""
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    prompt_content = f"""Battery Specs:
- Capacity: {battery.capacity_kwh} kWh
- Base Minimum Reserve: {battery.minimum_energy_kwh} kWh

Operator Notes to interpret:
{json.dumps(notes, indent=2)}

Extract the structured directives for each note following the instructions."""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"text": prompt_content}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.0
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=3.8)
        if resp.status_code == 200:
            data = resp.json()
            cand_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(cand_text)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "directives" in parsed:
                return parsed["directives"]
    except Exception as e:
        logger.warning(f"Gemini API invocation skipped/failed: {e}")
    return None

def call_openai_api(notes: List[str], battery: BatteryInput, api_key: str) -> Optional[List[Dict[str, Any]]]:
    """Invokes OpenAI API via REST with structured JSON output."""
    url = "https://api.openai.com/v1/chat/completions"
    prompt_content = f"""Battery Specs:
- Capacity: {battery.capacity_kwh} kWh
- Base Minimum Reserve: {battery.minimum_energy_kwh} kWh

Operator Notes to interpret:
{json.dumps(notes, indent=2)}"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                for k in ["directives", "interpretations", "results"]:
                    if k in parsed and isinstance(parsed[k], list):
                        return parsed[k]
    except Exception as e:
        logger.warning(f"OpenAI API invocation failed: {e}")
    return None

def interpret_operator_notes(notes: List[str], battery: BatteryInput) -> List[Dict[str, Any]]:
    """
    Main entry point for note interpretation.
    Attempts LLM interpretation first if an API key is provided,
    and falls back to deterministic semantic parser if unconfigured or on failure.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    raw_results = None
    if gemini_key:
        raw_results = call_gemini_api(notes, battery, gemini_key)
    elif openai_key:
        raw_results = call_openai_api(notes, battery, openai_key)

    if not raw_results:
        # Robust semantic fallback
        raw_results = deterministic_semantic_parser(notes, battery)

    return raw_results
