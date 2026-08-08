"""
main.py — Campus Router Health 360 FastAPI Backend
Endpoints:
  GET /rankings -> worst-N routers
  GET /router/{router_id} -> detailed 24h metrics + complaints + score
  POST /copilot -> deterministic diagnosis + phrased natural language response (Gemini API)
"""

import os
import json
from typing import Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()  # reads backend/.env and injects GEMINI_API_KEY into os.environ

from app.data_loader import load_all_data
from app.scoring import get_worst_n
from app.diagnosis import diagnose_router

app = FastAPI(title="Campus Router Health 360 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA = load_all_data()


class CopilotRequest(BaseModel):
    router_id: str
    question: str


def phrase_diagnosis_fallback(router_id: str, diagnosis: dict) -> str:
    """Deterministic natural language phrasing generator using evidence numbers.
    Used if GEMINI_API_KEY is not set or the API call fails."""
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
    """Phrase diagnosis using the Gemini REST API if GEMINI_API_KEY is set,
    else fall back to deterministic phrasing. LLM only ever sees this
    structured diagnosis JSON — never raw CSV data — so it cannot invent
    numbers not already computed by the deterministic diagnosis engine."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return phrase_diagnosis_fallback(router_id, diagnosis)

    diagnosis_json_str = json.dumps(diagnosis, indent=2, default=str)
    prompt = (
        f"You are an AI network copilot assisting campus IT administrators.\n"
        f"User asked: '{question}'\n\n"
        f"Below is a structured diagnostic report for router {router_id}, generated by a "
        f"deterministic diagnosis engine (not by you):\n\n{diagnosis_json_str}\n\n"
        f"Task: Write a concise 2-3 sentence natural language explanation of why this router "
        f"is performing the way it is and what action to take.\n"
        f"CRITICAL CONSTRAINTS:\n"
        f"1. Use ONLY the numbers and facts given in the structured JSON above.\n"
        f"2. Do NOT invent, hallucinate, or infer any external numbers or metrics.\n"
        f"3. Keep the response to exactly 2-3 sentences."
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            print(f"Gemini API error ({response.status_code}): {response.text}")
            return phrase_diagnosis_fallback(router_id, diagnosis)
    except Exception as e:
        print(f"Gemini API request exception: {e}")
        return phrase_diagnosis_fallback(router_id, diagnosis)


@app.get("/")
def read_root():
    return {"status": "online", "app": "Campus Router Health 360 Backend"}


@app.get("/rankings")
def get_rankings(n: int = 10):
    scored_df = DATA["scored_df"]
    routers_df = DATA["routers_df"]

    worst = get_worst_n(scored_df, n=n)
    merged = worst.merge(routers_df, on="router_id", how="left")

    records = merged.to_dict(orient="records")
    return {"count": len(records), "rankings": records}


@app.get("/firmware-stats")
def get_firmware_stats():
    """GET /firmware-stats -> per-firmware-version fleet health stats.
    Used by the frontend to show a banner when a firmware version is
    flagged as a fleet-wide issue (the differentiator feature)."""
    firmware_stats_df = DATA["firmware_stats"]
    raw_records = firmware_stats_df.to_dict(orient="records")
    clean_records = json.loads(json.dumps(raw_records, default=str))
    return {"firmware_stats": clean_records}


@app.get("/router/{router_id}")
def get_router_detail(router_id: str):
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

    my_metrics = metrics_df[metrics_df["router_id"] == router_id].sort_values("hour")
    metrics_list = my_metrics.to_dict(orient="records")

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