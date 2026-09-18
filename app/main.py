import logging
import time
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

from app.models import (
    OptimizeEnergyRequest,
    OptimizeEnergyResponse,
    HealthResponse
)
from app.interpreter import interpret_operator_notes
from app.guardrails import validate_and_guardrail_directives
from app.optimizer import solve_energy_schedule

# Load .env file if available
load_dotenv()

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gridwise")

app = FastAPI(
    title="GridWise Smart Campus Energy Optimizer",
    description="LLM-assisted energy scheduling API for BUP CSE Fest 2026 Hackathon",
    version="1.0.0"
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles malformed requests and returns HTTP 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Malformed JSON or structurally invalid request.", "errors": exc.errors()}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Controlled internal error handler to avoid leaking secrets or stack traces."""
    logger.error(f"Internal server error: {exc}", exc_info=False)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred while processing the energy schedule."}
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Readiness endpoint for the judging harness."""
    return HealthResponse(status="ok")

@app.post("/optimize-energy", response_model=OptimizeEnergyResponse)
async def optimize_energy(req: OptimizeEnergyRequest):
    """
    Main endpoint:
    1. Interprets natural-language operator notes via LLM.
    2. Runs deterministic guardrails on extracted directives.
    3. Solves the 24-hour linear program with HiGHS optimizer.
    4. Formulates and returns the verified response schema.
    """
    start_time = time.time()
    
    # 1. LLM Note Interpretation
    num_notes = len(req.operator_notes)
    raw_directives = interpret_operator_notes(req.operator_notes, req.battery)

    # 2. Guardrails & Sanitization
    guarded_directives = validate_and_guardrail_directives(
        raw_directives=raw_directives,
        num_notes=num_notes,
        battery=req.battery
    )

    # 3. Math Optimization
    hourly_plan, total_grid_kwh, total_cost_bdt, peak_grid_kwh, plan_summary = solve_energy_schedule(
        hours_data=req.hours,
        battery=req.battery,
        directives=guarded_directives
    )

    elapsed = time.time() - start_time
    logger.info(f"Processed scenario {req.scenario_id} in {elapsed:.3f}s, cost={total_cost_bdt} BDT")

    return OptimizeEnergyResponse(
        scenario_id=req.scenario_id,
        directive_interpretation=guarded_directives,
        hourly_plan=hourly_plan,
        total_grid_kwh=total_grid_kwh,
        total_cost_bdt=total_cost_bdt,
        peak_grid_kwh=peak_grid_kwh,
        plan_summary=plan_summary
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
