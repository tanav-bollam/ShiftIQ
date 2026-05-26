# =============================================================================
# Insight Agent
#
# This file analyzes historical POS sales data and turns it into the operational
# insights shown on the Sales Insights and Forecast pages. It answers questions
# such as which days produce the most revenue, which hours are busiest, which
# products sell best on weekdays versus weekends, and which low-revenue hours
# are likely overstaffed relative to the labor target.
#
# Main responsibilities:
# - Build average daily revenue by day of week.
# - Build the hourly heatmap dataset by aggregating item-level rows into true
#   hourly revenue and transaction totals.
# - Identify the busiest day/hour periods for staffing recommendations.
# - Rank top-selling items separately for weekday and weekend behavior.
# - Flag overstaffing risk using a simple labor-cost guardrail model.
# - Produce high-level summary metrics for dashboard stat cards.
#
# The Insight Agent reads CSV-backed data through the Data Agent and returns
# JSON-friendly lists/dictionaries for FastAPI routes and React charts.
# =============================================================================

from agents.data_agent import DAY_ORDER, load_sales
from agents.forecast_agent import forecast_next_week


def _ordered_day_dict(values):
    return [{"day": day, "revenue": round(float(values.get(day, 0)), 2)} for day in DAY_ORDER]


def get_daily_revenue():
    df = load_sales()
    daily = df.groupby(["date", "day_of_week"], as_index=False)["revenue"].sum()
    averages = daily.groupby("day_of_week")["revenue"].mean().to_dict()
    return _ordered_day_dict(averages)


def get_hourly_heatmap():
    df = load_sales()
    hour_totals = df.groupby(["date", "day_of_week", "hour"], as_index=False).agg(
        revenue=("revenue", "sum"), transaction_count=("transaction_count", "sum")
    )
    hourly = hour_totals.groupby(["day_of_week", "hour"], as_index=False).agg(
        revenue=("revenue", "mean"), transaction_count=("transaction_count", "mean")
    )
    return [
        {
            "day": row.day_of_week,
            "hour": int(row.hour),
            "revenue": round(float(row.revenue), 2),
            "transaction_count": round(float(row.transaction_count), 1),
        }
        for row in hourly.itertuples()
    ]


def get_busiest_periods(top_n=5):
    df = load_sales()
    hour_totals = df.groupby(["date", "day_of_week", "hour"], as_index=False)["revenue"].sum()
    hourly = hour_totals.groupby(["day_of_week", "hour"], as_index=False)["revenue"].mean()
    top = hourly.sort_values("revenue", ascending=False).head(top_n)
    return [
        {"day": row.day_of_week, "hour": int(row.hour), "revenue": round(float(row.revenue), 2)}
        for row in top.itertuples()
    ]


def get_top_items():
    df = load_sales()
    df["period"] = df["day_of_week"].apply(lambda day: "weekend" if day in ["Saturday", "Sunday"] else "weekday")
    totals = df.groupby(["period", "item_name"], as_index=False)["revenue"].sum()
    result = {"weekday": [], "weekend": []}
    for period in result:
        rows = totals[totals["period"] == period].sort_values("revenue", ascending=False).head(5)
        result[period] = [
            {"item_name": row.item_name, "revenue": round(float(row.revenue), 2)}
            for row in rows.itertuples()
        ]
    return result


def get_overstaffing_alerts(target_labor_pct=0.30):
    df = load_sales()
    hour_totals = df.groupby(["date", "day_of_week", "hour"], as_index=False)["revenue"].sum()
    hourly = hour_totals.groupby(["day_of_week", "hour"], as_index=False)["revenue"].mean()
    alerts = []
    assumed_labor = 3 * 15
    for row in hourly.itertuples():
        labor_pct = assumed_labor / max(float(row.revenue), 1)
        if labor_pct > target_labor_pct and row.hour <= 11:
            alerts.append(
                {
                    "day": row.day_of_week,
                    "hour": int(row.hour),
                    "revenue": round(float(row.revenue), 2),
                    "labor_pct": round(labor_pct * 100, 1),
                    "recommendation": "Reduce staffing by 1 unless a specialty order is expected.",
                }
            )
    return sorted(alerts, key=lambda item: item["labor_pct"], reverse=True)[:8]


def get_summary(labor_summary=None):
    daily = get_daily_revenue()
    busiest = get_busiest_periods(1)[0]
    alerts = get_overstaffing_alerts()
    avg_daily = sum(item["revenue"] for item in daily) / max(len(daily), 1)
    labor_cost = labor_summary["weekly"]["labor_cost"] if labor_summary else 0
    return {
        "avg_daily_revenue": round(avg_daily, 2),
        "peak_hour": f"{busiest['day']} {busiest['hour']}:00",
        "peak_hour_revenue": busiest["revenue"],
        "labor_this_week": round(labor_cost, 2),
        "overstaffed_hours": len(alerts),
        "forecast": forecast_next_week(),
    }
