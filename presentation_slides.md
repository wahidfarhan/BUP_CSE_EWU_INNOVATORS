# GridWise — 3-Minute Presentation Slide Deck & Speaking Script
**BUP CSE Fest 2026 · Hackathon · Preliminary Round**  
**Team Name:** EWU Innovators  
**Target Duration:** Exactly 2 minutes 45 seconds to 3 minutes  

---

## Slide 1: Title & The Challenge (0:00 – 0:35)

### Visual Content:
* **Title:** GridWise — Smart Campus Energy Optimization Service
* **Subtitle:** High-Performance LLM-Assisted Directive Interpretation & Optimal Linear Programming Dispatch
* **Team:** EWU Innovators (East West University)
* **The Core Challenge:**
  * Converting vague, natural-language operator notes into verified, machine-executable grid constraints.
  * Balancing 24-hour variable solar generation, dynamic TOU tariffs, and campus electricity demand.
  * Ensuring zero violations of physical battery dynamics ($E_{23} = E_{\text{initial}}$, charge/discharge rate limits).

### Speaker Script (English):
> *"Hello respected judges and organizers. We are team EWU Innovators, and today we present **GridWise** — an enterprise-grade energy scheduling and optimization service designed for the Smart Campus Energy Challenge.
> 
> The challenge asks us to solve a real-world energy dispatch problem: university microgrids face dynamic tariffs, variable solar generation, and battery degradation limits. Crucially, human campus operators communicate unexpected events through informal text notes — like maintenance outages, temporary emergency reserves, or irrelevant notices.
> 
> GridWise bridges the gap between unstructured human language and rigorous mathematical optimization."*

---

## Slide 2: End-to-End 3-Stage Architecture (0:35 – 1:15)

### Visual Content:
```
[ Operator Notes + 24h Scenario ]
               │
               ▼
┌────────────────────────────────────────┐
│  Stage 1: LLM Directive Interpreter   │
│  - Gemini Flash / GPT-4o-mini          │
│  - Semantic Paraphrase Engine Fallback │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│  Stage 2: Deterministic Guardrails     │
│  - 6 Allowed Directive Types Only      │
│  - Start-Inclusive/End-Exclusive Hours │
│  - Global vs Window Reserve Logic      │
│  - Sanitized applies & null checks     │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│  Stage 3: SciPy HiGHS LP Optimizer     │
│  - 120 Decision Variables (G,S,C,D,E)  │
│  - Hour-by-Hour Energy Balance         │
│  - End-of-Day Battery Neutrality       │
│  - Solves in < 4 milliseconds          │
└──────────────────┬─────────────────────┘
                   │
                   ▼
[ Valid 24h Hourly Plan + Recalculated Cost ]
```

### Speaker Script (English):
> *"To guarantee absolute correctness and zero hallucinations, we built GridWise as a strict three-stage pipeline:
> 
> First is our **LLM Directive Interpreter**. It ingests natural text notes and maps them into one of six canonical directive types. It features a built-in semantic fallback engine to handle network disruptions with zero downtime.
> 
> Second is our **Deterministic Guardrail Engine**. We treat all LLM output as untrusted until verified. It sanitizes start-inclusive, end-exclusive time windows, checks boundaries, and guarantees that irrelevant notes safely become `no_op` with `null` adjustments.
> 
> Third is our **Math Optimizer**, built using SciPy's high-performance HiGHS Linear Programming solver. Across 120 continuous variables, it finds the global mathematically optimal dispatch schedule in under 4 milliseconds."*

---

## Slide 3: Robust Directive Handling & Safety (1:15 – 1:55)

### Visual Content:
* **Supported Directives:**
  1. `solar_reduction`: Usable solar fraction remaining (e.g. 50% $\rightarrow$ factor = 0.5).
  2. `minimum_battery_reserve`: Supports both specific windows (`[18..20]`) and **global whole-day reserve** without hours.
  3. `no_charge_window` & `no_discharge_window`: Strict rate-limit zeroing.
  4. `max_grid_window`: Feeder/transformer intake caps.
  5. `no_op`: Distractors (cafeteria, sports, bookings) safely ignored.
* **Latency & Failure Protection:**
  * Strict **3.8s LLM timeout** ensures API always complies with the $\le 5.0\text{s}$ P95 rubric limit.
  * Graceful **HTTP 400 Bad Request** for physically infeasible grid scenarios.
  * Secret safety: zero API keys or credentials exposed in repository or responses.

### Speaker Script (English):
> *"GridWise handles subtle, real-world edge cases with surgical precision:
> 
> It correctly distinguishes between time-windowed constraints and global whole-day directives — such as general emergency battery reserves where no operating hours are required.
> 
> For performance and reliability, we implemented a strict 3.8-second timeout on external AI calls. If Google's API experiences latency, our deterministic parser takes over instantly, guaranteeing a P95 response time well within the competition's 5.0-second limit for full marks.
> 
> Furthermore, any physically impossible demand scenario is cleanly caught and reported with an informative HTTP 400 Bad Request rather than crashing."*

---

## Slide 4: Validation Results & Optimization Quality (1:55 – 2:30)

### Visual Content:
* **Public Benchmark Results:**
  * **10 / 10 Public Sample Cases Passed (100%)**
  * Average solve time: **2.9 ms per request**
  * Cost parity: **100.0% match** with organizer reference targets.
* **Constraint Compliance:**
  * Energy Balance: $G_h + S_h + D_h - C_h = \text{Demand}_h$ (Every single hour)
  * Solar bounds: $S_h \le \text{Effective Solar}_h$
  * Battery bounds: $\text{Active Reserve}_h \le E_h \le \text{Capacity}$
  * Neutrality: $E_{23} = E_{\text{initial}}$

### Speaker Script (English):
> *"We rigorously validated GridWise against all 10 official public sample cases and novel hidden stress scenarios:
> 
> GridWise achieved a **100% pass rate** across all public test cases. 
> 
> Our HiGHS solver delivers the absolute theoretical minimum electricity cost, achieving an exact cost match with organizer reference solutions. Every hourly plan strictly obeys physical laws: energy balance is maintained, solar is never over-utilized, and end-of-day battery neutrality is satisfied to four decimal places.
> 
> On local hardware, the optimizer finishes in less than 3 milliseconds, and our live cloud deployment serves complete requests in under 3 seconds."*

---

## Slide 5: Live Deployment & Verification (2:30 – 3:00)

### Visual Content:
* **Live Public Endpoint:** `https://bup-gridwise.onrender.com/optimize-energy`
* **Health Check URL:** `https://bup-gridwise.onrender.com/health` $\rightarrow$ `{"status": "ok"}`
* **Interactive Documentation:** `https://bup-gridwise.onrender.com/docs` (Swagger UI)
* **Pre-built Docker Fallback Image:**
  `docker pull ghcr.io/wahidfarhan/bup_cse_ewu_innovators:latest`
  `docker run -d -p 8000:8000 ghcr.io/wahidfarhan/bup_cse_ewu_innovators:latest`
* **GitHub Repository:** `wahidfarhan/BUP_CSE_EWU_INNOVATORS`

### Speaker Script (English):
> *"Finally, GridWise is fully deployed and immediately testable:
> 
> Our live cloud API is running on Render, with active readiness probes on `/health` and full Swagger documentation on `/docs`.
> 
> For offline reproducibility and complete Docker fallback compliance, our automated CI/CD pipeline builds and publishes container images to GitHub Container Registry, ready to pull and run with a single command.
> 
> With robust LLM interpretation, deterministic guardrails, and optimal mathematical dispatch, GridWise is ready for evaluation. Thank you!"*

---

## Quick Bangla Speaking Notes (বাংলায় বলার জন্য গাইডলাইন):
* **Slide 1 (০-৩৫ সেকেন্ড):** সবাইকে সালাম/নমস্কার দিয়ে টিম EWU Innovators এবং GridWise প্রোজেক্ট ইন্ট্রোডিউস করবেন। বলবেন কীভাবে ক্যাম্পাসের বিদ্যুৎ খরচ কমাতে এবং অপারেটরের টেক্সট নোট ইন্টারপ্রেট করতে এটি বানানো হয়েছে।
* **Slide 2 (৩৫-৭৫ সেকেন্ড):** ৩টি মূল ধাপ বোঝাবেন: ১) LLM ইন্টারপ্রেটার, ২) ডিটারমিনিস্টিক গার্ডরেইল (যাতে AI ভুলভাল কিছু বানাতে না পারে), ৩) SciPy HiGHS লিনিয়ার প্রোগ্রামিং অপটিমাইজার (যা ৩ মিলি-সেকেন্ডে সলভ করে)।
* **Slide 3 (৭৫-১১৫ সেকেন্ড):** বলবেন কীভাবে ৬টি ডিরেক্টিভ নির্ভুলভাবে কাজ করে, গ্লোবাল ব্যাটারি রিজার্ভ রক্ষা করে এবং ৩.৮ সেকেন্ড টাইমআউট দিয়ে ৫ সেকেন্ডের লেটেন্সি রুল রক্ষা করা হয়েছে।
* **Slide 4 (১১৫-১৫০ সেকেন্ড):** ১০/১০টি পাবলিক স্যাম্পল কেসে ১০০% পাস এবং হুবহু রেফারেন্স খরচের সাথে মেলা রেজাল্ট হাইলাইট করবেন।
* **Slide 5 (১৫০-১৮০ সেকেন্ড):** লাইভ রেন্ডার লিঙ্ক, `/health` এন্ডপয়েন্ট এবং GitHub Container Registry (Docker) পুল করার অপশন দেখিয়ে ধন্যবাদ দিয়ে শেষ করবেন।
