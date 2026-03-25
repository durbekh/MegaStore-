/**
 * Shopping cart store for MegaStore (Zustand).
 *
 * Manages the shopping cart state with server synchronization.
 * All cart operations are reflected both locally (for instant UI updates)
 * and on the server (for persistence across sessions).
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import apiClient from "../api/client";

const useCartStore = create(
  devtools(
    (set, get) => ({
      // State
      items: [],
      totalItems: 0,
      totalUniqueItems: 0,
      subtotal: "0.00",
      isLoading: false,
      error: null,

      /**
       * Fetch the current cart from the server.
       */
      fetchCart: async () => {
        set({ isLoading: true, error: null });
        try {
          const response = await apiClient.get("/cart/");
          const cart = response.data;
          set({
            items: cart.items || [],
            totalItems: cart.total_items || 0,
            totalUniqueItems: cart.total_unique_items || 0,
            subtotal: cart.subtotal || "0.00",
            isLoading: false,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error.response?.data?.error?.message || "Failed to load cart.",
          });
        }
      },

      /**
       * Fetch a lightweight cart summary (for header badge).
       */
      fetchCartSummary: async () => {
        try {
          const response = await apiClient.get("/cart/summary/");
          set({
            totalItems: response.data.total_items,
            totalUniqueItems: response.data.total_unique_items,
            subtotal: response.data.subtotal,
          });
        } catch {
          // Silently fail for summary requests
        }
      },

      /**
       * Add a product to the cart.
       *
       * @param {string} productId - UUID of the product to add.
       * @param {number} [quantity=1] - Quantity to add.
       */
      addItem: async (productId, quantity = 1) => {
        set({ isLoading: true, error: null });
        try {
          const response = await apiClient.post("/cart/items/", {
            product_id: productId,
            quantity,
          });
          const cart = response.data;
          set({
            items: cart.items || [],
            totalItems: cart.total_items || 0,
            totalUniqueItems: cart.total_unique_items || 0,
            subtotal: cart.subtotal || "0.00",
            isLoading: false,
          });
          return { success: true };
        } catch (error) {
          const message =
            error.response?.data?.detail ||
            error.response?.data?.[0] ||
            "Failed to add item to cart.";
          set({ isLoading: false, error: message });
          return { success: false, error: message };
        }
      },

      /**
       * Update the quantity of a cart item.
       *
       * @param {string} itemId - UUID of the cart item.
       * @param {number} quantity - New quantity.
       */
      updateItemQuantity: async (itemId, quantity) => {
        set({ isLoading: true, error: null });
        try {
          const response = await apiClient.patch(`/cart/items/${itemId}/`, {
            quantity,
          });
          const cart = response.data;
          set({
            items: cart.items || [],
            totalItems: cart.total_items || 0,
            totalUniqueItems: cart.total_unique_items || 0,
            subtotal: cart.subtotal || "0.00",
            isLoading: false,
          });
          return { success: true };
        } catch (error) {
          const message =
            error.response?.data?.detail || "Failed to update item quantity.";
          set({ isLoading: false, error: message });
          return { success: false, error: message };
        }
      },

      /**
       * Remove an item from the cart.
       *
       * @param {string} itemId - UUID of the cart item to remove.
       */
      removeItem: async (itemId) => {
        // Optimistic update: remove from local state immediately
        const previousItems = get().items;
        set({
          items: previousItems.filter((item) => item.id !== itemId),
          error: null,
        });

        try {
          const response = await apiClient.delete(
            `/cart/items/${itemId}/remove/`
          );
          const cart = response.data;
          set({
            items: cart.items || [],
            totalItems: cart.total_items || 0,
            totalUniqueItems: cart.total_unique_items || 0,
            subtotal: cart.subtotal || "0.00",
          });
          return { success: true };
        } catch (error) {
          // Revert optimistic update on failure
          set({ items: previousItems, error: "Failed to remove item." });
          return { success: false };
        }
      },

      /**
       * Clear all items from the cart.
       */
      clearCart: async () => {
        set({ isLoading: true, error: null });
        try {
          await apiClient.post("/cart/clear/");
          set({
            items: [],
            totalItems: 0,
            totalUniqueItems: 0,
            subtotal: "0.00",
            isLoading: false,
          });
          return { success: true };
        } catch {
          set({ isLoading: false, error: "Failed to clear cart." });
          return { success: false };
        }
      },

      /**
       * Check if a specific product is already in the cart.
       *
       * @param {string} productId - UUID of the product.
       * @returns {boolean}
       */
      isInCart: (productId) => {
        return get().items.some((item) => item.product === productId);
      },

      /**
       * Get the cart item for a specific product.
       *
       * @param {string} productId - UUID of the product.
       * @returns {Object|undefined}
       */
      getCartItem: (productId) => {
        return get().items.find((item) => item.product === productId);
      },

      /**
       * Reset cart to initial empty state (used on logout).
       */
      resetCart: () => {
        set({
          items: [],
          totalItems: 0,
          totalUniqueItems: 0,
          subtotal: "0.00",
          error: null,
        });
      },
    }),
    { name: "CartStore" }
  )
);

export default useCartStore;
