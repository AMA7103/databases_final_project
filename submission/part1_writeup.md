# Part 1: Database Design

Left these notes for whoever tackles part 1 writeup:

- **MySQL:** Stores transactional data (users, products, variants, carts, orders, payments, returns) because of relational integrity and ACID transactions.
- **MongoDB:** Stores flexible category-specific product attributes and high-volume user behavior events.
- **Redis:** Provides fast session management, recently viewed products, and cart/inventory caching. MySQL remains authoritative for carts and stock.
- **Neo4j:** Models user, order, product, and category relationships for co-purchase analysis and recommendations.
- **Product variants:** Each size/color combination has its own SKU and stock quantity in MySQL.
- **Cross-device carts:** Carts are linked to user IDs in MySQL and cached in Redis, so they persist across devices and sessions.
- **Synchronization:** MySQL uses a transactional outbox to propagate changes to Redis and Neo4j. MongoDB views are periodically aggregated into Neo4j.
- **Denormalization:** Order items preserve historical prices, while Redis caches improve read performance at the cost of additional synchronization.
- **Security:** Payment provider tokens are stored instead of full card numbers; all databases share consistent identifiers.