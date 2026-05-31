import { describe, expect, it } from "vitest";
import { buildInsights } from "../../../frontend/src/utils/buildInsights.js";

describe("buildInsights", () => {
  const products = [
    { id: 1, name: "Widget", price: 100, quantity: 3, category: "tools" },
    { id: 2, name: "Gadget", price: 50, quantity: 20, category: "tools" },
    { id: 3, name: "Gizmo", price: 25, quantity: 5, category: "misc" },
  ];

  const today = new Date();
  today.setHours(12, 0, 0, 0);
  const todayIso = today.toISOString();

  const orders = [
    {
      id: 1,
      status: "delivered",
      total_amount: 200,
      created_at: todayIso,
      items: [
        { product_id: 1, product_name: "Widget", quantity: 2, unit_price: 100 },
      ],
    },
    {
      id: 2,
      status: "cancelled",
      total_amount: 999,
      created_at: todayIso,
      items: [
        { product_id: 2, product_name: "Gadget", quantity: 1, unit_price: 50 },
      ],
    },
    {
      id: 3,
      status: "pending",
      total_amount: 50,
      created_at: todayIso,
      items: [
        { product_id: 2, product_name: "Gadget", quantity: 1, unit_price: 50 },
      ],
    },
  ];

  it("computes inventory summary metrics", () => {
    const insights = buildInsights(products, orders);
    expect(insights.summary.total_products).toBe(3);
    expect(insights.summary.total_stock).toBe(28);
    expect(insights.summary.inventory_value).toBe(1425);
    expect(insights.summary.total_orders).toBe(3);
    expect(insights.summary.pending_orders).toBe(1);
  });

  it("excludes cancelled orders from revenue totals", () => {
    const insights = buildInsights(products, orders);
    expect(insights.summary.total_revenue).toBe(250);
  });

  it("flags low-stock products at or below threshold", () => {
    const insights = buildInsights(products, orders);
    expect(insights.summary.low_stock_count).toBe(2);
    expect(insights.low_stock.map((p) => p.id)).toEqual([1, 3]);
  });

  it("aggregates top products by quantity sold", () => {
    const insights = buildInsights(products, orders);
    expect(insights.top_products[0]).toMatchObject({
      product_id: 1,
      name: "Widget",
      quantity_sold: 2,
      revenue: 200,
    });
  });

  it("builds inventory value by category", () => {
    const insights = buildInsights(products, orders);
    const tools = insights.inventory_by_category.find((c) => c.category === "tools");
    expect(tools.value).toBe(1300);
  });

  it("includes order counts per status", () => {
    const insights = buildInsights(products, orders);
    expect(insights.orders_by_status).toEqual(
      expect.arrayContaining([
        { status: "delivered", count: 1 },
        { status: "cancelled", count: 1 },
        { status: "pending", count: 1 },
      ])
    );
  });
});
