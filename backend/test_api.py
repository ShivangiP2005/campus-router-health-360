"""
test_api.py — Verification script for Campus Router Health 360 backend.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent))

from app.data_loader import load_data
from app.scoring import compute_health_scores, get_worst_n
from app.diagnosis import diagnose_router, get_firmware_batch_flags

def test_data_and_logic():
    print("--- 1. Testing Data Loader ---")
    routers_df, metrics_df, complaints_df = load_data()
    print(f"Loaded routers: {len(routers_df)} rows")
    print(f"Loaded metrics: {len(metrics_df)} rows")
    print(f"Loaded complaints: {len(complaints_df)} rows")
    assert len(routers_df) > 0, "routers_df is empty"
    assert len(metrics_df) > 0, "metrics_df is empty"
    assert len(complaints_df) > 0, "complaints_df is empty"

    print("\n--- 2. Testing Scoring Engine ---")
    scored_df = compute_health_scores(metrics_df)
    print(f"Scored routers count: {len(scored_df)}")
    worst_10 = get_worst_n(scored_df, n=10)
    print("Worst 5 routers:")
    print(worst_10[["router_id", "health_score", "bad_hour_count", "sustained_bad"]].head())

    print("\n--- 3. Testing Diagnosis Engine ---")
    fw_flags = get_firmware_batch_flags(scored_df, routers_df)
    print("Firmware batch flags:")
    print(fw_flags)

    # Test diagnosis for worst router
    worst_router_id = worst_10.iloc[0]["router_id"]
    diag = diagnose_router(worst_router_id, scored_df, routers_df, complaints_df, fw_flags)
    print(f"\nDiagnosis for {worst_router_id}:")
    print(diag)

    print("\n--- 4. Testing FastAPI App via TestClient ---")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Test GET /
    res_root = client.get("/")
    assert res_root.status_code == 200, f"Root failed: {res_root.status_code}"
    print("GET / -> OK:", res_root.json())

    # Test GET /rankings
    res_rankings = client.get("/rankings?limit=5")
    assert res_rankings.status_code == 200, f"Rankings failed: {res_rankings.status_code}"
    rankings_data = res_rankings.json()
    print("GET /rankings?limit=5 -> OK, returned count:", rankings_data["count"])
    assert len(rankings_data["rankings"]) == 5

    # Test GET /router/{router_id}
    res_router = client.get(f"/router/{worst_router_id}")
    assert res_router.status_code == 200, f"Router detail failed: {res_router.status_code}"
    router_data = res_router.json()
    print(f"GET /router/{worst_router_id} -> OK, health_score:", router_data["score_details"]["health_score"])

    # Test POST /copilot
    res_copilot = client.post("/copilot", json={"router_id": worst_router_id, "question": "Why is this router underperforming?"})
    assert res_copilot.status_code == 200, f"Copilot failed: {res_copilot.status_code}"
    copilot_data = res_copilot.json()
    print(f"\nPOST /copilot -> OK for {worst_router_id}:")
    print("Cause:", copilot_data["diagnosis"]["cause"])
    print("Phrased answer:", copilot_data["phrased_answer"])

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_data_and_logic()
