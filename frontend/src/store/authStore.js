/**
 * Authentication store for MegaStore (Zustand).
 *
 * Manages user authentication state, login/logout flows,
 * token storage, and user profile data.
 */

import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import apiClient from "../api/client";

const useAuthStore = create(
  devtools(
    persist(
      (set, get) => ({
        // State
        user: null,
        tokens: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,

        /**
         * Log in with email and password.
         * Stores tokens in localStorage and user data in the store.
         */
        login: async (email, password) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.post("/auth/login/", {
              email,
              password,
            });
            const { access, refresh, user } = response.data;
            const tokens = { access, refresh };

            localStorage.setItem("tokens", JSON.stringify(tokens));

            set({
              user,
              tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });

            return { success: true, user };
          } catch (error) {
            const message =
              error.response?.data?.detail ||
              error.response?.data?.error?.message ||
              "Login failed. Please check your credentials.";
            set({ isLoading: false, error: message });
            return { success: false, error: message };
          }
        },

        /**
         * Register a new customer account.
         */
        registerCustomer: async (data) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.post("/auth/register/", data);
            const { user, tokens } = response.data;

            localStorage.setItem("tokens", JSON.stringify(tokens));

            set({
              user,
              tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });

            return { success: true, user };
          } catch (error) {
            const message =
              error.response?.data?.detail ||
              error.response?.data?.error?.message ||
              "Registration failed.";
            set({ isLoading: false, error: message });
            return { success: false, error: message };
          }
        },

        /**
         * Register a new vendor account.
         */
        registerVendor: async (data) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.post("/auth/register/vendor/", data);
            const { user, tokens } = response.data;

            localStorage.setItem("tokens", JSON.stringify(tokens));

            set({
              user,
              tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });

            return { success: true, user };
          } catch (error) {
            const message =
              error.response?.data?.detail ||
              "Vendor registration failed.";
            set({ isLoading: false, error: message });
            return { success: false, error: message };
          }
        },

        /**
         * Log out the current user.
         * Blacklists the refresh token on the server and clears local state.
         */
        logout: async () => {
          const { tokens } = get();
          try {
            if (tokens?.refresh) {
              await apiClient.post("/auth/logout/", {
                refresh: tokens.refresh,
              });
            }
          } catch {
            // Ignore logout errors (token may already be invalid)
          } finally {
            localStorage.removeItem("tokens");
            set({
              user: null,
              tokens: null,
              isAuthenticated: false,
              error: null,
            });
          }
        },

        /**
         * Fetch the current user's profile from the API.
         */
        fetchProfile: async () => {
          try {
            const response = await apiClient.get("/auth/profile/");
            set({ user: response.data });
            return response.data;
          } catch {
            return null;
          }
        },

        /**
         * Update the current user's profile.
         */
        updateProfile: async (data) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.patch("/auth/profile/", data);
            set({ user: response.data, isLoading: false });
            return { success: true };
          } catch (error) {
            const message =
              error.response?.data?.error?.message || "Profile update failed.";
            set({ isLoading: false, error: message });
            return { success: false, error: message };
          }
        },

        /**
         * Clear any error messages in the store.
         */
        clearError: () => set({ error: null }),

        /**
         * Check if the current user has a specific role.
         */
        hasRole: (role) => get().user?.role === role,

        /**
         * Check if the user is a vendor.
         */
        isVendor: () => get().user?.role === "vendor",

        /**
         * Check if the user is an admin.
         */
        isAdmin: () => get().user?.role === "admin",
      }),
      {
        name: "megastore-auth",
        partialize: (state) => ({
          user: state.user,
          tokens: state.tokens,
          isAuthenticated: state.isAuthenticated,
        }),
      }
    ),
    { name: "AuthStore" }
  )
);

export default useAuthStore;
