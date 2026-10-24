import os
from collections.abc import Generator
from datetime import date, timedelta
import random

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

load_dotenv()


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    category: Mapped[str]
    unit_price: Mapped[float]
    unit_cost: Mapped[float]
    stock: Mapped[int]
    reorder_point: Mapped[int]
    lead_days: Mapped[int]


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(index=True)
    sold_on: Mapped[date] = mapped_column(index=True)
    units: Mapped[int]


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./opspulse.db")
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def initialize_database() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        existing = session.scalar(select(func.count()).select_from(Product))
        if existing:
            return

        products = [
            Product(name="Everyday Backpack", category="Accessories", unit_price=64, unit_cost=29, stock=42, reorder_point=20, lead_days=7),
            Product(name="Insulated Bottle", category="Accessories", unit_price=28, unit_cost=9, stock=13, reorder_point=18, lead_days=8),
            Product(name="Desk Lamp", category="Home & Office", unit_price=49, unit_cost=21, stock=31, reorder_point=12, lead_days=10),
            Product(name="Wireless Mouse", category="Electronics", unit_price=39, unit_cost=16, stock=8, reorder_point=15, lead_days=6),
            Product(name="Ceramic Planter", category="Home & Office", unit_price=34, unit_cost=12, stock=54, reorder_point=16, lead_days=12),
            Product(name="Cable Organizer Set", category="Electronics", unit_price=18, unit_cost=5, stock=25, reorder_point=14, lead_days=5),
            Product(name="Travel Mug", category="Accessories", unit_price=32, unit_cost=11, stock=11, reorder_point=14, lead_days=8),
            Product(name="Notebook Set", category="Stationery", unit_price=22, unit_cost=7, stock=63, reorder_point=20, lead_days=5),
        ]
        session.add_all(products)
        session.flush()

        rng = random.Random(23)
        today = date.today()
        sales = []
        for product_index, product in enumerate(products):
            daily_baseline = [5.4, 7.2, 3.7, 6.4, 3.2, 8.1, 5.1, 4.3][product_index]
            for day_index in range(180):
                sold_on = today - timedelta(days=179 - day_index)
                weekend_factor = 1.18 if sold_on.weekday() >= 5 else 1
                growth_factor = 0.76 + day_index * 0.003
                seasonal_factor = 1 + 0.12 * (1 if day_index % 7 in (4, 5) else 0)
                campaign_factor = 2.4 if day_index in (50, 120, 160) else 1
                spike_factor = 2.8 if product_index == 3 and day_index in (32, 67) else 1
                noise = rng.uniform(0.65, 1.35)
                units = max(
                    1,
                    round(
                        daily_baseline
                        * weekend_factor
                        * growth_factor
                        * seasonal_factor
                        * campaign_factor
                        * spike_factor
                        * noise
                    ),
                )
                sales.append(Sale(product_id=product.id, sold_on=sold_on, units=units))

        session.add_all(sales)
        session.commit()
