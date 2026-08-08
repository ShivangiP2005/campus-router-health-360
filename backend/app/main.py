"""
main.py — Campus Router Health 360 FastAPI Backend
Endpoints:
  GET /rankings -> worst-N routers
  GET /router/{router_id} -> detailed 24h metrics + complaints + score
  POST /copilot -> deterministic diagnosis + phrased natural language response
"""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.data_loader import load_all_data
from backend.app.scoring import get_worst_n
from backend.app.diagnosis import diagnose_router

app = FastAPI(title="Campus Router Health 360 API")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load dataset once at startup
DATA = load_all_data()


class CopilotRequest(BaseModel):
    router_id: str
    question: str


def phrase_diagnosis_fallback(router_id: str, diagnosis: dict) -> str:
    """Deterministic natural language phrasing generator using evidence numbers."""
    cause = diagnosis.get("cause")
    evidence = diagnosis.get("evidence", {})
    fix = diagnosis.get("fix")
    confidence = diagnosis.get("confidence", 0.0)

    if cause == "user_side_issue":
        sc = evidence.get("health_score", 0)
        lat = evidence.get("avg_latency_ms", 0)
        bh = evidence.get("bad_hour_count", 0)
        cc = evidence.get("complaint_count", 0)
        sample = evidence.get("sample_complaint", "")
        return (
            f"Router {router_id} telemetry shows healthy metrics (Health Score: {sc}, Avg Latency: {lat:.1f}ms, "
            f"Bad Hours: {bh}/24). However, {cc} user complaint(s) were filed (e.g., '{sample}'). "
            f"The issue is likely on the user client side. Recommended action: {fix} (confidence: {confidence * 100:.0f}%)."
        )
    elif cause == "healthy":
        sc = evidence.get("health_score", 0)
        bh = evidence.get("bad_hour_count", 0)
        return (
            f"Router {router_id} is operating in healthy condition with a Health Score of {sc}/100 "
            f"and only {bh} bad hour(s) out of 24. No hardware or configuration action is required."
        )
    elif cause == "firmware":
        fw = evidence.get("firmware_version", "unknown")
        cnt = evidence.get("affected_router_count", 0)
        fleet_bh = evidence.get("fleet_avg_bad_hour_count_on_firmware", 0)
        this_bh = evidence.get("this_router_bad_hour_count", 0)
        return (
            f"Router {router_id} is affected by a fleet-wide issue on firmware {fw}. "
            f"A total of {cnt} routers on firmware {fw} show an average of {fleet_bh:.1f} bad hours "
            f"(this router has {this_bh} bad hours). Recommended action: update/patch firmware ({fix})."
        )
    elif cause == "placement_dead_zone":
        sig = evidence.get("avg_signal_dbm", 0)
        bld = evidence.get("building", "N/A")
        rm = evidence.get("room", "N/A")
        return (
            f"Router {router_id} located in {bld} Room {rm} suffers from weak signal strength "
            f"(average {sig:.1f} dBm, weaker than -70 dBm threshold). "
            f"Recommended action: {fix} router to eliminate physical dead zones."
        )
    elif cause == "hardware_degradation":
        bh = evidence.get("bad_hour_count", 0)
        lat = evidence.get("avg_latency_ms", 0)
        pkt = evidence.get("avg_packet_loss_pct", 0)
        disc = evidence.get("avg_disconnects", 0)
        mdl = evidence.get("model", "N/A")
        return (
            f"Router {router_id} ({mdl}) exhibits sustained hardware degradation across {bh} of 24 hours "
            f"with elevated latency ({lat:.1f}ms), packet loss ({pkt:.1f}%), and average disconnects ({disc:.1f}). "
            f"Recommended action: {fix} the physical router unit."
        )
    else:
        sc = evidence.get("health_score", 0)
        bh = evidence.get("bad_hour_count", 0)
        return (
            f"Router {router_id} shows borderline underperformance with a Health Score of {sc} "
            f"and {bh} bad hours. Recommended action: {fix}."
        )


def phrase_diagnosis(router_id: str, question: str, diagnosis: dict) -> str:
    """Phrase diagnosis using Anthropic API if key is set, else deterministic fallback."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            prompt = (
                f"User asked: '{question}'.\n"
                f"Structured diagnosis data for router {router_id}: {diagnosis}.\n"
                f"Phrase a clear, helpful 2-3 sentence answer explaining the cause, fix, and exact numbers provided. "
                f"Do not invent any numbers not present in the diagnosis evidence."
            )
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic API call fallback due to error: {e}")

    return phrase_diagnosis_fallback(router_id, diagnosis)


@app.get("/")
def read_root():
    return {"status": "online", "app": "Campus Router Health 360 Backend"}


@app.get("/rankings")
def get_rankings(n: int = 10):
    """GET /rankings -> worst-N routers sorted ascending by health_score."""
    scored_df = DATA["scored_df"]
    routers_df = DATA["routers_df"]

    worst = get_worst_n(scored_df, n=n)
    merged = worst.merge(routers_df, on="router_id", how="left")

    records = merged.to_dict(orient="records")
    return {"count": len(records), "rankings": records}


@app.get("/router/{router_id}")
def get_router_detail(router_id: str):
    """GET /router/{router_id} -> router details, 24h hourly metrics, complaints, score."""
    scored_df = DATA["scored_df"]
    routers_df = DATA["routers_df"]
    metrics_df = DATA["metrics_df"]
    complaints_df = DATA["complaints_df"]

    score_row = scored_df[scored_df["router_id"] == router_id]
    if score_row.empty:
        raise HTTPException(status_code=404, detail=f"Router {router_id} not found")

    router_info = routers_df[routers_df["router_id"] == router_id]
    info_dict = router_info.iloc[0].to_dict() if not router_info.empty else {}

    score_dict = score_row.iloc[0].to_dict()

    # 24h hourly metrics sorted chronologically
    my_metrics = metrics_df[metrics_df["router_id"] == router_id].sort_values("hour")
    metrics_list = my_metrics.to_dict(orient="records")

    # Complaints for this router
    my_complaints = complaints_df[complaints_df["router_id"] == router_id]
    complaints_list = my_complaints.to_dict(orient="records")

    return {
        "router_id": router_id,
        "info": info_dict,
        "score": score_dict,
        "metrics": metrics_list,
        "complaints": complaints_list,
    }


@app.post("/copilot")
def query_copilot(req: CopilotRequest):
    """POST /copilot -> deterministic diagnosis + phrased answer."""
    scored_df = DATA["scored_df"]
    routers_df = DATA["routers_df"]
    complaints_df = DATA["complaints_df"]
    firmware_stats = DATA["firmware_stats"]

    diag = diagnose_router(
        req.router_id, scored_df, routers_df, complaints_df, firmware_stats
    )
    phrased = phrase_diagnosis(req.router_id, req.question, diag)

    return {
        "router_id": req.router_id,
        "question": req.question,
        "diagnosis": diag,
        "phrased_answer": phrased,
    }