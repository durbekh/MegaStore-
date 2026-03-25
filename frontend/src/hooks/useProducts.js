/**
 * Custom React hooks for product data fetching and management.
 *
 * Uses React Query (TanStack Query) for server state management
 * with caching, background refetching, and optimistic updates.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import productsAPI from "../api/products";

/** Cache key constants for query invalidation. */
const QUERY_KEYS = {
  products: "products",
  product: "product",
  categories: "categories",
  featured: "featuredProducts",
  search: "productSearch",
  vendorProducts: "vendorProducts",
  reviews: "productReviews",
};

/**
 * Fetch a paginated list of products with filters.
 *
 * @param {Object} params - Filter and pagination parameters.
 * @param {Object} [options] - React Query options (enabled, etc.).
 * @returns {UseQueryResult} Query result with products data.
 */
export function useProducts(params = {}, options = {}) {
  return useQuery({
    queryKey: [QUERY_KEYS.products, params],
    queryFn: () => productsAPI.getProducts(params).then((res) => res.data),
    staleTime: 1000 * 60 * 2, // 2 minutes
    ...options,
  });
}

/**
 * Fetch a single product by slug.
 *
 * @param {string} slug - Product URL slug.
 * @param {Object} [options] - React Query options.
 * @returns {UseQueryResult} Query result with product detail data.
 */
export function useProduct(slug, options = {}) {
  return useQuery({
    queryKey: [QUERY_KEYS.product, slug],
    queryFn: () => productsAPI.getProduct(slug).then((res) => res.data),
    enabled: !!slug,
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Fetch featured products for the homepage.
 *
 * @returns {UseQueryResult} Query result with featured products.
 */
export function useFeaturedProducts() {
  return useQuery({
    queryKey: [QUERY_KEYS.featured],
    queryFn: () => productsAPI.getFeaturedProducts().then((res) => res.data),
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

/**
 * Search products by query string.
 *
 * @param {string} query - Search query.
 * @param {Object} [params] - Additional filter parameters.
 * @returns {UseQueryResult} Query result with search results.
 */
export function useProductSearch(query, params = {}) {
  return useQuery({
    queryKey: [QUERY_KEYS.search, query, params],
    queryFn: () =>
      productsAPI.searchProducts(query, params).then((res) => res.data),
    enabled: query.length >= 2,
    staleTime: 1000 * 30, // 30 seconds
  });
}

/**
 * Fetch all product categories.
 *
 * @returns {UseQueryResult} Query result with category tree.
 */
export function useCategories() {
  return useQuery({
    queryKey: [QUERY_KEYS.categories],
    queryFn: () => productsAPI.getCategories().then((res) => res.data),
    staleTime: 1000 * 60 * 15, // 15 minutes (categories rarely change)
  });
}

/**
 * Fetch the authenticated vendor's products.
 *
 * @returns {UseQueryResult} Query result with vendor's products.
 */
export function useVendorProducts() {
  return useQuery({
    queryKey: [QUERY_KEYS.vendorProducts],
    queryFn: () => productsAPI.getVendorProducts().then((res) => res.data),
  });
}

/**
 * Fetch reviews for a product.
 *
 * @param {string} slug - Product slug.
 * @returns {UseQueryResult} Query result with product reviews.
 */
export function useProductReviews(slug) {
  return useQuery({
    queryKey: [QUERY_KEYS.reviews, slug],
    queryFn: () => productsAPI.getProductReviews(slug).then((res) => res.data),
    enabled: !!slug,
  });
}

/**
 * Mutation hook for creating a new product.
 * Invalidates the vendor products and products list caches on success.
 *
 * @returns {UseMutationResult} Mutation result for product creation.
 */
export function useCreateProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (formData) => productsAPI.createProduct(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.vendorProducts] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.products] });
    },
  });
}

/**
 * Mutation hook for submitting a product review.
 *
 * @param {string} slug - Product slug.
 * @returns {UseMutationResult} Mutation result for review creation.
 */
export function useCreateReview(slug) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => productsAPI.createReview(slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.reviews, slug] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.product, slug] });
    },
  });
}
