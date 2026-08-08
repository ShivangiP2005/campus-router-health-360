"""
data_loader.py — Campus Router Health 360
Loads CSV datasets from backend/data and pre-computes health scores and firmware batch stats.
"""

from pathlib import Path
import pandas as pd

from app.scoring import compute_health_scores
from app.diagnosis import get_firmware_batch_flags

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def get_data_file_path(filename: str) -> Path:
    """Find file in DATA_DIR, handling potential short filenames like COMPLA~1.CSV."""
    path = DATA_DIR / filename
    if path.exists():
        return path
    target = filename.split(".")[0].lower()
    for f in DATA_DIR.iterdir():
        if f.name.lower() == filename.lower() or f.name.lower().startswith(target):
            return f
    raise FileNotFoundError(f"Could not find {filename} in {DATA_DIR}")


def load_all_data() -> dict:
    routers_path = get_data_file_path("routers.csv")
    metrics_path = get_data_file_path("metrics.csv")

    try:
        complaints_path = get_data_file_path("complaints.csv")
    except FileNotFoundError:
        complaints_path = get_data_file_path("COMPLA~1.CSV")

    routers_df = pd.read_csv(routers_path)
    metrics_df = pd.read_csv(metrics_path)
    complaints_df = pd.read_csv(complaints_path)

    scored_df = compute_health_scores(metrics_df)
    firmware_stats = get_firmware_batch_flags(scored_df, routers_df)

    return {
        "routers_df": routers_df,
        "metrics_df": metrics_df,
        "complaints_df": complaints_df,
        "scored_df": scored_df,
        "firmware_stats": firmware_stats,
    }