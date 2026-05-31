export function productToForm(product) {
  return {
    name: product.name ?? "",
    sku: product.sku ?? "",
    description: product.description ?? "",
    price: product.price ?? 0,
    quantity: product.quantity ?? 0,
    category: product.category ?? "general",
    image_url: product.image_url ?? "",
  };
}

/**
 * Build a body that matches backend ProductWrite (no id/timestamps).
 */
export function toProductWrite(form) {
  const price = roundPrice(parseFloat(form.price));
  const quantity = parseInt(form.quantity, 10);

  if (Number.isNaN(price) || price < 0) {
    throw new Error("Enter a valid price (max 2 decimal places).");
  }
  if (Number.isNaN(quantity) || quantity < 0) {
    throw new Error("Enter a valid quantity (0 or more).");
  }

  return {
    name: String(form.name ?? "").trim(),
    description: String(form.description ?? ""),
    sku: String(form.sku ?? "").trim(),
    price,
    quantity,
    category: String(form.category ?? "").trim() || "general",
    image_url: String(form.image_url ?? ""),
  };
}

function roundPrice(value) {
  if (Number.isNaN(value)) return NaN;
  return Math.round(value * 100) / 100;
}
