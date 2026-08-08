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

    # Test GET /firmware-stats
    res_fw = client.get("/firmware-stats")
    assert res_fw.status_code == 200, f"Firmware stats failed: {res_fw.status_code}"
    fw_data = res_fw.json()
    print("GET /firmware-stats -> OK, returned entries:", len(fw_data))
    assert any(item["firmware_version"] == "v5.1" and item["is_flagged"] for item in fw_data)

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_data_and_logic()
