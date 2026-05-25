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
