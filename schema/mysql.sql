-- All timestamps will be stored in UTC and IDs are shared with MongoDB, Redis, and Neo4j.

CREATE DATABASE IF NOT EXISTS ecommerce
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecommerce;

-- 1. Users
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
);

-- 2. Saved addresses
CREATE TABLE IF NOT EXISTS addresses (
    address_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    recipient_name VARCHAR(150) NOT NULL,
    line1 VARCHAR(255) NOT NULL,
    line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    region VARCHAR(100),
    postal_code VARCHAR(20) NOT NULL,
    country_code CHAR(2) NOT NULL,
    INDEX idx_addresses_user (user_id),
    CONSTRAINT fk_addresses_user FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

-- 3. Categories
CREATE TABLE IF NOT EXISTS categories (
    category_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE
);

-- 4. Core product catalog; flexible specifications live in MongoDB
CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    base_price DECIMAL(10,2) NOT NULL,
    return_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    return_window_days SMALLINT UNSIGNED NOT NULL DEFAULT 30,
    restocking_fee_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_products_category (category_id),
    CONSTRAINT chk_products_price CHECK (base_price >= 0),
    CONSTRAINT chk_restocking_percent CHECK
        (restocking_fee_percent BETWEEN 0 AND 100),
    CONSTRAINT fk_products_category FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
);

-- 5. Sellable variants with authoritative per-variant stock
CREATE TABLE IF NOT EXISTS product_variants (
    variant_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT UNSIGNED NOT NULL,
    sku VARCHAR(100) NOT NULL UNIQUE,
    size VARCHAR(50),
    color VARCHAR(80),
    price DECIMAL(10,2) NOT NULL,
    stock_quantity INT UNSIGNED NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    INDEX idx_variants_product (product_id),
    INDEX idx_variants_stock (stock_quantity),
    INDEX idx_variants_color_stock (color, stock_quantity),
    INDEX idx_variants_size_stock (size, stock_quantity),
    CONSTRAINT chk_variants_price CHECK (price >= 0),
    CONSTRAINT fk_variants_product FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);

-- 6. Durable carts, including abandoned and converted carts
CREATE TABLE IF NOT EXISTS carts (
    cart_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    status ENUM('active', 'converted', 'abandoned') NOT NULL DEFAULT 'active',
    last_device VARCHAR(50),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_carts_user_status (user_id, status),
    INDEX idx_carts_created (created_at),
    CONSTRAINT fk_carts_user FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

-- 7. Cart contents (Redis holds a cache, not the source of truth)
CREATE TABLE IF NOT EXISTS cart_items (
    cart_id BIGINT UNSIGNED NOT NULL,
    variant_id BIGINT UNSIGNED NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    added_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (cart_id, variant_id),
    INDEX idx_cart_items_variant (variant_id),
    CONSTRAINT chk_cart_quantity CHECK (quantity > 0),
    CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id)
        REFERENCES carts(cart_id) ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_variant FOREIGN KEY (variant_id)
        REFERENCES product_variants(variant_id)
);

-- 8. Available shipping services
CREATE TABLE IF NOT EXISTS shipping_options (
    shipping_option_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    base_cost DECIMAL(10,2) NOT NULL,
    min_delivery_days SMALLINT UNSIGNED NOT NULL,
    max_delivery_days SMALLINT UNSIGNED NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_shipping_cost CHECK (base_cost >= 0),
    CONSTRAINT chk_shipping_days CHECK
        (min_delivery_days <= max_delivery_days)
);

-- 9. Orders link back to their originating carts for conversion analysis
CREATE TABLE IF NOT EXISTS orders (
    order_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    cart_id BIGINT UNSIGNED NOT NULL UNIQUE,
    shipping_address_id BIGINT UNSIGNED NOT NULL,
    billing_address_id BIGINT UNSIGNED,
    shipping_option_id BIGINT UNSIGNED NOT NULL,
    status ENUM('placed', 'paid', 'processing', 'shipped', 'delivered',
                'cancelled') NOT NULL DEFAULT 'placed',
    placed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    subtotal DECIMAL(12,2) NOT NULL,
    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    shipping_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(12,2) NOT NULL,
    expected_ship_date DATE,
    expected_delivery_date DATE,
    shipped_at DATETIME(6),
    delivered_at DATETIME(6),
    tracking_number VARCHAR(120),
    INDEX idx_orders_user_date (user_id, placed_at),
    INDEX idx_orders_status (status),
    CONSTRAINT chk_orders_amounts CHECK
        (subtotal >= 0 AND tax_amount >= 0 AND shipping_amount >= 0
         AND total_amount = subtotal + tax_amount + shipping_amount),
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    CONSTRAINT fk_orders_cart FOREIGN KEY (cart_id)
        REFERENCES carts(cart_id),
    CONSTRAINT fk_orders_shipping_address FOREIGN KEY (shipping_address_id)
        REFERENCES addresses(address_id),
    CONSTRAINT fk_orders_billing_address FOREIGN KEY (billing_address_id)
        REFERENCES addresses(address_id),
    CONSTRAINT fk_orders_shipping_option FOREIGN KEY (shipping_option_id)
        REFERENCES shipping_options(shipping_option_id)
);

-- 10. Historical order-item prices and product-name snapshots
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    variant_id BIGINT UNSIGNED NOT NULL,
    product_name_snapshot VARCHAR(200) NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    INDEX idx_order_items_order (order_id),
    INDEX idx_order_items_variant (variant_id),
    CONSTRAINT chk_order_item_quantity CHECK (quantity > 0),
    CONSTRAINT chk_order_item_price CHECK (unit_price >= 0),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id)
        REFERENCES orders(order_id),
    CONSTRAINT fk_order_items_variant FOREIGN KEY (variant_id)
        REFERENCES product_variants(variant_id)
);

-- 11. Payments: provider tokens only; never store card numbers or CVVs
CREATE TABLE IF NOT EXISTS payments (
    payment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    method_type ENUM('credit_card', 'bank_account') NOT NULL,
    provider VARCHAR(100) NOT NULL,
    provider_token VARCHAR(255),
    provider_transaction_id VARCHAR(255) UNIQUE,
    status ENUM('pending', 'approved', 'failed', 'refunded',
                'partially_refunded') NOT NULL DEFAULT 'pending',
    amount DECIMAL(12,2) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    paid_at DATETIME(6),
    INDEX idx_payments_order (order_id),
    CONSTRAINT chk_payment_amount CHECK (amount >= 0),
    CONSTRAINT fk_payments_order FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
);

-- 12. Item-level refunds and exchanges, including return shipping
CREATE TABLE IF NOT EXISTS `returns` (
    return_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_item_id BIGINT UNSIGNED NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    resolution ENUM('refund', 'exchange') NOT NULL,
    exchange_variant_id BIGINT UNSIGNED,
    status ENUM('requested', 'label_issued', 'in_transit', 'received',
                'completed', 'rejected') NOT NULL DEFAULT 'requested',
    refund_status ENUM('not_applicable', 'pending', 'processed', 'failed')
        NOT NULL DEFAULT 'not_applicable',
    exchange_status ENUM('not_applicable', 'pending', 'shipped', 'completed',
                         'failed') NOT NULL DEFAULT 'not_applicable',
    refund_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    restocking_fee DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    return_shipping_method VARCHAR(100),
    return_tracking_number VARCHAR(120),
    return_label_url VARCHAR(500),
    requested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    completed_at DATETIME(6),
    INDEX idx_returns_order_item (order_item_id),
    CONSTRAINT chk_return_quantity CHECK (quantity > 0),
    CONSTRAINT chk_return_amounts CHECK
        (refund_amount >= 0 AND restocking_fee >= 0),
    CONSTRAINT fk_returns_order_item FOREIGN KEY (order_item_id)
        REFERENCES order_items(order_item_id),
    CONSTRAINT fk_returns_exchange_variant FOREIGN KEY (exchange_variant_id)
        REFERENCES product_variants(variant_id)
);

-- 13. Minimal transactional outbox for reliable cross-store updates
CREATE TABLE IF NOT EXISTS outbox_events (
    event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT UNSIGNED NOT NULL,
    payload JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    processed_at DATETIME(6),
    attempts INT UNSIGNED NOT NULL DEFAULT 0,
    last_error TEXT,
    INDEX idx_outbox_pending (processed_at, event_id)
);
