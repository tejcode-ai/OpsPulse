from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.analytics import build_dashboard
from backend.database import Base, Product, Sale


def test_dashboard_calculates_kpis_trends_and_recommendations() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    today = date.today()
    with Session(engine) as session:
        product = Product(
            name="Test bottle",
            category="Accessories",
            unit_price=10,
            unit_cost=4,
            stock=3,
            reorder_point=5,
            lead_days=4,
        )
        session.add(product)
        session.flush()
        for offset in range(30):
            session.add(
                Sale(
                    product_id=product.id,
                    sold_on=today - timedelta(days=29 - offset),
                    units=2,
                )
            )
        session.commit()

        result = build_dashboard(session, 30)

    assert result["kpis"]["units_sold"] == 60
    assert result["kpis"]["revenue"] == 600
    assert result["kpis"]["profit"] == 360
    assert len(result["trend"]) == 30
    assert len(result["forecast"]) == 7
    assert result["low_stock"][0]["suggested_restock"] > 0


def test_dashboard_rejects_unseeded_productless_sales_cleanly() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        result = build_dashboard(session, 7)

    assert result["kpis"]["revenue"] == 0
    assert result["best_sellers"] == []


def test_dashboard_flags_an_outlier_when_median_deviation_is_zero() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    today = date.today()
    with Session(engine) as session:
        product = Product(
            name="Test notebook",
            category="Stationery",
            unit_price=10,
            unit_cost=4,
            stock=50,
            reorder_point=10,
            lead_days=4,
        )
        session.add(product)
        session.flush()
        for offset in range(30):
            session.add(
                Sale(
                    product_id=product.id,
                    sold_on=today - timedelta(days=29 - offset),
                    units=20 if offset == 25 else 2,
                )
            )
        session.commit()

        result = build_dashboard(session, 30)

    assert len(result["anomalies"]) == 1
    assert result["anomalies"][0]["date"] == (today - timedelta(days=4)).isoformat()
