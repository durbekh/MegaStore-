# MegaStore - E-Commerce Marketplace Platform

## Overview

MegaStore is a full-featured, production-grade e-commerce marketplace platform where multiple vendors can register, list products, and sell to customers worldwide. Think of it as a self-hosted Amazon or AliExpress -- a multi-vendor marketplace with complete order management, payment processing, real-time notifications, and an advanced product search engine.

The platform is built with a modern, scalable architecture using Django REST Framework on the backend, React with Redux on the frontend, and a suite of battle-tested infrastructure services including PostgreSQL, Redis, Celery, Elasticsearch, Stripe, and Nginx, all orchestrated with Docker Compose.

---

## Project Goal

To provide a complete, deployable, and extensible marketplace solution that handles every aspect of e-commerce operations: user management across multiple roles (admin, vendor, customer), product catalog management with full-text search, shopping cart and checkout workflows, secure payment processing via Stripe, asynchronous order processing, and real-time email notifications.

---

## Key Features

### For Customers
- Browse and search products with advanced filtering (category, price range, rating, vendor)
- Full-text search powered by Elasticsearch with autocomplete and relevance scoring
- Persistent shopping cart with real-time stock validation
- Secure checkout with Stripe payment integration
- Order history and tracking
- Product reviews and ratings
- User profile management with address book

### For Vendors
- Vendor registration and profile management
- Product catalog management (CRUD with image uploads)
- Order management dashboard with fulfillment workflows
- Sales analytics and revenue tracking
- Inventory management with low-stock alerts
- Payout tracking via Stripe Connect

### For Administrators
- Full admin dashboard with platform-wide analytics
- User, vendor, and product moderation
- Order oversight and dispute resolution
- Platform configuration and fee management
- Vendor approval workflow

### Platform-Wide
- JWT-based authentication with token refresh
- Role-based access control (RBAC)
- Asynchronous task processing (email, payments, analytics) via Celery
- Redis-backed caching and session management
- Comprehensive RESTful API with OpenAPI/Swagger documentation
- Responsive React frontend with Redux state management
- Dockerized deployment with Nginx reverse proxy
- Production-ready logging, error handling, and monitoring hooks

---

## Architecture

```
                           +-------------------+
                           |     Nginx         |
                           | (Reverse Proxy)   |
                           +---------+---------+
                                     |
                     +---------------+---------------+
                     |                               |
              +------+------+               +-------+-------+
              |   React     |               |   Django      |
              |   Frontend  |               |   REST API    |
              |  (Port 3000)|               |  (Port 8000)  |
              +-------------+               +---+---+---+---+
                                                |   |   |
                          +---------------------+   |   +--------------------+
                          |                         |                        |
                   +------+------+          +-------+-------+        +------+------+
                   | PostgreSQL  |          |     Redis     |        | Elasticsearch|
                   |  (Port 5432)|          |  (Port 6379)  |        |  (Port 9200) |
                   +-------------+          +-------+-------+        +--------------+
                                                    |
                                            +-------+-------+
                                            |    Celery     |
                                            |   Workers     |
                                            +-------+-------+
                                                    |
                                            +-------+-------+
                                            |    Stripe     |
                                            |   (Payments)  |
                                            +---------------+
```

### Data Flow

1. **Client requests** hit Nginx, which routes to either the React frontend (static assets) or the Django API (`/api/` prefix).
2. **Django REST Framework** handles all API logic: authentication, serialization, validation, and business rules.
3. **PostgreSQL** stores all relational data (users, products, orders, payments).
4. **Redis** provides caching (product listings, sessions), message brokering for Celery, and rate-limiting support.
5. **Celery** workers process background tasks: sending emails, processing payments, syncing search indexes, generating reports.
6. **Elasticsearch** powers the product search engine with full-text search, faceted filtering, and autocomplete.
7. **Stripe** handles all payment processing, including customer charges and vendor payouts via Connect.

---

## Tech Stack

| Layer          | Technology                          | Purpose                              |
|----------------|-------------------------------------|--------------------------------------|
| Backend        | Django 5.0, Django REST Framework   | API server, business logic, ORM      |
| Frontend       | React 18, Redux Toolkit             | Single-page application, state mgmt  |
| Database       | PostgreSQL 16                       | Primary relational data store        |
| Cache/Broker   | Redis 7                             | Caching, Celery message broker       |
| Task Queue     | Celery 5                            | Async task processing                |
| Search Engine  | Elasticsearch 8                     | Full-text product search             |
| Payments       | Stripe API                          | Payment processing, vendor payouts   |
| Web Server     | Nginx                               | Reverse proxy, static file serving   |
| Containerization | Docker, Docker Compose            | Development and deployment           |
| Authentication | JWT (SimpleJWT)                     | Stateless token-based auth           |

---

## Folder Structure

```
megastore/
|-- README.md
|-- docker-compose.yml
|-- .env.example
|-- .gitignore
|-- Makefile
|
|-- backend/
|   |-- manage.py
|   |-- requirements.txt
|   |-- config/
|   |   |-- __init__.py
|   |   |-- settings/
|   |   |   |-- __init__.py
|   |   |   |-- base.py
|   |   |   |-- development.py
|   |   |   |-- production.py
|   |   |-- urls.py
|   |   |-- wsgi.py
|   |   |-- asgi.py
|   |   |-- celery.py
|   |
|   |-- apps/
|   |   |-- __init__.py
|   |   |-- accounts/          # User management, authentication, profiles
|   |   |-- products/          # Product catalog, categories, reviews
|   |   |-- orders/            # Order processing, fulfillment
|   |   |-- cart/              # Shopping cart
|   |   |-- payments/          # Stripe integration, transactions
|   |   |-- notifications/     # Email and in-app notifications
|   |
|   |-- utils/
|       |-- __init__.py
|       |-- pagination.py
|       |-- permissions.py
|       |-- exceptions.py
|
|-- frontend/
|   |-- package.json
|   |-- public/
|   |   |-- index.html
|   |-- src/
|       |-- index.js
|       |-- App.jsx
|       |-- api/               # Axios API client modules
|       |-- components/        # Reusable React components
|       |   |-- layout/        # Header, Footer, Sidebar
|       |   |-- products/      # Product cards, lists, detail, search
|       |   |-- cart/           # Cart drawer, cart items
|       |   |-- checkout/      # Checkout form
|       |   |-- auth/          # Login, register forms
|       |-- pages/             # Route-level page components
|       |-- store/             # Redux slices and store
|       |-- hooks/             # Custom React hooks
|       |-- styles/            # Global CSS
|
|-- nginx/
    |-- nginx.conf
    |-- Dockerfile
```

---

## Setup Instructions

### Prerequisites

- Docker and Docker Compose (v2.0+)
- Git
- (Optional) Node.js 18+ and Python 3.11+ for local development without Docker

### Quick Start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/your-org/megastore.git
cd megastore

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your Stripe keys and other secrets

# 3. Build and start all services
make build
make up

# 4. Run database migrations
make migrate

# 5. Create a superuser
make superuser

# 6. Seed sample data (optional)
make seed

# The application is now available:
# - Frontend: http://localhost
# - API: http://localhost/api/
# - Admin: http://localhost/api/admin/
```

### Local Development (Without Docker)

#### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable for development settings
export DJANGO_SETTINGS_MODULE=config.settings.development

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
# Frontend available at http://localhost:3000
```

### Environment Variables

See `.env.example` for all required and optional environment variables. At minimum, you need:

- `SECRET_KEY` -- Django secret key
- `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` -- Stripe API keys
- `DATABASE_URL` or individual `POSTGRES_*` variables
- `REDIS_URL`
- `ELASTICSEARCH_URL`

---

## API Documentation

### Authentication

All authenticated endpoints require a JWT token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

| Endpoint                      | Method | Description                | Auth Required |
|-------------------------------|--------|----------------------------|---------------|
| `/api/auth/register/`         | POST   | Register a new user        | No            |
| `/api/auth/login/`            | POST   | Obtain JWT token pair      | No            |
| `/api/auth/token/refresh/`    | POST   | Refresh access token       | No            |
| `/api/auth/profile/`          | GET    | Get current user profile   | Yes           |
| `/api/auth/profile/`          | PATCH  | Update user profile        | Yes           |

### Products

| Endpoint                           | Method | Description                     | Auth Required |
|------------------------------------|--------|---------------------------------|---------------|
| `/api/products/`                   | GET    | List all products (paginated)   | No            |
| `/api/products/`                   | POST   | Create a new product            | Vendor        |
| `/api/products/{slug}/`            | GET    | Get product detail              | No            |
| `/api/products/{slug}/`            | PUT    | Update product                  | Vendor/Owner  |
| `/api/products/{slug}/`            | DELETE | Delete product                  | Vendor/Owner  |
| `/api/products/{slug}/reviews/`    | GET    | List product reviews            | No            |
| `/api/products/{slug}/reviews/`    | POST   | Create a review                 | Customer      |
| `/api/products/categories/`        | GET    | List all categories             | No            |
| `/api/products/search/`            | GET    | Full-text search                | No            |

### Cart

| Endpoint                  | Method | Description              | Auth Required |
|---------------------------|--------|--------------------------|---------------|
| `/api/cart/`              | GET    | Get current cart          | Yes           |
| `/api/cart/items/`        | POST   | Add item to cart          | Yes           |
| `/api/cart/items/{id}/`   | PATCH  | Update item quantity      | Yes           |
| `/api/cart/items/{id}/`   | DELETE | Remove item from cart     | Yes           |
| `/api/cart/clear/`        | POST   | Clear entire cart         | Yes           |

### Orders

| Endpoint                      | Method | Description                  | Auth Required |
|-------------------------------|--------|------------------------------|---------------|
| `/api/orders/`                | GET    | List user's orders           | Yes           |
| `/api/orders/`                | POST   | Create order from cart       | Customer      |
| `/api/orders/{id}/`           | GET    | Get order detail             | Yes           |
| `/api/orders/{id}/cancel/`    | POST   | Cancel an order              | Customer      |
| `/api/orders/vendor/`         | GET    | List vendor's received orders| Vendor        |
| `/api/orders/{id}/fulfill/`   | POST   | Mark order as fulfilled      | Vendor        |

### Payments

| Endpoint                              | Method | Description                    | Auth Required |
|---------------------------------------|--------|--------------------------------|---------------|
| `/api/payments/create-intent/`        | POST   | Create Stripe payment intent   | Yes           |
| `/api/payments/confirm/`              | POST   | Confirm payment                | Yes           |
| `/api/payments/webhook/`              | POST   | Stripe webhook handler         | No            |

---

## User Roles and Permissions

### Customer (default role)
- Browse and search products
- Add/remove items to cart
- Place orders and make payments
- View order history
- Write product reviews (one per product, only for purchased products)
- Manage profile and addresses

### Vendor
- All customer permissions
- Create, update, and delete own products
- Upload product images
- View and fulfill received orders
- Access sales dashboard and analytics
- Manage inventory and pricing

### Admin (superuser)
- Full platform access
- Approve/reject vendor registrations
- Moderate products and reviews
- Manage all orders and payments
- Access Django admin panel
- Platform configuration

---

## Business Logic

### Order Lifecycle

```
PENDING --> CONFIRMED --> PROCESSING --> SHIPPED --> DELIVERED
    |           |              |
    +-----------+--------------+-------> CANCELLED
                                           |
                                           +--> REFUNDED
```

1. **PENDING**: Order created, awaiting payment confirmation.
2. **CONFIRMED**: Payment received via Stripe; stock decremented.
3. **PROCESSING**: Vendor acknowledged and is preparing the order.
4. **SHIPPED**: Order dispatched; tracking information available.
5. **DELIVERED**: Order received by customer.
6. **CANCELLED**: Order cancelled by customer or admin (before shipping).
7. **REFUNDED**: Payment refunded via Stripe after cancellation.

### Payment Flow

1. Customer completes checkout; a Stripe PaymentIntent is created.
2. Frontend confirms payment using Stripe.js Elements.
3. Stripe webhook notifies the backend of payment success/failure.
4. On success: order status moves to CONFIRMED, stock is decremented, confirmation email is sent.
5. On failure: order remains PENDING; customer is notified to retry.

### Multi-Vendor Order Splitting

When a customer orders products from multiple vendors, the system:
1. Creates a parent order for the customer.
2. Splits into sub-orders (OrderItems grouped by vendor).
3. Each vendor sees only their portion of the order.
4. Payments are split accordingly via Stripe Connect (platform fee deducted).

### Inventory Management

- Stock is validated at cart-add and again at checkout.
- Stock is decremented atomically on order confirmation using database-level locks.
- Low-stock alerts are sent to vendors via Celery tasks.
- Out-of-stock products are automatically hidden from search results.

### Search and Discovery

- Elasticsearch indexes product title, description, category, tags, and vendor name.
- Search supports fuzzy matching, synonyms, and relevance boosting.
- Filters: category, price range, rating, vendor, availability.
- Results are sorted by relevance, with options for price and rating sorting.

---

## Roadmap

### Phase 1 (Current) -- Core Platform
- [x] User authentication and authorization (JWT)
- [x] Vendor registration and management
- [x] Product catalog with categories and images
- [x] Shopping cart
- [x] Checkout and Stripe payment integration
- [x] Order management and lifecycle
- [x] Product search with Elasticsearch
- [x] Email notifications via Celery
- [x] Docker Compose deployment

### Phase 2 -- Enhanced Experience
- [ ] Real-time notifications via WebSockets (Django Channels)
- [ ] Product wishlists and favorites
- [ ] Advanced analytics dashboard (vendor and admin)
- [ ] Coupon and discount code system
- [ ] Product variations (size, color, etc.)
- [ ] Bulk product import/export (CSV)

### Phase 3 -- Scale and Optimize
- [ ] CDN integration for media files (AWS S3 + CloudFront)
- [ ] Kubernetes deployment manifests
- [ ] API rate limiting and throttling
- [ ] A/B testing framework
- [ ] Multi-language and multi-currency support (i18n)
- [ ] Mobile app (React Native)

### Phase 4 -- Marketplace Intelligence
- [ ] Recommendation engine (collaborative filtering)
- [ ] Fraud detection system
- [ ] Automated vendor quality scoring
- [ ] SEO optimization and sitemap generation
- [ ] Social login (Google, Facebook, Apple)

---

## Potential Improvements

- **Observability**: Integrate Prometheus + Grafana for metrics, Sentry for error tracking, and structured logging with ELK stack.
- **CI/CD**: Add GitHub Actions pipelines for automated testing, linting, security scanning, and deployment.
- **API Versioning**: Implement URL-based API versioning (`/api/v1/`, `/api/v2/`) for backward compatibility.
- **GraphQL**: Add a GraphQL endpoint (via Graphene-Django) for more flexible frontend data fetching.
- **Caching Strategy**: Implement cache invalidation patterns with Redis for hot product listings and category trees.
- **Security Hardening**: Add CORS fine-tuning, Content Security Policy headers, SQL injection protection audits, and dependency vulnerability scanning.
- **Testing**: Expand unit, integration, and end-to-end test coverage (pytest, Cypress).
- **Documentation**: Auto-generate API docs with drf-spectacular (OpenAPI 3.0).

---

## License

This project is proprietary software. All rights reserved.

---

## Contributing

Please read `CONTRIBUTING.md` for guidelines on how to contribute to this project. All contributions require a signed CLA (Contributor License Agreement).
