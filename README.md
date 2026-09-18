# GridWise — Smart Campus Energy Optimization Service
### BUP CSE Fest 2026 · Hackathon · Preliminary Round

GridWise is an enterprise-grade, high-performance energy scheduling HTTP API service. It converts natural-language campus operator notes into structured operating directives via an LLM, sanitizes and validates them with deterministic guardrails, and solves the 24-hour cost-minimization energy scheduling problem using SciPy Linear Programming (HiGHS solver).

---

## 1. Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │      POST /optimize-energy Request     │
                      │  (scenario_id, operator_notes,         │
                      │   hours[24], battery)                  │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │           LLM Interpreter              │
                      │  (Gemini 2.0 Flash / GPT-4o-mini       │
                      │   + Semantic Fallback Regex Engine)    │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │         Deterministic Guardrail        │
                      │  - Validate allowed directive types    │
                      │  - Ascending unique hours in [0..23]   │
                      │  - Factor in [0, 1] & reserve bounds   │
                      │  - Strict applies semantics            │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │        Math Optimizer (SciPy HiGHS)    │
                      │  - Hour-by-hour Energy balance         │
                      │  - Effective solar & curtailment       │
                      │  - Battery charge/discharge dynamics   │
                      │  - End-of-day battery neutrality       │
                      │  - Objective: Minimize total grid cost │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │          Replay & Final Response       │
                      │  - Recalculated total cost & peak grid │
                      │  - Strict JSON schema matching         │
                      └────────────────────────────────────────┘
```

### Key Components:
1. **LLM Interpreter (`app/interpreter.py`)**:
   - Parses unstructured operator notes into one of 6 supported directive types (`solar_reduction`, `minimum_battery_reserve`, `no_charge_window`, `no_discharge_window`, `max_grid_window`, `no_op`).
   - Normalizes time intervals as start-inclusive, end-exclusive (e.g., 1 PM to 3 PM $\rightarrow$ `[13, 14]`).
   - Built-in **Deterministic Semantic Fallback Engine** ensures 100% reliability and zero 500 crashes even during network/provider disruptions.
2. **Deterministic Guardrails (`app/guardrails.py`)**:
   - Treats LLM output as untrusted until verified.
   - Enforces unique sorted integers for `hours`, bounds on factors ($0 \le \text{factor} \le 1$), and non-negative reserve limits.
   - Guarantees `applies = False` and `structured_adjustment = null` for all `no_op` notes.
3. **Linear Programming Optimizer (`app/optimizer.py`)**:
   - Uses SciPy's modern `highs` solver.
   - 120 decision variables (Grid, Solar used, Charge, Discharge, Energy state across 24 hours).
   - Solves the global minimum cost in under **4 milliseconds**.
   - Enforces hour-by-hour energy balance, battery capacity, rate limits, and end-of-day neutrality ($E_{23} = E_{\text{initial}}$).

---

## 2. Environment Variables & Configuration

Create a `.env` file in the root directory (see `.env.example`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `PORT` | No | `8000` | Port for the HTTP API service. |
| `GEMINI_API_KEY` | Optional | `None` | Google AI Studio Gemini API key (recommended: `gemini-2.0-flash`). |
| `OPENAI_API_KEY` | Optional | `None` | OpenAI API key (`gpt-4o-mini`). |

> **Note on Security:** Do not commit any API keys or secrets to version control. The repository ignores `.env` by default.

---

## 3. Local Quickstart (Clean Environment)

### Step 1: Clone the repository & enter the folder
```bash
git clone <your-repository-url>
cd BUP
```

### Step 2: Create a virtual environment & install dependencies
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 3: Run the local test suite
Verify all 10 public sample cases immediately:
```bash
python test_runner.py
```
Expected output:
```text
======================================================================
RESULTS: 10/10 CASES PASSED (100%)
Average latency per request: ~3.5ms
======================================================================
```

Run the API integration tests:
```bash
python test_api.py
```

### Step 4: Start the API server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 4. API Testing with cURL

### 1. Health Check (`GET /health`)
```bash
curl -X GET http://localhost:8000/health
```
**Response:**
```json
{
  "status": "ok"
}
```

### 2. Energy Optimization (`POST /optimize-energy`)
```bash
curl -X POST http://localhost:8000/optimize-energy \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "TEST-01",
    "operator_notes": [
      "Solar output will drop to about 20% from 1 PM to 3 PM.",
      "The cafeteria menu changes tomorrow."
    ],
    "hours": [
      {"hour": 0, "demand_kwh": 100, "solar_kwh": 0, "tariff_bdt_per_kwh": 6},
      {"hour": 1, "demand_kwh": 90, "solar_kwh": 0, "tariff_bdt_per_kwh": 6},
      {"hour": 2, "demand_kwh": 85, "solar_kwh": 0, "tariff_bdt_per_kwh": 5},
      {"hour": 3, "demand_kwh": 80, "solar_kwh": 0, "tariff_bdt_per_kwh": 5},
      {"hour": 4, "demand_kwh": 85, "solar_kwh": 0, "tariff_bdt_per_kwh": 5},
      {"hour": 5, "demand_kwh": 95, "solar_kwh": 0, "tariff_bdt_per_kwh": 6},
      {"hour": 6, "demand_kwh": 110, "solar_kwh": 10, "tariff_bdt_per_kwh": 8},
      {"hour": 7, "demand_kwh": 130, "solar_kwh": 30, "tariff_bdt_per_kwh": 10},
      {"hour": 8, "demand_kwh": 150, "solar_kwh": 60, "tariff_bdt_per_kwh": 12},
      {"hour": 9, "demand_kwh": 170, "solar_kwh": 90, "tariff_bdt_per_kwh": 14},
      {"hour": 10, "demand_kwh": 190, "solar_kwh": 120, "tariff_bdt_per_kwh": 15},
      {"hour": 11, "demand_kwh": 200, "solar_kwh": 140, "tariff_bdt_per_kwh": 16},
      {"hour": 12, "demand_kwh": 210, "solar_kwh": 150, "tariff_bdt_per_kwh": 16},
      {"hour": 13, "demand_kwh": 200, "solar_kwh": 140, "tariff_bdt_per_kwh": 18},
      {"hour": 14, "demand_kwh": 190, "solar_kwh": 110, "tariff_bdt_per_kwh": 20},
      {"hour": 15, "demand_kwh": 180, "solar_kwh": 80, "tariff_bdt_per_kwh": 22},
      {"hour": 16, "demand_kwh": 190, "solar_kwh": 40, "tariff_bdt_per_kwh": 25},
      {"hour": 17, "demand_kwh": 210, "solar_kwh": 10, "tariff_bdt_per_kwh": 28},
      {"hour": 18, "demand_kwh": 230, "solar_kwh": 0, "tariff_bdt_per_kwh": 30},
      {"hour": 19, "demand_kwh": 220, "solar_kwh": 0, "tariff_bdt_per_kwh": 30},
      {"hour": 20, "demand_kwh": 200, "solar_kwh": 0, "tariff_bdt_per_kwh": 26},
      {"hour": 21, "demand_kwh": 170, "solar_kwh": 0, "tariff_bdt_per_kwh": 18},
      {"hour": 22, "demand_kwh": 130, "solar_kwh": 0, "tariff_bdt_per_kwh": 10},
      {"hour": 23, "demand_kwh": 100, "solar_kwh": 0, "tariff_bdt_per_kwh": 7}
    ],
    "battery": {
      "capacity_kwh": 200,
      "initial_energy_kwh": 100,
      "minimum_energy_kwh": 40,
      "max_charge_kwh_per_hour": 50,
      "max_discharge_kwh_per_hour": 50
    }
  }'
```

---

## 5. Docker Fallback & Deployment

### Option A: Pull & Run Pre-built Docker Image (GHCR):
```bash
docker pull ghcr.io/wahidfarhan/bup_cse_ewu_innovators:latest
docker run -d --name gridwise -p 8000:8000 ghcr.io/wahidfarhan/bup_cse_ewu_innovators:latest
```

### Option B: Build & Run Locally:
```bash
docker build -t gridwise-service:latest .
docker run -d --name gridwise -p 8000:8000 gridwise-service:latest
```

### Verify Container Health:
```bash
curl http://localhost:8000/health
```

---

## 6. Known Limitations & Edge Cases Handled

1. **Simultaneous Charge/Discharge**: Handled by net flow canceling and zero-threshold deadbands in the optimizer to ensure battery state strictly complies with valid action enums (`charge`, `discharge`, `idle`).
2. **Provider Downtime / Rate Limits**: If external LLM calls encounter rate limits or timeouts, the built-in deterministic parser automatically activates, maintaining 100% uptime with sub-10ms response time.
3. **End-of-Day Neutrality**: Enforced both in the LP equality constraints ($E_{23} = E_{\text{initial}}$) and verified post-optimization.
