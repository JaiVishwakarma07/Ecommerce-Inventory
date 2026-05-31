export function validatePassword(password) {
  if (!password || password.length < 8) {
    return {
      ok: false,
      message: "Password must be at least 8 characters.",
    };
  }
  if (password.length > 128) {
    return {
      ok: false,
      message: "Password must be at most 128 characters.",
    };
  }

  const hasLower = /[a-z]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSymbol = /[^a-zA-Z0-9\s]/.test(password);

  if (!hasLower || !hasUpper || !hasDigit || !hasSymbol) {
    return {
      ok: false,
      message:
        "Password must include lowercase, uppercase, a number, and a symbol.",
    };
  }

  return { ok: true, message: "" };
}

export const PASSWORD_HINT =
  "8+ characters with uppercase, lowercase, a number, and a symbol.";
