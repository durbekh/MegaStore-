/**
 * Orders API service for MegaStore.
 *
 * Provides functions for order management including creation,
 * listing, detail retrieval, cancellation, and vendor operations.
 */

import apiClient from "./client";

const ordersAPI = {
  /**
   * Fetch the authenticated customer's orders.
   *
   * @param {Object} [params] - Pagination and filter parameters.
   * @param {number} [params.page] - Page number.
   * @param {string} [params.status] - Filter by order status.
   * @returns {Promise} Paginated order list.
   */
  getOrders(params = {}) {
    return apiClient.get("/orders/", { params });
  },

  /**
   * Fetch detailed information for a specific order.
   *
   * @param {string} orderId - UUID of the order.
   * @returns {Promise} Full order detail with items and shipping info.
   */
  getOrder(orderId) {
    return apiClient.get(`/orders/${orderId}/`);
  },

  /**
   * Create a new order from the current cart.
   *
   * @param {Object} shippingData - Shipping address and notes.
   * @param {string} shippingData.shipping_full_name
   * @param {string} shippingData.shipping_address_line1
   * @param {string} shippingData.shipping_city
   * @param {string} shippingData.shipping_state
   * @param {string} shippingData.shipping_postal_code
   * @param {string} [shippingData.shipping_country="US"]
   * @param {string} [shippingData.customer_notes]
   * @returns {Promise} Created order data.
   */
  createOrder(shippingData) {
    return apiClient.post("/orders/create/", shippingData);
  },

  /**
   * Cancel an order.
   *
   * @param {string} orderId - UUID of the order to cancel.
   * @returns {Promise} Cancellation confirmation.
   */
  cancelOrder(orderId) {
    return apiClient.post(`/orders/${orderId}/cancel/`);
  },

  // -- Vendor endpoints --

  /**
   * Fetch orders containing items from the authenticated vendor's store.
   *
   * @param {Object} [params] - Pagination parameters.
   * @returns {Promise} Paginated list of vendor orders.
   */
  getVendorOrders(params = {}) {
    return apiClient.get("/orders/vendor/", { params });
  },

  /**
   * Fulfill the vendor's items in an order.
   *
   * @param {string} orderId - UUID of the order.
   * @param {Object} [trackingData] - Optional tracking information.
   * @param {string} [trackingData.tracking_number]
   * @param {string} [trackingData.tracking_url]
   * @returns {Promise} Fulfillment confirmation.
   */
  fulfillOrder(orderId, trackingData = {}) {
    return apiClient.post(`/orders/vendor/${orderId}/fulfill/`, trackingData);
  },

  /**
   * Fetch sales statistics for the authenticated vendor.
   *
   * @returns {Promise} Sales metrics and recent orders.
   */
  getVendorSalesStats() {
    return apiClient.get("/orders/vendor/stats/");
  },
};

export default ordersAPI;
