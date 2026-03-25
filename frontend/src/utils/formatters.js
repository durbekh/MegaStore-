/**
 * Formatting utilities for MegaStore frontend.
 *
 * Provides consistent formatting for currency, dates, numbers,
 * and other display values across all components.
 */

/**
 * Format a number or string as USD currency.
 *
 * @param {number|string} amount - The amount to format.
 * @param {string} [currency="USD"] - ISO 4217 currency code.
 * @returns {string} Formatted currency string (e.g., "$29.99").
 *
 * @example
 * formatCurrency(29.99)    // "$29.99"
 * formatCurrency("1500")   // "$1,500.00"
 * formatCurrency(0)        // "$0.00"
 */
export function formatCurrency(amount, currency = "USD") {
  const numericAmount = typeof amount === "string" ? parseFloat(amount) : amount;

  if (isNaN(numericAmount)) {
    return "$0.00";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numericAmount);
}

/**
 * Format a date string or Date object into a human-readable format.
 *
 * @param {string|Date} date - The date to format.
 * @param {Object} [options] - Intl.DateTimeFormat options.
 * @returns {string} Formatted date string.
 *
 * @example
 * formatDate("2024-03-15T10:30:00Z")  // "March 15, 2024"
 * formatDate(new Date(), { dateStyle: "short" })  // "3/15/24"
 */
export function formatDate(date, options = {}) {
  if (!date) return "";

  const dateObj = typeof date === "string" ? new Date(date) : date;

  const defaultOptions = {
    year: "numeric",
    month: "long",
    day: "numeric",
    ...options,
  };

  return new Intl.DateTimeFormat("en-US", defaultOptions).format(dateObj);
}

/**
 * Format a date as a relative time string (e.g., "2 hours ago").
 *
 * @param {string|Date} date - The date to format.
 * @returns {string} Relative time string.
 *
 * @example
 * formatRelativeTime(new Date(Date.now() - 3600000))  // "1 hour ago"
 */
export function formatRelativeTime(date) {
  if (!date) return "";

  const dateObj = typeof date === "string" ? new Date(date) : date;
  const now = new Date();
  const diffMs = now - dateObj;
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);
  const diffMonths = Math.floor(diffDays / 30);
  const diffYears = Math.floor(diffDays / 365);

  if (diffSeconds < 60) return "just now";
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes !== 1 ? "s" : ""} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`;
  if (diffWeeks < 5) return `${diffWeeks} week${diffWeeks !== 1 ? "s" : ""} ago`;
  if (diffMonths < 12) return `${diffMonths} month${diffMonths !== 1 ? "s" : ""} ago`;
  return `${diffYears} year${diffYears !== 1 ? "s" : ""} ago`;
}

/**
 * Format an order status string for display.
 *
 * @param {string} status - Raw status value (e.g., "out_of_stock").
 * @returns {string} Human-readable status (e.g., "Out of Stock").
 */
export function formatStatus(status) {
  if (!status) return "";

  const statusMap = {
    pending: "Pending",
    confirmed: "Confirmed",
    processing: "Processing",
    shipped: "Shipped",
    delivered: "Delivered",
    cancelled: "Cancelled",
    refunded: "Refunded",
    draft: "Draft",
    active: "Active",
    inactive: "Inactive",
    out_of_stock: "Out of Stock",
    approved: "Approved",
    suspended: "Suspended",
    rejected: "Rejected",
    paid: "Paid",
    unpaid: "Unpaid",
    failed: "Failed",
  };

  return statusMap[status] || status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Get the CSS color class for an order status badge.
 *
 * @param {string} status - Order status value.
 * @returns {string} Tailwind CSS color classes.
 */
export function getStatusColor(status) {
  const colorMap = {
    pending: "bg-yellow-100 text-yellow-800",
    confirmed: "bg-blue-100 text-blue-800",
    processing: "bg-indigo-100 text-indigo-800",
    shipped: "bg-purple-100 text-purple-800",
    delivered: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800",
    refunded: "bg-gray-100 text-gray-800",
    active: "bg-green-100 text-green-800",
    inactive: "bg-gray-100 text-gray-800",
    draft: "bg-gray-100 text-gray-600",
    out_of_stock: "bg-red-100 text-red-800",
    approved: "bg-green-100 text-green-800",
    suspended: "bg-orange-100 text-orange-800",
    rejected: "bg-red-100 text-red-800",
    paid: "bg-green-100 text-green-800",
    unpaid: "bg-yellow-100 text-yellow-800",
    failed: "bg-red-100 text-red-800",
  };

  return colorMap[status] || "bg-gray-100 text-gray-800";
}

/**
 * Truncate a text string to a maximum length, adding an ellipsis.
 *
 * @param {string} text - Text to truncate.
 * @param {number} [maxLength=100] - Maximum character length.
 * @returns {string} Truncated text.
 */
export function truncateText(text, maxLength = 100) {
  if (!text || text.length <= maxLength) return text || "";
  return text.substring(0, maxLength).trim() + "...";
}

/**
 * Format a star rating value for display.
 *
 * @param {number|string} rating - Rating value (0-5).
 * @param {number} [precision=1] - Decimal precision.
 * @returns {string} Formatted rating (e.g., "4.5").
 */
export function formatRating(rating, precision = 1) {
  const numericRating = typeof rating === "string" ? parseFloat(rating) : rating;
  if (isNaN(numericRating)) return "0.0";
  return numericRating.toFixed(precision);
}

/**
 * Format a number with thousands separators.
 *
 * @param {number} num - Number to format.
 * @returns {string} Formatted number (e.g., "1,234").
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return "0";
  return new Intl.NumberFormat("en-US").format(num);
}

/**
 * Generate a URL-safe slug from a string.
 *
 * @param {string} text - Text to slugify.
 * @returns {string} URL-safe slug.
 */
export function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
