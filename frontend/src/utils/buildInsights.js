const LOW_STOCK_THRESHOLD = 5;
const TOP_PRODUCTS_LIMIT = 5;
const ORDERS_OVER_TIME_DAYS = 14;

const ORDER_STATUSES = [
  "pending",
  "processing",
  "shipped",
  "delivered",
  "cancelled",
];

function dateKey(isoString) {
  return isoString.slice(0, 10);
}

function lastNDays(n) {
  const days = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let i = n - 1; i >= 0; i -= 1) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  return days;
}

/**
 * Build insights dashboard shape from GET /products and GET /orders list responses.
 */
export function buildInsights(products, orders) {
  const lowStock = products
    .filter((p) => p.quantity <= LOW_STOCK_THRESHOLD)
    .sort((a, b) => a.quantity - b.quantity);

  const totalStock = products.reduce((sum, p) => sum + p.quantity, 0);
  const inventoryValue = products.reduce(
    (sum, p) => sum + p.price * p.quantity,
    0
  );

  const revenueOrders = orders.filter((o) => o.status !== "cancelled");
  const totalRevenue = revenueOrders.reduce(
    (sum, o) => sum + o.total_amount,
    0
  );
  const pendingOrders = orders.filter((o) => o.status === "pending").length;

  const ordersByStatus = ORDER_STATUSES.map((status) => ({
    status,
    count: orders.filter((o) => o.status === status).length,
  }));

  const dayBuckets = Object.fromEntries(
    lastNDays(ORDERS_OVER_TIME_DAYS).map((date) => [
      date,
      { date, orders: 0, revenue: 0 },
    ])
  );

  for (const order of orders) {
    const key = dateKey(order.created_at);
    if (!dayBuckets[key]) continue;
    dayBuckets[key].orders += 1;
    if (order.status !== "cancelled") {
      dayBuckets[key].revenue += order.total_amount;
    }
  }

  const ordersOverTime = Object.values(dayBuckets);

  const salesByProduct = new Map();
  for (const order of orders) {
    if (order.status === "cancelled") continue;
    for (const line of order.items || []) {
      const key = line.product_id;
      const existing = salesByProduct.get(key) || {
        product_id: line.product_id,
        name: line.product_name,
        quantity_sold: 0,
        revenue: 0,
      };
      existing.quantity_sold += line.quantity;
      existing.revenue += line.unit_price * line.quantity;
      salesByProduct.set(key, existing);
    }
  }

  const topProducts = [...salesByProduct.values()]
    .sort((a, b) => b.quantity_sold - a.quantity_sold)
    .slice(0, TOP_PRODUCTS_LIMIT);

  const categoryMap = new Map();
  for (const product of products) {
    const cat = product.category || "uncategorized";
    const prev = categoryMap.get(cat) || { category: cat, value: 0 };
    prev.value += product.price * product.quantity;
    categoryMap.set(cat, prev);
  }

  const inventoryByCategory = [...categoryMap.values()].sort(
    (a, b) => b.value - a.value
  );

  return {
    summary: {
      total_products: products.length,
      total_stock: totalStock,
      inventory_value: inventoryValue,
      total_orders: orders.length,
      total_revenue: totalRevenue,
      pending_orders: pendingOrders,
      low_stock_count: lowStock.length,
      low_stock_threshold: LOW_STOCK_THRESHOLD,
    },
    orders_by_status: ordersByStatus,
    orders_over_time: ordersOverTime,
    top_products: topProducts,
    inventory_by_category: inventoryByCategory,
    low_stock: lowStock,
  };
}

export async function fetchInsightsData(api) {
  const [productsRes, ordersRes] = await Promise.all([
    api.get("/products", { params: { limit: 100 } }),
    api.get("/orders", { params: { limit: 100 } }),
  ]);
  return buildInsights(productsRes.data, ordersRes.data);
}
