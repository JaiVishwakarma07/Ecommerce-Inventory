import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";
import { fetchInsightsData } from "../utils/buildInsights.js";
import { formatINR, formatNumber } from "../utils/format.js";

const STATUS_COLORS = {
  pending: "#d97706",
  processing: "#2563eb",
  shipped: "#0891b2",
  delivered: "#16a34a",
  cancelled: "#dc2626",
};

const CATEGORY_COLORS = [
  "#4f46e5",
  "#0891b2",
  "#16a34a",
  "#d97706",
  "#dc2626",
  "#7c3aed",
  "#db2777",
];

function StatCard({ label, value, accent }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
    </div>
  );
}

function ChartCard({ title, subtitle, children, height = 280 }) {
  return (
    <div className="card chart-card">
      <div className="chart-head">
        <h3>{title}</h3>
        {subtitle && <p className="muted small">{subtitle}</p>}
      </div>
      <div style={{ width: "100%", height }}>{children}</div>
    </div>
  );
}

export default function AdminInsights() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    fetchInsightsData(api)
      .then(setData)
      .catch((err) =>
        setError(formatApiError(err, "Failed to load insights"))
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <div className="muted">Loading insights...</div>;
  if (error) return <div className="alert error">{error}</div>;
  if (!data) return null;

  const { summary, orders_by_status, orders_over_time, top_products, inventory_by_category, low_stock } = data;

  const statusData = orders_by_status.filter((s) => s.count > 0);
  const timeData = orders_over_time.map((d) => ({
    ...d,
    label: new Date(d.date).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
    }),
  }));

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Insights</h1>
          <p className="muted">
            Inventory health and order performance (latest 100 products and
            orders).
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load}>
          Refresh
        </button>
      </div>

      <div className="stat-grid">
        <StatCard label="Products" value={formatNumber(summary.total_products)} />
        <StatCard label="Total Stock" value={formatNumber(summary.total_stock)} />
        <StatCard
          label="Inventory Value"
          value={formatINR(summary.inventory_value)}
        />
        <StatCard label="Orders" value={formatNumber(summary.total_orders)} />
        <StatCard
          label="Revenue"
          value={formatINR(summary.total_revenue)}
          accent="#16a34a"
        />
        <StatCard
          label="Pending Orders"
          value={formatNumber(summary.pending_orders)}
          accent={summary.pending_orders > 0 ? "#d97706" : undefined}
        />
        <StatCard
          label="Low Stock Items"
          value={formatNumber(summary.low_stock_count)}
          accent={summary.low_stock_count > 0 ? "#dc2626" : undefined}
        />
      </div>

      <div className="chart-grid">
        <ChartCard
          title="Orders over time"
          subtitle="Last 14 days"
        >
          <ResponsiveContainer>
            <LineChart data={timeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `₹${v}`}
              />
              <Tooltip
                formatter={(value, name) =>
                  name === "Revenue" ? formatINR(value) : value
                }
              />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="orders"
                name="Orders"
                stroke="#4f46e5"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="revenue"
                name="Revenue"
                stroke="#16a34a"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Order status mix"
          subtitle="Distribution across all orders"
        >
          {statusData.length === 0 ? (
            <div className="empty small">No orders yet</div>
          ) : (
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={statusData}
                  dataKey="count"
                  nameKey="status"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={2}
                  label={(entry) => `${entry.status} (${entry.count})`}
                >
                  {statusData.map((s) => (
                    <Cell
                      key={s.status}
                      fill={STATUS_COLORS[s.status] || "#6b7280"}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard
          title="Top selling products"
          subtitle={`Best ${top_products.length} by quantity sold`}
        >
          {top_products.length === 0 ? (
            <div className="empty small">No sales yet</div>
          ) : (
            <ResponsiveContainer>
              <BarChart
                data={top_products}
                layout="vertical"
                margin={{ left: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={140}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  formatter={(value, name) =>
                    name === "Revenue" ? formatINR(value) : value
                  }
                />
                <Legend />
                <Bar
                  dataKey="quantity_sold"
                  name="Units sold"
                  fill="#4f46e5"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard
          title="Inventory by category"
          subtitle="Current stock value distribution"
        >
          <ResponsiveContainer>
            <BarChart data={inventory_by_category}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="category" tick={{ fontSize: 12 }} />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                formatter={(value, name) =>
                  name === "Inventory value" ? formatINR(value) : value
                }
              />
              <Legend />
              <Bar
                dataKey="value"
                name="Inventory value"
                radius={[4, 4, 0, 0]}
              >
                {inventory_by_category.map((entry, idx) => (
                  <Cell
                    key={entry.category}
                    fill={CATEGORY_COLORS[idx % CATEGORY_COLORS.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="card" style={{ marginTop: "1.25rem" }}>
        <h3>Low stock alerts</h3>
        <p className="muted small">
          Items with {summary.low_stock_threshold ?? 5} units or fewer in stock
        </p>
        {low_stock.length === 0 ? (
          <div className="empty small">All products are well stocked.</div>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Product</th>
                  <th>Category</th>
                  <th>Quantity</th>
                </tr>
              </thead>
              <tbody>
                {low_stock.map((p) => (
                  <tr key={p.id}>
                    <td>{p.sku}</td>
                    <td>{p.name}</td>
                    <td>{p.category}</td>
                    <td>
                      <span
                        className={`chip ${
                          p.quantity === 0 ? "chip-red" : "chip-amber"
                        }`}
                      >
                        {p.quantity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
