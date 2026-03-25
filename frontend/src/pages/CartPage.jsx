/**
 * CartPage for MegaStore.
 *
 * Displays the shopping cart with item management (quantity update,
 * remove), price summary, coupon application, and checkout navigation.
 */

import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import useCartStore from "../store/cartStore";
import useAuthStore from "../store/authStore";
import { formatCurrency } from "../utils/formatters";

export default function CartPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const {
    items,
    totalItems,
    subtotal,
    isLoading,
    error,
    fetchCart,
    updateItemQuantity,
    removeItem,
    clearCart,
  } = useCartStore();

  const [couponCode, setCouponCode] = useState("");
  const [couponDiscount, setCouponDiscount] = useState(null);
  const [removingItemId, setRemovingItemId] = useState(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchCart();
    }
  }, [isAuthenticated, fetchCart]);

  const handleQuantityChange = async (itemId, newQuantity) => {
    if (newQuantity < 1) return;
    await updateItemQuantity(itemId, newQuantity);
  };

  const handleRemoveItem = async (itemId) => {
    setRemovingItemId(itemId);
    await removeItem(itemId);
    setRemovingItemId(null);
  };

  const handleClearCart = async () => {
    if (window.confirm("Are you sure you want to clear your cart?")) {
      await clearCart();
    }
  };

  const handleCheckout = () => {
    navigate("/checkout");
  };

  // Calculate totals
  const numericSubtotal = parseFloat(subtotal) || 0;
  const shippingEstimate = numericSubtotal >= 50 ? 0 : 5.99;
  const discount = couponDiscount ? parseFloat(couponDiscount) : 0;
  const estimatedTotal = numericSubtotal + shippingEstimate - discount;

  if (!isAuthenticated) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Your Shopping Cart</h1>
        <p className="text-gray-500 mb-8">Please sign in to view your cart.</p>
        <Link
          to="/login"
          className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700"
        >
          Sign In
        </Link>
      </div>
    );
  }

  if (isLoading && items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="animate-pulse space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex gap-4 p-4 bg-white rounded-lg">
              <div className="bg-gray-200 w-24 h-24 rounded" />
              <div className="flex-1 space-y-2">
                <div className="bg-gray-200 h-5 rounded w-1/2" />
                <div className="bg-gray-200 h-4 rounded w-1/4" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <svg className="w-24 h-24 mx-auto text-gray-300 mb-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
            d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z"
          />
        </svg>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Your Cart is Empty</h1>
        <p className="text-gray-500 mb-8">Looks like you haven't added anything to your cart yet.</p>
        <Link
          to="/products"
          className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700"
        >
          Start Shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Shopping Cart ({totalItems} item{totalItems !== 1 ? "s" : ""})
        </h1>
        <button
          onClick={handleClearCart}
          className="text-sm text-red-600 hover:text-red-700 font-medium"
        >
          Clear Cart
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-2 space-y-4">
          {items.map((item) => (
            <div
              key={item.id}
              className={`flex gap-4 p-4 bg-white rounded-lg border border-gray-200 ${
                !item.is_available ? "opacity-60" : ""
              }`}
            >
              {/* Product Image */}
              <Link to={`/products/${item.product_slug}`} className="flex-shrink-0">
                {item.product_image ? (
                  <img
                    src={item.product_image}
                    alt={item.product_name}
                    className="w-24 h-24 object-cover rounded-lg"
                  />
                ) : (
                  <div className="w-24 h-24 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
                    No Image
                  </div>
                )}
              </Link>

              {/* Item Details */}
              <div className="flex-1 min-w-0">
                <Link
                  to={`/products/${item.product_slug}`}
                  className="text-sm font-medium text-gray-900 hover:text-indigo-600 line-clamp-2"
                >
                  {item.product_name}
                </Link>
                <p className="text-xs text-gray-500 mt-1">
                  Sold by {item.vendor_name}
                </p>
                <p className="text-sm font-semibold text-gray-900 mt-1">
                  {formatCurrency(item.product_price)}
                </p>

                {!item.is_available && (
                  <p className="text-xs text-red-600 mt-1 font-medium">
                    This item is no longer available in the requested quantity.
                  </p>
                )}

                {/* Quantity Controls */}
                <div className="flex items-center gap-4 mt-3">
                  <div className="flex items-center border border-gray-300 rounded">
                    <button
                      onClick={() => handleQuantityChange(item.id, item.quantity - 1)}
                      disabled={item.quantity <= 1}
                      className="px-2 py-1 text-gray-600 hover:bg-gray-100 disabled:opacity-50 text-sm"
                    >
                      -
                    </button>
                    <span className="px-3 py-1 text-sm font-medium">{item.quantity}</span>
                    <button
                      onClick={() => handleQuantityChange(item.id, item.quantity + 1)}
                      disabled={item.quantity >= item.max_quantity}
                      className="px-2 py-1 text-gray-600 hover:bg-gray-100 disabled:opacity-50 text-sm"
                    >
                      +
                    </button>
                  </div>

                  <button
                    onClick={() => handleRemoveItem(item.id)}
                    disabled={removingItemId === item.id}
                    className="text-sm text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
                  >
                    {removingItemId === item.id ? "Removing..." : "Remove"}
                  </button>
                </div>
              </div>

              {/* Line Total */}
              <div className="text-right flex-shrink-0">
                <p className="font-semibold text-gray-900">
                  {formatCurrency(item.line_total)}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-gray-200 rounded-lg p-6 sticky top-24">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Order Summary</h2>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Subtotal</span>
                <span className="font-medium">{formatCurrency(numericSubtotal)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Shipping</span>
                <span className="font-medium">
                  {shippingEstimate === 0 ? (
                    <span className="text-green-600">Free</span>
                  ) : (
                    formatCurrency(shippingEstimate)
                  )}
                </span>
              </div>
              {discount > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>Discount</span>
                  <span>-{formatCurrency(discount)}</span>
                </div>
              )}
              <div className="border-t border-gray-200 pt-3 flex justify-between text-base">
                <span className="font-semibold">Estimated Total</span>
                <span className="font-bold">{formatCurrency(estimatedTotal)}</span>
              </div>
            </div>

            {numericSubtotal < 50 && (
              <p className="text-xs text-gray-500 mt-3">
                Add {formatCurrency(50 - numericSubtotal)} more for free shipping!
              </p>
            )}

            {/* Coupon Input */}
            <div className="mt-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                  placeholder="Coupon code"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
                <button
                  onClick={() => setCouponCode("")}
                  className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200"
                >
                  Apply
                </button>
              </div>
            </div>

            <button
              onClick={handleCheckout}
              className="w-full mt-6 bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition-colors"
            >
              Proceed to Checkout
            </button>

            <Link
              to="/products"
              className="block text-center mt-3 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Continue Shopping
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
