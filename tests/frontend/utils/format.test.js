import { describe, expect, it } from "vitest";
import {
  formatDate,
  formatINR,
  formatNumber,
} from "../../../frontend/src/utils/format.js";

describe("formatINR", () => {
  it("formats amounts as Indian Rupees with two decimal places", () => {
    expect(formatINR(1234.5)).toBe("₹1,234.50");
    expect(formatINR(0)).toBe("₹0.00");
  });

  it("treats invalid values as zero", () => {
    expect(formatINR(undefined)).toBe("₹0.00");
    expect(formatINR("not-a-number")).toBe("₹0.00");
  });
});

describe("formatNumber", () => {
  it("formats integers with en-IN grouping", () => {
    expect(formatNumber(1234567)).toBe("12,34,567");
  });

  it("treats invalid values as zero", () => {
    expect(formatNumber(null)).toBe("0");
  });
});

describe("formatDate", () => {
  it("formats ISO strings for en-IN locale", () => {
    const formatted = formatDate("2026-05-29T12:00:00.000Z");
    expect(formatted).toMatch(/2026/);
    expect(formatted).toMatch(/May|29/);
  });
});
