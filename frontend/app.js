const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const number = new Intl.NumberFormat("en-US");

const byId = (id) => document.getElementById(id);
let toastTimer;

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function shortDate(isoDate, includeDay = false) {
  const date = new Date(`${isoDate}T12:00:00`);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: includeDay ? "numeric" : undefined,
  }).format(date);
}

function showToast(message) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 3200);
}

function renderChart(trend, forecast) {
  const container = byId("chart-container");
  const actual = trend || [];
  const future = forecast || [];
  if (!actual.length) {
    container.innerHTML = '<div class="chart-loading">No sales data is available for this period.</div>';
    return;
  }

  const width = 720;
  const height = 130;
  const pad = { left: 40, right: 8, top: 8, bottom: 22 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const allValues = actual.map((item) => item.revenue).concat(future.map((item) => item.revenue));
  const maxValue = Math.max(...allValues, 1) * 1.15;
  const point = (index, value, count) => ({
    x: pad.left + (count <= 1 ? plotWidth / 2 : (index / (count - 1)) * plotWidth),
    y: pad.top + plotHeight - (value / maxValue) * plotHeight,
  });
  const formatAxis = (amount) => amount >= 1000
    ? `$${(amount / 1000).toFixed(amount >= 10000 ? 0 : 1)}k`
    : `$${Math.round(amount)}`;
  const tickValues = [0, maxValue / 2, maxValue];
  const grid = tickValues.map((tick) => {
    const y = pad.top + plotHeight - (tick / maxValue) * plotHeight;
    return `<line x1="${pad.left}" y1="${y}" x2="${width - pad.right}" y2="${y}" stroke="#eef0f3" stroke-dasharray="3 4"/><text x="${pad.left - 7}" y="${y + 3}" text-anchor="end" fill="#a3a9b1" font-size="9">${formatAxis(tick)}</text>`;
  }).join("");
  const actualPoints = actual.map((item, index) => point(index, item.revenue, actual.length));
  const forecastPoints = future.map((item, index) => point(actual.length + index, item.revenue, actual.length + future.length));
  const line = (points) => points.map((p, index) => `${index ? "L" : "M"}${p.x},${p.y}`).join(" ");
  const first = actualPoints[0];
  const last = actualPoints[actualPoints.length - 1];
  const areaPath = `${line(actualPoints)} L${last.x},${pad.top + plotHeight} L${first.x},${pad.top + plotHeight} Z`;
  const xLabels = [0, Math.floor((actual.length - 1) / 3), Math.floor((actual.length - 1) * 2 / 3), actual.length - 1];
  const labels = [...new Set(xLabels)].map((index) => {
    const p = actualPoints[index];
    const anchor = index === 0 ? "start" : index === actual.length - 1 ? "end" : "middle";
    return `<text x="${p.x}" y="${height - 3}" text-anchor="${anchor}" fill="#a0a6ae" font-size="9">${escapeHtml(shortDate(actual[index].date, true))}</text>`;
  }).join("");
  const interval = Math.max(1, Math.floor(actual.length / 12));
  const points = actualPoints.map((p, index) => ({ point: p, index }))
    .filter(({ index }) => index % interval === 0 || index === actual.length - 1)
    .map(({ point: p, index }) => `<circle cx="${p.x}" cy="${p.y}" r="2.4" fill="#fff" stroke="#5483e8" stroke-width="1.5"><title>${escapeHtml(actual[index].date)} · ${currency.format(actual[index].revenue)}</title></circle>`)
    .join("");
  const forecastLine = future.length
    ? `<path d="M${last.x},${last.y} ${line(forecastPoints).replace(/^M/, "L")}" fill="none" stroke="#8b9bb9" stroke-width="2" stroke-dasharray="5 4" stroke-linecap="round" stroke-linejoin="round"/>`
    : "";
  const forecastDots = forecastPoints.map((p, index) => `<circle cx="${p.x}" cy="${p.y}" r="2.2" fill="#fff" stroke="#8b9bb9" stroke-width="1.4"><title>${escapeHtml(future[index].date)} · forecast ${currency.format(future[index].revenue)}</title></circle>`).join("");
  container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Daily revenue chart with a seven-day forecast">${grid}<path d="${areaPath}" fill="url(#revenue-fill)" opacity=".55"/><defs><linearGradient id="revenue-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#80a3f1" stop-opacity=".28"/><stop offset="100%" stop-color="#80a3f1" stop-opacity="0"/></linearGradient></defs><path d="${line(actualPoints)}" fill="none" stroke="#5483e8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>${forecastLine}${points}${forecastDots}${labels}</svg>`;
}

function renderProducts(products) {
  const container = byId("best-sellers");
  if (!products.length) {
    container.innerHTML = '<div class="chart-loading">No product sales for this period.</div>';
    return;
  }
  container.innerHTML = products.map((product, index) => `
    <div class="product-row">
      <span class="product-rank">${String(index + 1).padStart(2, "0")}</span>
      <span class="product-info"><span class="product-name">${escapeHtml(product.name)}</span><span class="product-category">${escapeHtml(product.category)}</span></span>
      <span class="product-units">${number.format(product.units_sold)} units<small>${currency.format(product.revenue)}</small></span>
    </div>`).join("");
}

function renderInventory(products) {
  byId("nav-stock-count").textContent = products.length;
  byId("stock-badge").textContent = products.length
    ? `${products.length} low-stock item${products.length === 1 ? "" : "s"}`
    : "All stocked";
  const rows = products.length
    ? products.map((product) => `
      <tr>
        <td class="stock-product">${escapeHtml(product.name)}</td>
        <td class="stock-amount">${number.format(product.stock)} units</td>
        <td><span class="stock-status low"><i class="status-dot"></i>Low stock</span></td>
        <td class="restock-qty">${number.format(product.suggested_restock)} units</td>
      </tr>`).join("")
    : '<tr><td colspan="4" class="table-loading">No products are below their reorder point.</td></tr>';
  byId("inventory-rows").innerHTML = rows;
}

function renderSignals(data) {
  const signals = [];
  if (data.kpis.revenue_change_pct !== null) {
    const change = data.kpis.revenue_change_pct;
    const direction = change >= 0 ? "up" : "down";
    signals.push({
      type: change >= 0 ? "positive" : "warning",
      icon: change >= 0 ? "↗" : "↘",
      text: `<strong>Revenue ${direction} ${Math.abs(change)}%</strong> compared with the previous ${data.period_days}-day period.`,
    });
  }
  if (data.anomalies.length) {
    const spike = data.anomalies[0];
    signals.push({
      type: "warning",
      icon: "!",
      text: `<strong>Unusual sales on ${escapeHtml(shortDate(spike.date, true))}.</strong> Daily revenue was ${spike.direction} its typical baseline (${currency.format(spike.revenue)} vs. ${currency.format(spike.baseline)}).`,
    });
  } else {
    signals.push({
      type: "positive",
      icon: "✓",
      text: "<strong>No unusual revenue spikes found.</strong> The recent daily sales pattern stayed within its typical range.",
    });
  }
  if (data.low_stock.length) {
    const first = data.low_stock[0];
    signals.push({
      type: "warning",
      icon: "↗",
      text: `<strong>${data.low_stock.length} ${data.low_stock.length === 1 ? "product is" : "products are"} below reorder point.</strong> ${escapeHtml(first.name)} is at ${first.stock} units.`,
    });
  } else {
    signals.push({
      type: "positive",
      icon: "✓",
      text: "<strong>Inventory is above reorder points.</strong> No immediate stock alerts.",
    });
  }
  byId("business-signals").innerHTML = signals.map((signal) => `
    <div class="signal"><span class="signal-icon ${signal.type}">${signal.icon}</span><span class="signal-copy">${signal.text}</span></div>`).join("");
}

function updateSummary(data) {
  const { revenue_change_pct: change } = data.kpis;
  if (data.low_stock.length) {
    const first = data.low_stock[0];
    byId("insight-title").textContent = `${data.low_stock.length} product${data.low_stock.length === 1 ? "" : "s"} may need a restock.`;
    byId("insight-text").textContent = `${first.name} has ${first.stock} units on hand; suggested order: ${number.format(first.suggested_restock)} units.`;
  } else if (change !== null) {
    byId("insight-title").textContent = `Revenue ${change >= 0 ? "grew" : "declined"} ${Math.abs(change)}% vs. the previous period.`;
    byId("insight-text").textContent = `${data.anomalies.length} unusual revenue ${data.anomalies.length === 1 ? "day was" : "days were"} flagged for a closer look.`;
  }
}

async function loadDashboard() {
  const days = byId("period-select").value;
  byId("chart-container").innerHTML = '<div class="chart-loading">Loading revenue data…</div>';
  try {
    const response = await fetch(`/api/dashboard?days=${encodeURIComponent(days)}`);
    if (!response.ok) throw new Error(`Dashboard request failed (${response.status}).`);
    const data = await response.json();
    byId("kpi-revenue").textContent = currency.format(data.kpis.revenue);
    byId("kpi-profit").textContent = currency.format(data.kpis.profit);
    byId("kpi-units").textContent = number.format(data.kpis.units_sold);
    byId("kpi-attention").textContent = data.low_stock.length;
    byId("attention-caption").textContent = data.low_stock.length
      ? `${data.low_stock.length} product${data.low_stock.length === 1 ? "" : "s"} below reorder point`
      : "All products above reorder point";
    const change = data.kpis.revenue_change_pct;
    const changeElement = byId("revenue-change");
    changeElement.classList.toggle("down", change !== null && change < 0);
    changeElement.textContent = change === null
      ? "No comparison"
      : `${change >= 0 ? "+" : ""}${change}%`;
    byId("profit-margin").textContent = data.kpis.revenue
      ? `${Math.round(data.kpis.profit / data.kpis.revenue * 100)}%`
      : "—";
    byId("chart-revenue").textContent = currency.format(data.kpis.revenue);
    byId("chart-period").textContent = `last ${data.period_days} days`;
    renderChart(data.trend, data.forecast);
    renderProducts(data.best_sellers);
    renderInventory(data.low_stock);
    renderSignals(data);
    updateSummary(data);
  } catch (error) {
    byId("chart-container").innerHTML = '<div class="chart-loading">Unable to load dashboard data.</div>';
    showToast(error.message || "Could not load dashboard data. Check that the server is running.");
  }
}

async function requestAI(url, question) {
  const button = byId("ask-button");
  const answer = byId("ai-answer");
  const requestUrl = `${url}?days=${encodeURIComponent(byId("period-select").value)}`;
  answer.hidden = false;
  answer.classList.remove("error");
  answer.textContent = "Reviewing your computed dashboard metrics…";
  button.disabled = true;
  try {
    const response = await fetch(requestUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: question ? JSON.stringify({ question }) : undefined,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "The AI request could not be completed.");
    answer.textContent = result.answer;
  } catch (error) {
    answer.classList.add("error");
    answer.textContent = error.message || "The AI request failed. Please try again.";
  } finally {
    button.disabled = false;
  }
}

byId("period-select").addEventListener("change", loadDashboard);
byId("refresh-button").addEventListener("click", loadDashboard);
byId("summary-button").addEventListener("click", () => requestAI("/api/ai/summary"));
byId("question-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const question = byId("question-input").value.trim();
  if (question.length >= 3) requestAI("/api/ai/ask", question);
});
document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    byId("question-input").value = button.textContent;
    byId("question-form").requestSubmit();
  });
});
loadDashboard();
