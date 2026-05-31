import { describe, expect, it } from "vitest";
import { validateCartStock } from "../../../frontend/src/utils/validateCartStock.js";

describe("validateCartStock", () => {
  const products = [
    { id: 1, name: "Widget", quantity: 10 },
    { id: 2, name: "Gadget", quantity: 0 },
    { id: 3, name: "Gizmo", quantity: 2 },
  ];

  it("returns ok when all cart lines are in stock", () => {
    const cart = [{ product_id: 1, name: "Widget", quantity: 3 }];
    expect(validateCartStock(cart, products)).toEqual({ ok: true });
  });

  it("flags products that no longer exist", () => {
    const cart = [{ product_id: 99, name: "Missing", quantity: 1 }];
    const result = validateCartStock(cart, products);
    expect(result.ok).toBe(false);
    expect(result.issues).toContain("Missing: no longer available.");
  });

  it("flags out-of-stock products", () => {
    const cart = [{ product_id: 2, name: "Gadget", quantity: 1 }];
    const result = validateCartStock(cart, products);
    expect(result.ok).toBe(false);
    expect(result.issues).toContain("Gadget: out of stock.");
  });

  it("flags quantities exceeding available stock", () => {
    const cart = [{ product_id: 3, name: "Gizmo", quantity: 5 }];
    const result = validateCartStock(cart, products);
    expect(result.ok).toBe(false);
    expect(result.issues[0]).toBe(
      "Gizmo: only 2 in stock (cart has 5)."
    );
  });

  it("collects multiple issues across cart lines", () => {
    const cart = [
      { product_id: 2, name: "Gadget", quantity: 1 },
      { product_id: 3, name: "Gizmo", quantity: 5 },
    ];
    const result = validateCartStock(cart, products);
    expect(result.ok).toBe(false);
    expect(result.issues).toHaveLength(2);
  });
});
