import { describe, expect, it } from "vitest";
import { formatApiError } from "../../../frontend/src/utils/apiError.js";

describe("formatApiError", () => {
  it("returns network error message when response is missing", () => {
    expect(formatApiError(new Error("Network Error"))).toBe("Network Error");
    expect(formatApiError({})).toBe("Something went wrong");
  });

  it("returns string detail from FastAPI responses", () => {
    expect(
      formatApiError({
        response: { status: 400, data: { detail: "Email already registered" } },
      })
    ).toBe("Email already registered");
  });

  it("joins validation error arrays from FastAPI", () => {
    expect(
      formatApiError({
        response: {
          status: 422,
          data: {
            detail: [
              { loc: ["body", "email"], msg: "Invalid email" },
              { loc: ["body", "password"], msg: "Too short" },
            ],
          },
        },
      })
    ).toBe("email: Invalid email; password: Too short");
  });

  it("maps common HTTP statuses to friendly messages", () => {
    expect(
      formatApiError({ response: { status: 403, data: {} } })
    ).toBe("You do not have permission for this action.");
    expect(
      formatApiError({ response: { status: 404, data: {} } })
    ).toBe("The requested resource was not found.");
  });

  it("uses fallback for 409 conflicts", () => {
    expect(
      formatApiError(
        { response: { status: 409, data: {} } },
        "Duplicate SKU"
      )
    ).toBe("Duplicate SKU");
  });
});
