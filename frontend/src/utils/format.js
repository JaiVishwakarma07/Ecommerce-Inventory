/**
 * Format a number as Indian Rupees, e.g. 1234.5 -> "₹1,234.50".
 * Uses Intl so we get correct grouping (12,34,567.89 in en-IN).
 */
export const formatINR = (amount) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(Number(amount) || 0);

export const formatNumber = (n) =>
  new Intl.NumberFormat("en-IN").format(Number(n) || 0);

export const formatDate = (iso) =>
  new Date(iso).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
