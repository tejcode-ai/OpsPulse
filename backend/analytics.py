from datetime import date, timedelta
from typing import Any

import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import Product, Sale


def _money(value: float) -> float:
    return round(float(value), 2)


def build_dashboard(session: Session, days: int = 30) -> dict[str, Any]:
    today = date.today()
    start = today - timedelta(days=days - 1)
    previous_start = start - timedelta(days=days)
    products = session.scalars(select(Product).order_by(Product.name)).all()
    sales = session.scalars(
        select(Sale).where(Sale.sold_on >= previous_start, Sale.sold_on <= today)
    ).all()
    product_by_id = {product.id: product for product in products}

    records = [
        {
            "date": sale.sold_on,
            "product_id": sale.product_id,
            "units": sale.units,
            "revenue": sale.units * product_by_id[sale.product_id].unit_price,
            "profit": sale.units
            * (product_by_id[sale.product_id].unit_price - product_by_id[sale.product_id].unit_cost),
        }
        for sale in sales
        if sale.product_id in product_by_id
    ]
    frame = pd.DataFrame(records)
    if frame.empty:
        frame = pd.DataFrame(columns=["date", "product_id", "units", "revenue", "profit"])
    frame["date"] = pd.to_datetime(frame["date"])

    current = frame[frame["date"].dt.date >= start]
    previous = frame[frame["date"].dt.date < start]
    revenue = float(current["revenue"].sum())
    previous_revenue = float(previous["revenue"].sum())
    profit = float(current["profit"].sum())

    daily = (
        current.groupby(current["date"].dt.date)["revenue"]
        .sum()
        .reindex([start + timedelta(days=i) for i in range(days)], fill_value=0)
    )
    trend = [
        {"date": day.isoformat(), "revenue": _money(value)}
        for day, value in daily.items()
    ]

    product_sales = current.groupby("product_id")["units"].sum().to_dict()
    best_sellers = sorted(
        [
            {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "units_sold": int(product_sales.get(product.id, 0)),
                "revenue": _money(product_sales.get(product.id, 0) * product.unit_price),
            }
            for product in products
        ],
        key=lambda product: (-product["units_sold"], product["name"]),
    )

    low_stock = []
    for product in products:
        units_sold = int(product_sales.get(product.id, 0))
        daily_rate = units_sold / days
        suggested_stock = max(product.reorder_point * 2, round(daily_rate * product.lead_days * 1.5))
        if product.stock <= product.reorder_point:
            low_stock.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "stock": product.stock,
                    "reorder_point": product.reorder_point,
                    "suggested_restock": max(0, suggested_stock - product.stock),
                    "daily_units": round(daily_rate, 1),
                    "lead_days": product.lead_days,
                }
            )

    median = float(daily.median()) if len(daily) else 0
    mad = float((daily - median).abs().median()) if len(daily) else 0
    scale = 1.4826 * mad
    if scale == 0 and len(daily) > 1:
        scale = float(daily.std(ddof=0))
    anomalies = []
    if scale > 0:
        for day, amount in daily.items():
            deviation = (float(amount) - median) / scale
            if abs(deviation) >= 3.5:
                anomalies.append(
                    {
                        "date": day.isoformat(),
                        "revenue": _money(amount),
                        "baseline": _money(median),
                        "direction": "above" if deviation > 0 else "below",
                    }
                )

    recent_values = daily.tail(min(30, len(daily))).to_numpy(dtype=float)
    forecast = []
    if len(recent_values) >= 7:
        x_values = list(range(len(recent_values)))
        model = LinearRegression().fit(
            pd.DataFrame({"day": x_values}), recent_values
        )
        future_x = pd.DataFrame({"day": range(len(recent_values), len(recent_values) + 7)})
        for offset, amount in enumerate(model.predict(future_x), start=1):
            forecast.append(
                {
                    "date": (today + timedelta(days=offset)).isoformat(),
                    "revenue": _money(max(0, amount)),
                }
            )

    change_pct = (
        round((revenue - previous_revenue) / previous_revenue * 100, 1)
        if previous_revenue
        else None
    )
    return {
        "period_days": days,
        "kpis": {
            "revenue": _money(revenue),
            "profit": _money(profit),
            "units_sold": int(current["units"].sum()) if not current.empty else 0,
            "revenue_change_pct": change_pct,
            "previous_revenue": _money(previous_revenue),
        },
        "trend": trend,
        "forecast": forecast,
        "best_sellers": best_sellers[:6],
        "low_stock": low_stock,
        "anomalies": anomalies,
        "generated_at": today.isoformat(),
    }
