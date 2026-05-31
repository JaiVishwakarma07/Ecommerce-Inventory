import { describe, expect, it } from "vitest";
import {
  PASSWORD_HINT,
  validatePassword,
} from "../../../frontend/src/utils/passwordRules.js";

describe("validatePassword", () => {
  it("accepts passwords meeting all complexity rules", () => {
    expect(validatePassword("AdminPass123!")).toEqual({ ok: true, message: "" });
  });

  it("rejects passwords shorter than 8 characters", () => {
    expect(validatePassword("Ab1!")).toEqual({
      ok: false,
      message: "Password must be at least 8 characters.",
    });
  });

  it("rejects passwords longer than 128 characters", () => {
    const long = `Aa1!${"x".repeat(125)}`;
    expect(validatePassword(long).ok).toBe(false);
    expect(validatePassword(long).message).toMatch(/128 characters/);
  });

  it("rejects passwords missing required character classes", () => {
    expect(validatePassword("alllowercase1!").ok).toBe(false);
    expect(validatePassword("ALLUPPERCASE1!").ok).toBe(false);
    expect(validatePassword("NoDigitsHere!").ok).toBe(false);
    expect(validatePassword("NoSymbol123").ok).toBe(false);
  });

  it("exports a user-facing hint string", () => {
    expect(PASSWORD_HINT).toContain("uppercase");
    expect(PASSWORD_HINT).toContain("symbol");
  });
});
