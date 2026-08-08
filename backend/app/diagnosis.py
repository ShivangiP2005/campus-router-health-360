"""
diagnosis.py — Campus Router Health 360
Deterministic, rule-based diagnosis engine. NO LLM CALLS HERE.

This module returns a structured dict: {cause, evidence, fix, confidence}.
The API layer passes this dict to Claude ONLY to phrase it in natural
language — Claude never sees raw CSV data, so it cannot invent numbers.

Fix options (spec-defined): "firmware" | "relocate" | "replace" | "user_education"
"""

import pandas as pd

FIRMWARE_ISSUE_THRESHOLD = 5      # min bad_hour_count fleet-avg on that firmware to flag
SIGNAL_WEAK_DBM = -70
LATENCY_HIGH_MS = 60
PACKET_LOSS_HIGH_PCT = 2.0
OLD_ROUTER_DAYS = 500              # issue_date older than this = aging hardware candidate


def diagnose_router(router_id: str, scored_df: pd.DataFrame,
                     routers_df: pd.DataFrame, complaints_df: pd.DataFrame,
                     firmware_stats: pd.DataFrame) -> dict:
    """
    scored_df: output of scoring.compute_health_scores()
    routers_df: raw routers.csv
    complaints_df: raw complaints csv
    firmware_stats: output of get_firmware_batch_flags()
    """
    row = scored_df[scored_df["router_id"] == router_id]
    if row.empty:
        return {"cause": "unknown", "evidence": {}, "fix": None,
                "confidence": 0.0, "note": "router_id not found"}
    row = row.iloc[0]

    info = routers_df[routers_df["router_id"] == router_id]
    info = info.iloc[0] if not info.empty else None

    my_complaints = complaints_df[complaints_df["router_id"] == router_id]
    has_complaints = len(my_complaints) > 0

    is_healthy = row["health_score"] >= 70 and not row["sustained_bad"]

    # --- Rule 1: healthy metrics BUT complaints exist -> user education,
    #     never "just healthy" and never replace. Checked BEFORE the plain
    #     healthy rule so complaints are never silently ignored. ---
    if is_healthy and has_complaints:
        return {
            "cause": "user_side_issue",
            "evidence": {
                "health_score": float(row["health_score"]),
                "avg_latency_ms": float(row["avg_latency_ms"]),
                "avg_packet_loss_pct": float(row["avg_packet_loss_pct"]),
                "bad_hour_count": int(row["bad_hour_count"]),
                "complaint_count": int(len(my_complaints)),
                "sample_complaint": my_complaints.iloc[0]["complaint_text"],
            },
            "fix": "user_education",
            "confidence": 0.7,
        }

    # --- Rule 2: healthy, no complaints ---
    if is_healthy:
        return {
            "cause": "healthy",
            "evidence": {
                "health_score": float(row["health_score"]),
                "avg_latency_ms": float(row["avg_latency_ms"]),
                "avg_packet_loss_pct": float(row["avg_packet_loss_pct"]),
                "bad_hour_count": int(row["bad_hour_count"]),
            },
            "fix": None,
            "confidence": 0.9,
        }

    # --- Rule 3: firmware-wide issue ---
    if info is not None:
        fw = info["firmware_version"]
        fw_row = firmware_stats[firmware_stats["firmware_version"] == fw]
        if not fw_row.empty and fw_row.iloc[0]["affected_router_count"] >= 3 \
                and fw_row.iloc[0]["avg_bad_hour_count"] >= FIRMWARE_ISSUE_THRESHOLD \
                and row["bad_hour_count"] >= FIRMWARE_ISSUE_THRESHOLD:
            return {
                "cause": "firmware",
                "evidence": {
                    "firmware_version": fw,
                    "affected_router_count": int(fw_row.iloc[0]["affected_router_count"]),
                    "fleet_avg_bad_hour_count_on_firmware": float(fw_row.iloc[0]["avg_bad_hour_count"]),
                    "this_router_bad_hour_count": int(row["bad_hour_count"]),
                },
                "fix": "firmware",
                "confidence": 0.85,
            }

    # --- Rule 4: weak signal -> placement issue ---
    if row["avg_signal_dbm"] < SIGNAL_WEAK_DBM:
        return {
            "cause": "placement_dead_zone",
            "evidence": {
                "avg_signal_dbm": float(row["avg_signal_dbm"]),
                "building": str(info["building"]) if info is not None else None,
                "room": int(info["room"]) if info is not None else None,
            },
            "fix": "relocate",
            "confidence": 0.75,
        }

    # --- Rule 5: sustained bad latency/packet_loss/disconnects, not firmware/signal
    #     -> hardware degradation ---
    if row["sustained_bad"]:
        return {
            "cause": "hardware_degradation",
            "evidence": {
                "bad_hour_count": int(row["bad_hour_count"]),
                "avg_latency_ms": float(row["avg_latency_ms"]),
                "avg_packet_loss_pct": float(row["avg_packet_loss_pct"]),
                "avg_disconnects": float(row["avg_disconnects"]),
                "model": str(info["model"]) if info is not None else None,
            },
            "fix": "replace",
            "confidence": 0.65,
        }

    # --- Fallback: borderline, low confidence ---
    return {
        "cause": "borderline_underperformance",
        "evidence": {
            "health_score": float(row["health_score"]),
            "bad_hour_count": int(row["bad_hour_count"]),
        },
        "fix": "user_education",
        "confidence": 0.4,
    }


def get_firmware_batch_flags(scored_df: pd.DataFrame, routers_df: pd.DataFrame) -> pd.DataFrame:
    """
    DIFFERENTIATOR FEATURE: detects firmware versions where many routers show
    elevated bad_hour_count -> flags a fleet-wide firmware issue, not N
    individual hardware problems.
    """
    merged = scored_df.merge(routers_df[["router_id", "firmware_version"]], on="router_id")
    stats = merged.groupby("firmware_version").agg(
        affected_router_count=("router_id", lambda x: (
            merged.loc[x.index, "bad_hour_count"] >= FIRMWARE_ISSUE_THRESHOLD
        ).sum()),
        total_routers=("router_id", "count"),
        avg_bad_hour_count=("bad_hour_count", "mean"),
        avg_health_score=("health_score", "mean"),
    ).reset_index()
    stats["is_flagged"] = (
        (stats["affected_router_count"] >= 3) & (stats["avg_bad_hour_count"] >= FIRMWARE_ISSUE_THRESHOLD)
    )
    return stats.sort_values("avg_health_score")
    