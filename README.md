# OpsPulse

OpsPulse is a small, portfolio-ready business analytics app. It turns sales and inventory records into a live dashboard, then offers an optional Claude explanation of those **computed** results.

## What works in this version

- Revenue, gross profit, units sold, and revenue change compared with the previous period.
- Best-selling products and low-stock alerts, including a suggested restock amount based on recent sales and supplier lead time.
- Daily revenue charts, unusual-day flags using a robust median-deviation rule, and a seven-day linear-regression forecast.
- An optional Claude summary and question box. The model receives aggregates and product summaries from the dashboard—not raw database rows. The Python calculations remain the source of truth.
- Eight products and 180 days of reproducible sample sales data, initialized automatically in the database on first run. The extra history allows the 90-day view to compare two complete periods.
- SQLite works out of the box. PostgreSQL is supported by changing `DATABASE_URL`.

The sample catalog uses USD. The generated sample data is for demonstration only; forecasts are directional estimates, not guarantees. An unusual sales pattern signals something to investigate—it does not establish why it happened.

## Run it on Windows

Use Python 3.11 or newer. From this project folder, run these commands in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn backend.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). FastAPI's interactive API docs are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

On first launch, OpsPulse creates `opspulse.db` in the project folder and inserts sample records. It does not replace data in a database that already has products. To start over with the sample database, stop the server, delete that specific `opspulse.db` file, and restart.

## Enable the Claude feature (optional)

The dashboard and analytics work without a model key. To enable the AI summary and dashboard Q&A:

1. Create an Anthropic API key in your Anthropic account.
2. Add `ANTHROPIC_API_KEY=your-key` to your local `.env` file. Do not paste the key into source code, the browser, screenshots, or version control.
3. Restart the server and use **Get AI summary** or **Ask OpsPulse**.

The key stays on the server. The browser calls this app's API; only the backend calls Anthropic. Requests have a 15-second timeout, a 400-token response cap, a 500-character question limit, and a shared 20-request daily cap in the running application process. Provider errors and missing or invalid keys are reported clearly. Anthropic API usage may incur charges; check current provider pricing and configure spending limits in your Anthropic account. The in-memory cap resets if the server restarts and does not coordinate across multiple server processes. Do not expose this demo publicly without authentication, a persistent shared rate limit, and deployment-specific secret management.

When AI is enabled, computed KPIs, daily revenue totals, best sellers, low-stock summaries, anomalies, and forecasts are sent to Anthropic to generate the answer. Raw sales rows, credentials, and personal data are not intentionally included. Review your data-handling requirements and the provider's current retention terms before using real business data.

## PostgreSQL

SQLite is the default so a new developer can run the project without installing a database server. To use PostgreSQL, create a database, then change `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/opspulse
```

The application uses SQLAlchemy, so the same models work with SQLite and PostgreSQL. For production, use a database migration tool such as Alembic rather than relying on `create_all`, configure credentials through your deployment's secret manager, and add authentication and backups.

## Project map

```text
backend/
  ai.py          Optional, bounded Claude API integration
  analytics.py   Pandas calculations, anomaly flags, and sklearn forecast
  database.py    SQLAlchemy models, database setup, sample data
  main.py        FastAPI endpoints and static web app
frontend/
  index.html     Dashboard structure and labels
  styles.css     Responsive visual design
  app.js         API calls, dashboard rendering, and chart
tests/
  test_analytics.py
.env.example     Safe configuration template; copy to .env
requirements.txt Python dependencies
```

## API and checks

- `GET /api/health` — basic health check.
- `GET /api/dashboard?days=30` — computed dashboard data (`days` can be 7–90).
- `POST /api/ai/summary?days=30` — Claude explanation of computed dashboard context.
- `POST /api/ai/ask?days=30` — Claude answer to a short question, grounded in computed metrics.

Run the analytics tests with:

```powershell
python -m pytest
```

## Design and interview notes

- **FastAPI** serves JSON and the web dashboard from one local server.
- **SQLAlchemy** keeps database access consistent; SQLite is the convenient local default, while PostgreSQL is ready for a shared deployment.
- **Pandas** groups sales by day and product. Revenue and profit are computed from units and the catalog's price/cost.
- **Scikit-learn `LinearRegression`** projects the next seven daily revenue values using recent days. A linear model is intentionally simple and should not be presented as a reliable financial guarantee.
- **Robust median deviation** flags unusually high or low daily revenue without claiming a cause.
- **Claude** explains the calculated output; it does not calculate the KPIs. The key is server-side, the question and AI output are bounded, and provider failures are visible to the user.

For a next iteration, replace seeded records with validated CSV imports, add product and sales management, then introduce database migrations and user authentication before deploying with real data.
