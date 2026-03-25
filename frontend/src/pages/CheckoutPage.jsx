/**
 * CheckoutPage for MegaStore.
 *
 * Multi-step checkout flow: shipping address, order review,
 * and payment processing via Stripe Elements.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";
import useCartStore from "../store/cartStore";
import useAuthStore from "../store/authStore";
import { formatCurrency } from "../utils/formatters";

const STEPS = ["Shipping", "Review", "Payment"];

export default function CheckoutPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuthStore();
  const { items, subtotal, fetchCart, resetCart } = useCartStore();

  const [currentStep, setCurrentStep] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [orderResult, setOrderResult] = useState(null);

  const [shippingData, setShippingData] = useState({
    shipping_full_name: user?.full_name || "",
    shipping_phone: user?.phone || "",
    shipping_address_line1: "",
    shipping_address_line2: "",
    shipping_city: "",
    shipping_state: "",
    shipping_postal_code: "",
    shipping_country: "US",
    customer_notes: "",
  });

  const [savedAddresses, setSavedAddresses] = useState([]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login?redirect=/checkout");
      return;
    }
    fetchCart();
    fetchSavedAddresses();
  }, [isAuthenticated, navigate, fetchCart]);

  const fetchSavedAddresses = async () => {
    try {
      const response = await apiClient.get("/auth/addresses/");
      setSavedAddresses(response.data.results || response.data || []);
    } catch {
      // Non-critical error, user can still enter address manually
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setShippingData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSelectAddress = (address) => {
    setShippingData({
      shipping_full_name: address.full_name,
      shipping_phone: address.phone || "",
      shipping_address_line1: address.address_line1,
      shipping_address_line2: address.address_line2 || "",
      shipping_city: address.city,
      shipping_state: address.state,
      shipping_postal_code: address.postal_code,
      shipping_country: address.country,
      customer_notes: shippingData.customer_notes,
    });
  };

  const validateShipping = () => {
    const required = [
      "shipping_full_name",
      "shipping_address_line1",
      "shipping_city",
      "shipping_state",
      "shipping_postal_code",
    ];
    for (const field of required) {
      if (!shippingData[field]?.trim()) {
        setError(`Please fill in the ${field.replace(/shipping_|_/g, " ").trim()} field.`);
        return false;
      }
    }
    setError(null);
    return true;
  };

  const handleNext = () => {
    if (currentStep === 0 && !validateShipping()) return;
    setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  };

  const handleBack = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  const handlePlaceOrder = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      const response = await apiClient.post("/orders/create/", shippingData);
      setOrderResult(response.data);
      resetCart();
      setCurrentStep(STEPS.length); // Move past final step to success
    } catch (err) {
      const errorData = err.response?.data;
      if (errorData?.stock_errors) {
        setError(errorData.stock_errors.join(" "));
      } else if (errorData?.detail) {
        setError(errorData.detail);
      } else if (typeof errorData === "string") {
        setError(errorData);
      } else {
        setError("Failed to place order. Please try again.");
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const numericSubtotal = parseFloat(subtotal) || 0;

  // Order success screen
  if (orderResult) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Order Placed!</h1>
        <p className="text-gray-500 mb-2">
          Your order <span className="font-semibold text-gray-900">{orderResult.order_number}</span> has been placed successfully.
        </p>
        <p className="text-gray-500 mb-8">We'll send you a confirmation email shortly.</p>
        <div className="flex justify-center gap-4">
          <button
            onClick={() => navigate(`/orders/${orderResult.id}`)}
            className="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700"
          >
            View Order
          </button>
          <button
            onClick={() => navigate("/products")}
            className="px-6 py-3 border border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50"
          >
            Continue Shopping
          </button>
        </div>
      </div>
    );
  }

  // Redirect if cart is empty
  if (items.length === 0 && !isProcessing) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Your cart is empty</h1>
        <button onClick={() => navigate("/products")} className="text-indigo-600 hover:text-indigo-700 font-medium">
          Browse products
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Progress Steps */}
      <div className="flex items-center justify-center mb-10">
        {STEPS.map((step, idx) => (
          <div key={step} className="flex items-center">
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${
              idx <= currentStep ? "bg-indigo-600 text-white" : "bg-gray-200 text-gray-500"
            }`}>
              {idx < currentStep ? (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                idx + 1
              )}
            </div>
            <span className={`ml-2 text-sm font-medium ${idx <= currentStep ? "text-indigo-600" : "text-gray-500"}`}>
              {step}
            </span>
            {idx < STEPS.length - 1 && (
              <div className={`w-12 h-0.5 mx-3 ${idx < currentStep ? "bg-indigo-600" : "bg-gray-200"}`} />
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6 text-sm">{error}</div>
      )}

      {/* Step 1: Shipping Address */}
      {currentStep === 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Shipping Address</h2>

          {savedAddresses.length > 0 && (
            <div className="mb-6">
              <p className="text-sm font-medium text-gray-700 mb-2">Saved Addresses</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {savedAddresses.map((addr) => (
                  <button
                    key={addr.id}
                    onClick={() => handleSelectAddress(addr)}
                    className="text-left p-3 border border-gray-200 rounded-lg hover:border-indigo-300 hover:bg-indigo-50 transition-colors text-sm"
                  >
                    <p className="font-medium">{addr.full_name}</p>
                    <p className="text-gray-500">{addr.address_line1}, {addr.city}, {addr.state}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
              <input type="text" name="shipping_full_name" value={shippingData.shipping_full_name}
                onChange={handleInputChange} required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Address Line 1 *</label>
              <input type="text" name="shipping_address_line1" value={shippingData.shipping_address_line1}
                onChange={handleInputChange} required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Address Line 2</label>
              <input type="text" name="shipping_address_line2" value={shippingData.shipping_address_line2}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">City *</label>
              <input type="text" name="shipping_city" value={shippingData.shipping_city}
                onChange={handleInputChange} required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">State *</label>
              <input type="text" name="shipping_state" value={shippingData.shipping_state}
                onChange={handleInputChange} required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Postal Code *</label>
              <input type="text" name="shipping_postal_code" value={shippingData.shipping_postal_code}
                onChange={handleInputChange} required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input type="tel" name="shipping_phone" value={shippingData.shipping_phone}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Order Notes</label>
              <textarea name="customer_notes" value={shippingData.customer_notes}
                onChange={handleInputChange} rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Any special instructions for delivery..." />
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Review */}
      {currentStep === 1 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Review Your Order</h2>
          <div className="space-y-4 mb-6">
            {items.map((item) => (
              <div key={item.id} className="flex items-center gap-4 py-3 border-b border-gray-100 last:border-0">
                <div className="w-16 h-16 bg-gray-100 rounded flex-shrink-0 overflow-hidden">
                  {item.product_image && <img src={item.product_image} alt="" className="w-full h-full object-cover" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{item.product_name}</p>
                  <p className="text-xs text-gray-500">Qty: {item.quantity}</p>
                </div>
                <p className="font-medium text-gray-900">{formatCurrency(item.line_total)}</p>
              </div>
            ))}
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">Shipping To</h3>
            <p className="text-sm text-gray-600">
              {shippingData.shipping_full_name}<br />
              {shippingData.shipping_address_line1}<br />
              {shippingData.shipping_address_line2 && <>{shippingData.shipping_address_line2}<br /></>}
              {shippingData.shipping_city}, {shippingData.shipping_state} {shippingData.shipping_postal_code}
            </p>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between"><span>Subtotal</span><span>{formatCurrency(numericSubtotal)}</span></div>
            <div className="flex justify-between"><span>Shipping</span><span>{numericSubtotal >= 50 ? "Free" : formatCurrency(5.99)}</span></div>
            <div className="flex justify-between font-semibold text-base border-t pt-2 mt-2">
              <span>Total</span>
              <span>{formatCurrency(numericSubtotal + (numericSubtotal >= 50 ? 0 : 5.99))}</span>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Payment */}
      {currentStep === 2 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Complete Your Purchase</h2>
          <p className="text-gray-500 mb-8">
            Click the button below to place your order. Payment will be processed securely via Stripe.
          </p>
          <button
            onClick={handlePlaceOrder}
            disabled={isProcessing}
            className="px-8 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isProcessing ? "Processing..." : `Place Order - ${formatCurrency(numericSubtotal + (numericSubtotal >= 50 ? 0 : 5.99))}`}
          </button>
        </div>
      )}

      {/* Navigation Buttons */}
      {currentStep < STEPS.length && (
        <div className="flex justify-between mt-6">
          <button
            onClick={currentStep === 0 ? () => navigate("/cart") : handleBack}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
          >
            {currentStep === 0 ? "Back to Cart" : "Back"}
          </button>
          {currentStep < STEPS.length - 1 && (
            <button
              onClick={handleNext}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium"
            >
              Continue
            </button>
          )}
        </div>
      )}
    </div>
  );
}
