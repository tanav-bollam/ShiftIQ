# =============================================================================
# Forecast Agent
#
# This file predicts next week's demand from historical POS sales. The MVP uses
# a simple, explainable forecasting method instead of a heavy machine learning
# model: it aggregates daily revenue by day of week, calculates historical mean
# and variation, then turns that demand estimate into a recommended staff count
# and confidence score.
#
# Main responsibilities:
# - Read normalized sales data through the Data Agent.
# - Aggregate item-level sales rows into daily revenue totals.
# - Produce a seven-day forecast ordered Monday through Sunday.
# - Estimate confidence from historical consistency: lower relative variation
#   means higher confidence.
# - Estimate staff needed from predicted revenue with a minimum coverage floor.
#
# The output feeds the Forecast page, the scheduling engine, labor cost
# calculations, and Manager Chat responses. The method is intentionally
# transparent so managers can understand why the app thinks Friday or Saturday
# needs more coverage.
# =============================================================================

import pandas as pd

from agents.data_agent import DAY_ORDER, load_sales


def forecast_next_week():
    df = load_sales()
    daily = df.groupby(["date", "day_of_week"], as_index=False)["revenue"].sum()
    grouped = daily.groupby("day_of_week")["revenue"].agg(["mean", "std"]).reset_index()
    results = []

    for day in DAY_ORDER:
        row = grouped[grouped["day_of_week"] == day]
        if row.empty:
            continue
        mean = float(row.iloc[0]["mean"])
        std = float(row.iloc[0]["std"]) if not pd.isna(row.iloc[0]["std"]) else 0.0
        confidence = round(max(0.55, min(0.96, 1 - (std / (mean + 1)))) * 100)
        staff_needed = max(2, round(mean / 950))
        results.append(
            {
                "day": day,
                "predicted_revenue": round(mean, 2),
                "confidence_pct": confidence,
                "staff_needed": int(staff_needed),
            }
        )

    return results
