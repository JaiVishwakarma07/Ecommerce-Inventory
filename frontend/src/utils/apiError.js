/**
 * Turn FastAPI error responses into a single user-facing string.
 */
export function formatApiError(err, fallback = "Something went wrong") {
  if (!err?.response) {
    return err?.message || fallback;
  }

  const { status, data } = err.response;
  const detail = data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item?.msg) {
          const field = Array.isArray(item.loc)
            ? item.loc.filter((p) => p !== "body").join(".")
            : "";
          return field ? `${field}: ${item.msg}` : item.msg;
        }
        return null;
      })
      .filter(Boolean);
    if (messages.length > 0) return messages.join("; ");
  }

  if (status === 403) return "You do not have permission for this action.";
  if (status === 404) return "The requested resource was not found.";
  if (status === 409) return fallback;

  return fallback;
}
