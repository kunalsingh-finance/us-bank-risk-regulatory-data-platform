"""Verify review budgets against the complete latest-quarter population."""
from pathlib import Path

import pandas as pd

from src.dashboard.rankings import current_review_population

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "public_release/data"


def test_synthetic_budget_counts_include_institutions_outside_saved_top_five():
    scores = pd.read_parquet(DATA / "dashboard_demo_scores.parquet")
    drivers = pd.read_parquet(DATA / "dashboard_demo_drivers.parquet")
    population = current_review_population(scores, drivers)
    assert len(population) == 100
    assert population.reporting_date.nunique() == 1
    assert population.reporting_date.iloc[0] == scores.reporting_date.max()
    assert population[["top_1_percent_flag", "top_5_percent_flag", "top_10_percent_flag"]].sum().tolist() == [1, 5, 10]
    assert population[["top_driver_1", "top_driver_2", "top_driver_3"]].notna().all().all()
    assert not population.duplicated(["cert", "reporting_date"]).any()


def test_drivers_join_same_quarter_without_future_or_old_explanations():
    scores = pd.DataFrame([
        dict(cert=1, reporting_date="2024-03-31", same_quarter_rank=1),
        dict(cert=1, reporting_date="2024-06-30", same_quarter_rank=2),
        dict(cert=2, reporting_date="2024-06-30", same_quarter_rank=1),
    ])
    drivers = pd.DataFrame([
        dict(cert=1, reporting_date="2024-03-31", driver_rank=1, feature_name="old"),
        dict(cert=1, reporting_date="2024-06-30", driver_rank=1, feature_name="current"),
        dict(cert=2, reporting_date="2024-09-30", driver_rank=1, feature_name="future"),
    ])
    population = current_review_population(scores, drivers).set_index("cert")
    assert population.loc[1, "top_driver_1"] == "current"
    assert population.loc[2, "top_driver_1"] == "Unavailable"


def test_live_watchlist_radio_changes_visible_review_population(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from src.dashboard import app_pages

    monkeypatch.setattr(app_pages, "DATA", DATA)
    monkeypatch.setattr(app_pages, "DEMO_MODE", True)
    app = AppTest.from_file(str(ROOT / "dashboards/pages/02_Current_Watchlist.py"), default_timeout=30).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 5
    app.radio[0].set_value("Top 10%").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 10
    app.radio[0].set_value("Top 1%").run()
    assert len(app.dataframe[0].value) == 1
