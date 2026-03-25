/**
 * ProductDetailPage for MegaStore.
 *
 * Displays full product information including image gallery, pricing,
 * vendor details, specifications, reviews, and add-to-cart controls.
 */

import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useProduct, useCreateReview } from "../hooks/useProducts";
import useCartStore from "../store/cartStore";
import useAuthStore from "../store/authStore";
import {
  formatCurrency,
  formatDate,
  formatRating,
  formatRelativeTime,
} from "../utils/formatters";

export default function ProductDetailPage() {
  const { slug } = useParams();
  const { data: product, isLoading, error } = useProduct(slug);
  const addItem = useCartStore((state) => state.addItem);
  const { isAuthenticated, user } = useAuthStore();
  const createReview = useCreateReview(slug);

  const [selectedImage, setSelectedImage] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [isAddingToCart, setIsAddingToCart] = useState(false);
  const [activeTab, setActiveTab] = useState("description");

  // Review form state
  const [reviewData, setReviewData] = useState({ rating: 5, title: "", comment: "" });
  const [reviewError, setReviewError] = useState(null);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="animate-pulse bg-gray-200 rounded-lg aspect-square" />
          <div className="animate-pulse space-y-4">
            <div className="bg-gray-200 h-8 rounded w-3/4" />
            <div className="bg-gray-200 h-6 rounded w-1/4" />
            <div className="bg-gray-200 h-24 rounded" />
            <div className="bg-gray-200 h-12 rounded w-1/2" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Product Not Found</h1>
        <p className="text-gray-500 mb-8">The product you're looking for doesn't exist or has been removed.</p>
        <Link to="/products" className="text-indigo-600 hover:text-indigo-700 font-medium">
          Browse All Products
        </Link>
      </div>
    );
  }

  const images = product.images || [];
  const hasDiscount = product.compare_at_price && product.discount_percentage > 0;

  const handleAddToCart = async () => {
    setIsAddingToCart(true);
    await addItem(product.id, quantity);
    setIsAddingToCart(false);
  };

  const handleQuantityChange = (delta) => {
    const newQty = quantity + delta;
    if (newQty >= 1 && newQty <= (product.stock_quantity || 999)) {
      setQuantity(newQty);
    }
  };

  const handleSubmitReview = async (e) => {
    e.preventDefault();
    setReviewError(null);
    try {
      await createReview.mutateAsync(reviewData);
      setReviewData({ rating: 5, title: "", comment: "" });
    } catch (err) {
      setReviewError(
        err.response?.data?.detail ||
        err.response?.data?.[0] ||
        "Failed to submit review."
      );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link to="/" className="hover:text-indigo-600">Home</Link>
        <span>/</span>
        <Link to="/products" className="hover:text-indigo-600">Products</Link>
        {product.category && (
          <>
            <span>/</span>
            <Link to={`/products?category=${product.category.slug}`} className="hover:text-indigo-600">
              {product.category.name}
            </Link>
          </>
        )}
        <span>/</span>
        <span className="text-gray-900 font-medium truncate">{product.name}</span>
      </nav>

      {/* Product Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
        {/* Image Gallery */}
        <div>
          <div className="aspect-square rounded-lg overflow-hidden bg-gray-100 mb-4">
            {images.length > 0 ? (
              <img
                src={images[selectedImage]?.image}
                alt={images[selectedImage]?.alt_text || product.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-400">
                <span className="text-lg">No Image Available</span>
              </div>
            )}
          </div>
          {images.length > 1 && (
            <div className="flex gap-2 overflow-x-auto">
              {images.map((img, idx) => (
                <button
                  key={img.id}
                  onClick={() => setSelectedImage(idx)}
                  className={`flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-colors ${
                    idx === selectedImage ? "border-indigo-600" : "border-gray-200 hover:border-gray-400"
                  }`}
                >
                  <img src={img.image} alt={img.alt_text || ""} className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Product Info */}
        <div>
          {/* Vendor */}
          {product.vendor && (
            <Link
              to={`/vendors/${product.vendor.slug}`}
              className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
            >
              {product.vendor.store_name}
            </Link>
          )}

          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mt-1 mb-2">
            {product.name}
          </h1>

          {/* Rating */}
          <div className="flex items-center gap-2 mb-4">
            <div className="flex">
              {[1, 2, 3, 4, 5].map((star) => (
                <svg
                  key={star}
                  className={`w-5 h-5 ${star <= Math.round(product.average_rating) ? "text-yellow-400" : "text-gray-200"}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
            </div>
            <span className="text-sm text-gray-600">
              {formatRating(product.average_rating)} ({product.review_count} reviews)
            </span>
            <span className="text-sm text-gray-400">|</span>
            <span className="text-sm text-gray-500">{product.total_sold} sold</span>
          </div>

          {/* Price */}
          <div className="flex items-baseline gap-3 mb-6">
            <span className="text-3xl font-bold text-gray-900">
              {formatCurrency(product.price)}
            </span>
            {hasDiscount && (
              <>
                <span className="text-xl text-gray-400 line-through">
                  {formatCurrency(product.compare_at_price)}
                </span>
                <span className="text-sm font-semibold text-red-600 bg-red-50 px-2 py-1 rounded">
                  Save {product.discount_percentage}%
                </span>
              </>
            )}
          </div>

          {/* Short Description */}
          {product.short_description && (
            <p className="text-gray-600 mb-6">{product.short_description}</p>
          )}

          {/* Stock Status */}
          <div className="mb-6">
            {product.is_in_stock ? (
              <span className="text-green-600 font-medium">In Stock</span>
            ) : (
              <span className="text-red-600 font-medium">Out of Stock</span>
            )}
            {product.is_low_stock && product.is_in_stock && (
              <span className="ml-2 text-orange-500 text-sm">
                (Only {product.stock_quantity} left!)
              </span>
            )}
          </div>

          {/* Quantity & Add to Cart */}
          {product.is_in_stock && (
            <div className="flex items-center gap-4 mb-6">
              <div className="flex items-center border border-gray-300 rounded-lg">
                <button
                  onClick={() => handleQuantityChange(-1)}
                  disabled={quantity <= 1}
                  className="px-3 py-2 text-gray-600 hover:bg-gray-100 disabled:opacity-50 rounded-l-lg"
                >
                  -
                </button>
                <span className="px-4 py-2 text-center min-w-[3rem] font-medium">{quantity}</span>
                <button
                  onClick={() => handleQuantityChange(1)}
                  disabled={quantity >= (product.stock_quantity || 999)}
                  className="px-3 py-2 text-gray-600 hover:bg-gray-100 disabled:opacity-50 rounded-r-lg"
                >
                  +
                </button>
              </div>
              <button
                onClick={handleAddToCart}
                disabled={isAddingToCart}
                className="flex-1 bg-indigo-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAddingToCart ? "Adding..." : "Add to Cart"}
              </button>
            </div>
          )}

          {/* Product Meta */}
          <div className="border-t border-gray-200 pt-4 space-y-2 text-sm text-gray-500">
            <p><span className="font-medium text-gray-700">SKU:</span> {product.sku}</p>
            {product.brand && <p><span className="font-medium text-gray-700">Brand:</span> {product.brand}</p>}
            {product.tags && <p><span className="font-medium text-gray-700">Tags:</span> {product.tags}</p>}
          </div>
        </div>
      </div>

      {/* Tabs: Description, Reviews */}
      <div className="border-b border-gray-200 mb-8">
        <div className="flex gap-8">
          {["description", "reviews"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
                activeTab === tab
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab === "reviews" ? `Reviews (${product.review_count})` : tab}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "description" && (
        <div className="prose max-w-none mb-12">
          <p className="text-gray-700 whitespace-pre-line">{product.description}</p>
        </div>
      )}

      {activeTab === "reviews" && (
        <div className="mb-12">
          {/* Existing Reviews */}
          {product.reviews?.length > 0 ? (
            <div className="space-y-6 mb-8">
              {product.reviews.map((review) => (
                <div key={review.id} className="bg-white border border-gray-200 rounded-lg p-6">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{review.user_name}</span>
                        {review.is_verified_purchase && (
                          <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded">
                            Verified Purchase
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1 mt-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <svg
                            key={star}
                            className={`w-4 h-4 ${star <= review.rating ? "text-yellow-400" : "text-gray-200"}`}
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                        ))}
                      </div>
                    </div>
                    <span className="text-xs text-gray-400">{formatRelativeTime(review.created_at)}</span>
                  </div>
                  <h4 className="font-medium text-gray-900 mt-2">{review.title}</h4>
                  <p className="text-gray-600 text-sm mt-1">{review.comment}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 mb-8">No reviews yet. Be the first to review this product!</p>
          )}

          {/* Review Form */}
          {isAuthenticated && user?.role !== "vendor" && (
            <div className="bg-gray-50 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Write a Review</h3>
              {reviewError && (
                <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{reviewError}</div>
              )}
              <form onSubmit={handleSubmitReview} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Rating</label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setReviewData({ ...reviewData, rating: star })}
                        className="p-1"
                      >
                        <svg
                          className={`w-8 h-8 ${star <= reviewData.rating ? "text-yellow-400" : "text-gray-300"}`}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    value={reviewData.title}
                    onChange={(e) => setReviewData({ ...reviewData, title: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Summarize your experience"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Review</label>
                  <textarea
                    value={reviewData.comment}
                    onChange={(e) => setReviewData({ ...reviewData, comment: e.target.value })}
                    required
                    rows={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Share your thoughts about this product"
                  />
                </div>
                <button
                  type="submit"
                  disabled={createReview.isPending}
                  className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
                >
                  {createReview.isPending ? "Submitting..." : "Submit Review"}
                </button>
              </form>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
