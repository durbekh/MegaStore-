/**
 * Product API service for MegaStore.
 *
 * Provides functions for product listing, detail retrieval, search,
 * category browsing, and vendor product management.
 */

import apiClient from "./client";

const productsAPI = {
  /**
   * Fetch a paginated list of active products with optional filters.
   *
   * @param {Object} params - Query parameters for filtering and pagination.
   * @param {string} [params.category] - Category slug to filter by.
   * @param {number} [params.min_price] - Minimum price filter.
   * @param {number} [params.max_price] - Maximum price filter.
   * @param {number} [params.min_rating] - Minimum rating filter.
   * @param {string} [params.vendor] - Vendor slug to filter by.
   * @param {boolean} [params.in_stock] - Show only in-stock products.
   * @param {number} [params.page] - Page number.
   * @param {number} [params.page_size] - Results per page.
   * @param {string} [params.ordering] - Sort field (e.g., "-price", "created_at").
   * @returns {Promise} Paginated product results.
   */
  getProducts(params = {}) {
    return apiClient.get("/products/", { params });
  },

  /**
   * Fetch detailed product information by slug.
   *
   * @param {string} slug - The product's URL slug.
   * @returns {Promise} Product detail data including images, vendor, and reviews.
   */
  getProduct(slug) {
    return apiClient.get(`/products/${slug}/`);
  },

  /**
   * Fetch featured products for the homepage.
   *
   * @returns {Promise} Array of featured product objects.
   */
  getFeaturedProducts() {
    return apiClient.get("/products/featured/");
  },

  /**
   * Search products by query string.
   *
   * @param {string} query - Search query.
   * @param {Object} [params] - Additional filter parameters.
   * @returns {Promise} Search results with count.
   */
  searchProducts(query, params = {}) {
    return apiClient.get("/products/search/", {
      params: { q: query, ...params },
    });
  },

  /**
   * Fetch all product categories (hierarchical tree).
   *
   * @returns {Promise} Array of top-level categories with children.
   */
  getCategories() {
    return apiClient.get("/products/categories/");
  },

  /**
   * Fetch a single category by slug.
   *
   * @param {string} slug - The category's URL slug.
   * @returns {Promise} Category detail with product count.
   */
  getCategory(slug) {
    return apiClient.get(`/products/categories/${slug}/`);
  },

  /**
   * Create a new product (vendor only).
   *
   * @param {FormData} formData - Product data with optional image files.
   * @returns {Promise} Created product data.
   */
  createProduct(formData) {
    return apiClient.post("/products/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  /**
   * Update an existing product (vendor/admin only).
   *
   * @param {string} slug - Product slug to update.
   * @param {Object|FormData} data - Updated product fields.
   * @returns {Promise} Updated product data.
   */
  updateProduct(slug, data) {
    const headers = data instanceof FormData
      ? { "Content-Type": "multipart/form-data" }
      : {};
    return apiClient.patch(`/products/${slug}/`, data, { headers });
  },

  /**
   * Delete a product (vendor/admin only).
   *
   * @param {string} slug - Product slug to delete.
   * @returns {Promise}
   */
  deleteProduct(slug) {
    return apiClient.delete(`/products/${slug}/`);
  },

  /**
   * Fetch products for the authenticated vendor's store.
   *
   * @returns {Promise} Array of the vendor's products.
   */
  getVendorProducts() {
    return apiClient.get("/products/vendor_products/");
  },

  /**
   * Fetch reviews for a product.
   *
   * @param {string} slug - Product slug.
   * @returns {Promise} Array of approved reviews.
   */
  getProductReviews(slug) {
    return apiClient.get(`/products/${slug}/reviews/`);
  },

  /**
   * Submit a review for a product.
   *
   * @param {string} slug - Product slug.
   * @param {Object} data - Review data { rating, title, comment }.
   * @returns {Promise} Created review data.
   */
  createReview(slug, data) {
    return apiClient.post(`/products/${slug}/reviews/`, data);
  },

  /**
   * Delete a product image.
   *
   * @param {string} imageId - UUID of the image to delete.
   * @returns {Promise}
   */
  deleteProductImage(imageId) {
    return apiClient.delete(`/products/images/${imageId}/`);
  },
};

export default productsAPI;
