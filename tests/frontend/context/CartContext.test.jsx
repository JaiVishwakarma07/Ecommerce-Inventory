import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  CartProvider,
  useCart,
} from "../../../frontend/src/context/CartContext.jsx";

function CartProbe() {
  const { items, itemCount, total, addItem, updateQuantity, removeItem, clearCart } =
    useCart();

  return (
    <div>
      <span data-testid="count">{itemCount}</span>
      <span data-testid="total">{total}</span>
      <span data-testid="items">{JSON.stringify(items)}</span>
      <button
        type="button"
        onClick={() =>
          addItem(
            { id: 1, name: "Widget", price: 10, image_url: "" },
            2
          )
        }
      >
        add-widget
      </button>
      <button
        type="button"
        onClick={() =>
          addItem({ id: 2, name: "Gadget", price: 5, image_url: "" }, 1)
        }
      >
        add-gadget
      </button>
      <button type="button" onClick={() => updateQuantity(1, 5)}>
        bump-widget
      </button>
      <button type="button" onClick={() => updateQuantity(1, 0)}>
        zero-widget
      </button>
      <button type="button" onClick={() => removeItem(2)}>
        remove-gadget
      </button>
      <button type="button" onClick={() => clearCart()}>
        clear
      </button>
    </div>
  );
}

describe("CartContext", () => {
  it("adds items and merges quantities for the same product", async () => {
    render(
      <CartProvider>
        <CartProbe />
      </CartProvider>
    );

    await act(async () => {
      screen.getByText("add-widget").click();
      screen.getByText("add-widget").click();
    });

    expect(screen.getByTestId("count")).toHaveTextContent("4");
    expect(screen.getByTestId("total")).toHaveTextContent("40");
    expect(screen.getByTestId("items")).toHaveTextContent(
      '"product_id":1'
    );
  });

  it("updates quantity and removes lines when quantity hits zero", async () => {
    render(
      <CartProvider>
        <CartProbe />
      </CartProvider>
    );

    await act(async () => {
      screen.getByText("add-widget").click();
      screen.getByText("zero-widget").click();
    });

    expect(screen.getByTestId("count")).toHaveTextContent("0");
    expect(screen.getByTestId("items")).toHaveTextContent("[]");
  });

  it("removeItem drops a single product from the cart", async () => {
    render(
      <CartProvider>
        <CartProbe />
      </CartProvider>
    );

    await act(async () => {
      screen.getByText("add-widget").click();
      screen.getByText("add-gadget").click();
      screen.getByText("remove-gadget").click();
    });

    expect(screen.getByTestId("count")).toHaveTextContent("2");
    expect(screen.getByTestId("items")).not.toHaveTextContent('"product_id":2');
  });

  it("clearCart empties all items", async () => {
    render(
      <CartProvider>
        <CartProbe />
      </CartProvider>
    );

    await act(async () => {
      screen.getByText("add-widget").click();
      screen.getByText("clear").click();
    });

    expect(screen.getByTestId("items")).toHaveTextContent("[]");
  });

  it("persists cart items to localStorage", async () => {
    render(
      <CartProvider>
        <CartProbe />
      </CartProvider>
    );

    await act(async () => {
      screen.getByText("add-widget").click();
    });

    const stored = JSON.parse(localStorage.getItem("cart"));
    expect(stored).toHaveLength(1);
    expect(stored[0]).toMatchObject({ product_id: 1, quantity: 2 });
  });

  it("throws when useCart is used outside CartProvider", () => {
    expect(() => render(<CartProbe />)).toThrow(
      /useCart must be used inside <CartProvider>/
    );
  });
});
