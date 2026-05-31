/**
 * Check cart lines against live product list before checkout.
 * @returns {{ ok: true } | { ok: false, issues: string[] }}
 */
export function validateCartStock(cartItems, products) {
  const byId = new Map(products.map((p) => [p.id, p]));
  const issues = [];

  for (const item of cartItems) {
    const product = byId.get(item.product_id);
    if (!product) {
      issues.push(`${item.name}: no longer available.`);
      continue;
    }
    if (product.quantity === 0) {
      issues.push(`${item.name}: out of stock.`);
      continue;
    }
    if (item.quantity > product.quantity) {
      issues.push(
        `${item.name}: only ${product.quantity} in stock (cart has ${item.quantity}).`
      );
    }
  }

  if (issues.length > 0) {
    return { ok: false, issues };
  }
  return { ok: true };
}
