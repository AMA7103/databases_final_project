 // Unique identifiers
 CREATE CONSTRAINT user_id_unique IF NOT EXISTS
 FOR (u:User)
 REQUIRE u.user_id IS UNIQUE;

 CREATE CONSTRAINT order_id_unique IF NOT EXISTS
 FOR (o:Order)
 REQUIRE o.order_id IS UNIQUE;

 CREATE CONSTRAINT product_id_unique IF NOT EXISTS
 FOR (p:Product)
 REQUIRE p.product_id IS UNIQUE;

 CREATE CONSTRAINT category_id_unique IF NOT EXISTS
 FOR (c:Category)
 REQUIRE c.category_id IS UNIQUE;

 // Category lookup index
 CREATE INDEX category_name_idx IF NOT EXISTS
 FOR (c:Category)
 ON (c.name);
