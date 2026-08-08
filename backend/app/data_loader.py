"""
data_loader.py — Campus Router Health 360
Loads routers.csv, metrics.csv, and complaints.csv into pandas DataFrames.
"""

from pathlib import Path
import pandas as pd


def load_data(data_dir: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads data files from the data directory into pandas DataFrames.
    
    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            (routers_df, metrics_df, complaints_df)
    """
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent.parent / "data"
    else:
        data_dir = Path(data_dir)

    routers_path = data_dir / "routers.csv"
    metrics_path = data_dir / "metrics.csv"
    
    complaints_path = data_dir / "complaints.csv"
    if not complaints_path.exists():
        fallback = data_dir / "COMPLA~1.CSV"
        if fallback.exists():
            complaints_path = fallback

    if not routers_path.exists():
        raise FileNotFoundError(f"routers.csv not found at {routers_path}")
    if not metrics_path.exists():
        raise FileNotFoundError(f"metrics.csv not found at {metrics_path}")
    if not complaints_path.exists():
        raise FileNotFoundError(f"complaints.csv not found at {complaints_path}")

    routers_df = pd.read_csv(routers_path)
    metrics_df = pd.read_csv(metrics_path)
    complaints_df = pd.read_csv(complaints_path)

    return routers_df, metrics_df, complaints_df
