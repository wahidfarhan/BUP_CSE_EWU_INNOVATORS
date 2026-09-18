# GridWise — Smart Campus Energy Optimization Service
### BUP CSE Fest 2026 · Hackathon · Preliminary Round

GridWise is an enterprise-grade, high-performance energy scheduling HTTP API service. It converts natural-language campus operator notes into structured operating directives via an LLM, sanitizes and validates them with deterministic guardrails, and solves the 24-hour cost-minimization energy scheduling problem using SciPy Linear Programming (HiGHS solver).

---

## 🌐 Live Deployment & Interactive Endpoints

The service is deployed live on Render with automatic health monitoring and interactive OpenAPI/Swagger documentation:

| Resource | URL | Method | Description |
|---|---|---|---|
| **Live API Service** | [https://bup-gridwise.onrender.com](https://bup-gridwise.onrender.com) | `GET /` | Root service status and metadata |
| **Health Check** | [https://bup-gridwise.onrender.com/health](https://bup-gridwise.onrender.com/health) | `GET /health` | Production health check (`{"status": "ok"}`) |
| **Interactive API Docs** | [https://bup-gridwise.onrender.com/docs](https://bup-gridwise.onrender.com/docs) | `GET /docs` | Swagger UI documentation with test console |
| **Optimization Endpoint** | `https://bup-gridwise.onrender.com/optimize-energy` | `POST /optimize-energy` | Main LLM interpretation & LP optimizer endpoint |

```bash
# Instant Live Health Check
curl https://bup-gridwise.onrender.com/health
# Response: {"status":"ok"}
```

---

## ⚡ Quick Evaluation Guide for Judges & Organizers

To evaluate GridWise with zero setup friction, choose any of the 3 ready evaluation methods below:

### Option A: In-Browser Interactive Testing (Zero Setup Friction)
Judges can test any scenario payload directly from their web browser without installing tools or writing code:
1. Open the **Interactive Swagger UI**: [https://bup-gridwise.onrender.com/docs](https://bup-gridwise.onrender.com/docs)
2. Expand `POST /optimize-energy` and click **"Try it out"**.
3. Paste any test case JSON and click **"Execute"**. The verified JSON response and hourly dispatch schedule will render immediately.

### Option B: Terminal cURL & PowerShell Test (Instant Live API Verification)

#### 1. Universal Cross-Platform 1-Liner (Windows, Linux, macOS):
Using the bundled `sample_request.json` directly from the repository root avoids multi-line quote escaping issues across all operating systems:
```bash
curl -X POST "https://bup-gridwise.onrender.com/optimize-energy" -H "Content-Type: application/json" -d "@sample_request.json"
```

#### 2. Linux / macOS / Git Bash (Inline Multi-line):
```bash
curl -X POST "https://bup-gridwise.onrender.com/optimize-energy" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "JUDGE-SAMPLE-EVAL",
    "operator_notes": [
      "Solar maintenance from 10 AM to noon; only half generation usable.",
      "Keep at least 60 kWh battery reserve throughout the day.",
      "The cafeteria is serving biryani today."
    ],
    "battery": {
      "capacity_kwh": 200.0,
      "initial_energy_kwh": 120.0,
      "minimum_energy_kwh": 30.0,
      "max_charge_kwh_per_hour": 40.0,
      "max_discharge_kwh_per_hour": 40.0
    },
    "hours": [
      {"hour": 0, "demand_kwh": 70.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 6.0},
      {"hour": 1, "demand_kwh": 65.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 6.0},
      {"hour": 2, "demand_kwh": 60.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 5.0},
      {"hour": 3, "demand_kwh": 60.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 5.0},
      {"hour": 4, "demand_kwh": 65.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 6.0},
      {"hour": 5, "demand_kwh": 70.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 7.0},
      {"hour": 6, "demand_kwh": 80.0, "solar_kwh": 10.0, "tariff_bdt_per_kwh": 8.0},
      {"hour": 7, "demand_kwh": 95.0, "solar_kwh": 25.0, "tariff_bdt_per_kwh": 10.0},
      {"hour": 8, "demand_kwh": 110.0, "solar_kwh": 50.0, "tariff_bdt_per_kwh": 12.0},
      {"hour": 9, "demand_kwh": 125.0, "solar_kwh": 75.0, "tariff_bdt_per_kwh": 14.0},
      {"hour": 10, "demand_kwh": 140.0, "solar_kwh": 100.0, "tariff_bdt_per_kwh": 16.0},
      {"hour": 11, "demand_kwh": 150.0, "solar_kwh": 120.0, "tariff_bdt_per_kwh": 17.0},
      {"hour": 12, "demand_kwh": 155.0, "solar_kwh": 135.0, "tariff_bdt_per_kwh": 18.0},
      {"hour": 13, "demand_kwh": 150.0, "solar_kwh": 125.0, "tariff_bdt_per_kwh": 17.0},
      {"hour": 14, "demand_kwh": 145.0, "solar_kwh": 105.0, "tariff_bdt_per_kwh": 15.0},
      {"hour": 15, "demand_kwh": 140.0, "solar_kwh": 80.0, "tariff_bdt_per_kwh": 16.0},
      {"hour": 16, "demand_kwh": 150.0, "solar_kwh": 50.0, "tariff_bdt_per_kwh": 20.0},
      {"hour": 17, "demand_kwh": 165.0, "solar_kwh": 20.0, "tariff_bdt_per_kwh": 24.0},
      {"hour": 18, "demand_kwh": 180.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 28.0},
      {"hour": 19, "demand_kwh": 190.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 30.0},
      {"hour": 20, "demand_kwh": 180.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 27.0},
      {"hour": 21, "demand_kwh": 155.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 20.0},
      {"hour": 22, "demand_kwh": 120.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 12.0},
      {"hour": 23, "demand_kwh": 90.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 8.0}
    ]
  }'
```

#### 3. Windows PowerShell:
```powershell
Invoke-RestMethod -Uri "https://bup-gridwise.onrender.com/optimize-energy" -Method POST -ContentType "application/json" -InFile "sample_request.json"
```

#### 4. Windows Command Prompt (CMD 1-Liner):
```cmd
curl -X POST "https://bup-gridwise.onrender.com/optimize-energy" -H "Content-Type: application/json" --data-raw "{\"scenario_id\":\"BUP-TEST-CASE-01\",\"operator_notes\":[\"Facilities will wash the rooftop solar panels from noon until 2 PM. During cleaning, usable solar should be treated as roughly 25% of the forecast.\",\"The sports office moved registration deadline.\",\"Maloy eats rice\"],\"battery\":{\"capacity_kwh\":200.0,\"initial_energy_kwh\":100.0,\"minimum_energy_kwh\":30.0,\"max_charge_kwh_per_hour\":40.0,\"max_discharge_kwh_per_hour\":40.0},\"hours\":[{\"hour\":0,\"demand_kwh\":60.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":6.0},{\"hour\":1,\"demand_kwh\":55.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":6.0},{\"hour\":2,\"demand_kwh\":50.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":5.0},{\"hour\":3,\"demand_kwh\":50.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":5.0},{\"hour\":4,\"demand_kwh\":55.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":5.0},{\"hour\":5,\"demand_kwh\":65.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":6.0},{\"hour\":6,\"demand_kwh\":80.0,\"solar_kwh\":5.0,\"tariff_bdt_per_kwh\":8.0},{\"hour\":7,\"demand_kwh\":100.0,\"solar_kwh\":20.0,\"tariff_bdt_per_kwh\":10.0},{\"hour\":8,\"demand_kwh\":120.0,\"solar_kwh\":50.0,\"tariff_bdt_per_kwh\":12.0},{\"hour\":9,\"demand_kwh\":135.0,\"solar_kwh\":80.0,\"tariff_bdt_per_kwh\":14.0},{\"hour\":10,\"demand_kwh\":140.0,\"solar_kwh\":110.0,\"tariff_bdt_per_kwh\":16.0},{\"hour\":11,\"demand_kwh\":145.0,\"solar_kwh\":130.0,\"tariff_bdt_per_kwh\":16.0},{\"hour\":12,\"demand_kwh\":150.0,\"solar_kwh\":140.0,\"tariff_bdt_per_kwh\":15.0},{\"hour\":13,\"demand_kwh\":145.0,\"solar_kwh\":130.0,\"tariff_bdt_per_kwh\":14.0},{\"hour\":14,\"demand_kwh\":140.0,\"solar_kwh\":110.0,\"tariff_bdt_per_kwh\":13.0},{\"hour\":15,\"demand_kwh\":135.0,\"solar_kwh\":70.0,\"tariff_bdt_per_kwh\":14.0},{\"hour\":16,\"demand_kwh\":140.0,\"solar_kwh\":35.0,\"tariff_bdt_per_kwh\":18.0},{\"hour\":17,\"demand_kwh\":150.0,\"solar_kwh\":10.0,\"tariff_bdt_per_kwh\":22.0},{\"hour\":18,\"demand_kwh\":170.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":28.0},{\"hour\":19,\"demand_kwh\":180.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":30.0},{\"hour\":20,\"demand_kwh\":170.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":26.0},{\"hour\":21,\"demand_kwh\":140.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":18.0},{\"hour\":22,\"demand_kwh\":110.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":10.0},{\"hour\":23,\"demand_kwh\":80.0,\"solar_kwh\":0.0,\"tariff_bdt_per_kwh\":7.0}]}"
```

### Option C: Local 1-Command Automated Harness Verification
To run the automated validation suite on all 10 official public sample cases locally:
```bash
git clone https://github.com/wahidfarhan/BUP_CSE_EWU_INNOVATORS.git
cd BUP_CSE_EWU_INNOVATORS
pip install -r requirements.txt
python test_runner.py
```
*Expected Output: `RESULTS: 10/10 CASES PASSED (100%)` in under 50 milliseconds.*

### Option D: Docker Fallback 1-Liner
If evaluating via containerized fallback:
```bash
docker run -d -p 8000:8000 -e PORT=8000 ghcr.io/wahidfarhan/bup_cse_ewu_innovators:latest
curl http://localhost:8000/health
```

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
                      │   + Deterministic Semantic Fallback)   │
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
                      │    Post-Optimization Validator & Final │
                      │  - Deterministic invariant audit       │
                      │  - Recalculated total cost & peak grid │
                      │  - Strict JSON schema matching         │
                      └────────────────────────────────────────┘
```

### LLM Role
The LLM is used directly in the operator-note interpretation path. For every operator note, the model produces a structured directive interpretation containing relevance, directive type, affected hours, and required numeric parameters. The resulting model output is treated as untrusted data and is passed through deterministic guardrails before any directive reaches the optimizer.

**Pipeline Flow:**
`Operator Note` ➔ `LLM Structured Interpretation` ➔ `Deterministic Validation / Guardrails` ➔ `Validated Directive` ➔ `Optimization Constraints` ➔ `Deterministic Schedule Invariant Validator` ➔ `24-hour Schedule`

### Key Components:
1. **LLM Interpreter (`app/interpreter.py`)**:
   - Parses unstructured operator notes into one of 6 supported directive types (`solar_reduction`, `minimum_battery_reserve`, `no_charge_window`, `no_discharge_window`, `max_grid_window`, `no_op`).
   - Normalizes time intervals as start-inclusive, end-exclusive (e.g., 1 PM to 3 PM $\rightarrow$ `[13, 14]`).
   - Provider failures are handled through a deterministic fallback parser to keep the service operational when an external model provider is temporarily unavailable. Under normal operation, the LLM directly produces the structured operator-note interpretation used by the optimizer.
2. **Deterministic Guardrails (`app/guardrails.py`)**:
   - Treats LLM output as untrusted until verified.
   - Enforces unique sorted integers for `hours`, bounds on factors ($0 \le \text{factor} \le 1$), and non-negative reserve limits.
   - Guarantees `applies = False` and `structured_adjustment = null` for all `no_op` notes.
3. **Linear Programming Optimizer (`app/optimizer.py`)**:
   - Uses SciPy's modern `highs` solver over 120 decision variables (Grid, Solar used, Charge, Discharge, Energy state across 24 hours).
   - The HiGHS optimization stage typically solves the LP in a few milliseconds; end-to-end latency depends primarily on LLM/provider response time.
   - Enforces hour-by-hour energy balance, battery capacity, rate limits, and end-of-day neutrality ($E_{23} = E_{\text{initial}}$).
   - Features a deterministic post-optimization invariant validator checking energy balance ($\le 0.01$ tolerance), solar limits, and state transitions before returning.

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

#### Public Sample Cases
The repository includes the organizer-provided public sample cases for automated evaluation.
Run:
```bash
python test_runner.py
```
Expected output:
```text
======================================================================
RESULTS: 10/10 CASES PASSED (100%)
======================================================================
```

Run the API integration and replay tests:
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
- **Live Deployment:**
  ```bash
  curl https://bup-gridwise.onrender.com/health
  ```
- **Local:**
  ```bash
  curl http://localhost:8000/health
  ```
**Response:**
```json
{
  "status": "ok"
}
```

### 2. Energy Optimization (`POST /optimize-energy`)
- **Live Deployment:**
  ```bash
  curl -X POST https://bup-gridwise.onrender.com/optimize-energy \
    -H "Content-Type: application/json" \
    -d '{ ... }'
  ```
- **Full cURL Example (Local or Live):**
```bash
curl -X POST https://bup-gridwise.onrender.com/optimize-energy \
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

The container binds to `0.0.0.0:8000` and exposes port `8000`.

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
Expected output:
```json
{"status":"ok"}
```

---

## 6. Known Limitations & Edge Cases Handled

1. **Simultaneous Charge/Discharge**: Handled by net flow canceling and zero-threshold deadbands in the optimizer to ensure battery state strictly complies with valid action enums (`charge`, `discharge`, `idle`).
2. **Provider Downtime / Rate Limits**: If external LLM calls encounter rate limits or timeouts, the built-in deterministic parser automatically activates as a resilience fallback to ensure continuous service availability.
3. **End-of-Day Neutrality**: Enforced both in the LP equality constraints ($E_{23} = E_{\text{initial}}$) and verified post-optimization.
4. **Post-Optimization Schedule Verification**: All returned plans are checked by a deterministic invariant validator ensuring energy balance and battery limits hold within $\le 0.01$ tolerance.
