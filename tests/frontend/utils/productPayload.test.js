import { describe, expect, it } from "vitest";
import {
  productToForm,
  toProductWrite,
} from "../../../frontend/src/utils/productPayload.js";

describe("productToForm", () => {
  it("maps API product fields to form defaults", () => {
    expect(
      productToForm({
        name: "Widget",
        sku: "W-1",
        description: "A widget",
        price: 19.99,
        quantity: 5,
        category: "tools",
        image_url: "http://example.com/w.png",
      })
    ).toEqual({
      name: "Widget",
      sku: "W-1",
      description: "A widget",
      price: 19.99,
      quantity: 5,
      category: "tools",
      image_url: "http://example.com/w.png",
    });
  });

  it("fills missing fields with safe defaults", () => {
    expect(productToForm({})).toEqual({
      name: "",
      sku: "",
      description: "",
      price: 0,
      quantity: 0,
      category: "general",
      image_url: "",
    });
  });
});

describe("toProductWrite", () => {
  it("builds a trimmed ProductWrite payload", () => {
    expect(
      toProductWrite({
        name: "  Widget  ",
        sku: " W-1 ",
        description: "Desc",
        price: "19.999",
        quantity: "4",
        category: "",
        image_url: "",
      })
    ).toEqual({
      name: "Widget",
      sku: "W-1",
      description: "Desc",
      price: 20,
      quantity: 4,
      category: "general",
      image_url: "",
    });
  });

  it("throws for invalid price", () => {
    expect(() =>
      toProductWrite({
        name: "X",
        sku: "X",
        price: "bad",
        quantity: "1",
      })
    ).toThrow(/valid price/i);
  });

  it("throws for invalid quantity", () => {
    expect(() =>
      toProductWrite({
        name: "X",
        sku: "X",
        price: "10",
        quantity: "-1",
      })
    ).toThrow(/valid quantity/i);
  });
});
