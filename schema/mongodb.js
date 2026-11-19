const database = db.getSiblingDB("ecommerce");

// 1. Product Attributes
// Category-specific specifications and visualization metadata

const productValidator = {
  $jsonSchema: {
    bsonType: "object",
    required: ["product_id", "category_slug", "attributes"],
    properties: {
      product_id: { bsonType: ["int", "long"] },
      category_slug: { bsonType: "string" },
      attributes: { bsonType: "object" },
      image_urls: {
        bsonType: "array",
        items: { bsonType: "string" }
      },
      visualization: { bsonType: "object" }
    }
  }
};

// 2. User Behavior Events
// Product views, searches, clicks, and cart interactions

const eventValidator = {
  $jsonSchema: {
    bsonType: "object",
    required: ["event_id", "user_id", "event_type", "occurred_at"],
    properties: {
      event_id: { bsonType: ["int", "long"] },
      user_id: { bsonType: ["int", "long"] },
      product_id: { bsonType: ["int", "long"] },
      cart_id: { bsonType: ["int", "long"] },
      session_id: { bsonType: "string" },
      event_type: {
        enum: [
          "product_view",
          "product_click",
          "search",
          "cart_add",
          "cart_remove",
          "cart_update"
        ]
      },
      occurred_at: { bsonType: "date" },
      device: { bsonType: "string" },
      search_term: { bsonType: "string" },
      duration_ms: {
        bsonType: ["int", "long"],
        minimum: 0
      }
    }
  }
};

// Create collections and apply validators
// Safe to run again without deleting existing data

for (const [name, validator] of [
  ["product_attributes", productValidator],
  ["events", eventValidator]
]) {
  if (!database.getCollectionNames().includes(name)) {
    database.createCollection(name);
  }

  database.runCommand({
    collMod: name,
    validator: validator,
    validationLevel: "strict",
    validationAction: "error"
  });
}

// 3. Indexes

// One attributes document per MySQL product
database.product_attributes.createIndex(
  { product_id: 1 },
  { unique: true }
);

// Unique event identifiers
database.events.createIndex(
  { event_id: 1 },
  { unique: true }
);

// Sarah's recent views and search history
database.events.createIndex(
  { user_id: 1, event_type: 1, occurred_at: -1 }
);

// Product page view counts
database.events.createIndex(
  { event_type: 1, product_id: 1 }
);

print("MongoDB collections, validators, and indexes initialized.");
