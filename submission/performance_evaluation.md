# Performance Evaluation

## Results

Measured at 2026-11-24T02:14:22.961048+00:00. Dataset counts were checked before timing: 10,000 users, 5,000 products, 100,000 orders, 500,000 events.

Each task was executed three times sequentially using `time.perf_counter()`, without a separate warm-up. Timings include fetching all results and application-side combination, grouping, and sorting. Connection creation, dataset-count checks, execution-plan collection, and result formatting are excluded. Lightweight query recording was enabled to capture the exact statements used. Plans were collected separately after each task’s three timed runs.

| # | Task | Stores | Run 1 (ms) | Run 2 (ms) | Run 3 (ms) | Median (ms) | Rows returned | Within 2 s |
|---|---|---|---|---|---|---|---|---|
| 1 | Fashion products with attributes | MySQL, MongoDB | 22.885 | 31.756 | 22.191 | 22.885 | 625 | Yes |
| 2 | Sarah's last 5 viewed products (6 months) | Redis, MySQL (MongoDB fallback) | 2.335 | 1.063 | 0.984 | 1.063 | 5 | Yes |
| 3 | Variants with stock under 5 | MySQL | 3.598 | 3.179 | 3.384 | 3.384 | 1,579 | Yes |
| 4 | Fashion products in blue or size Large | MySQL | 12.548 | 11.657 | 11.991 | 11.991 | 625 | Yes |
| 5 | Page-view count per product | MongoDB, MySQL | 58.321 | 54.596 | 56.899 | 56.899 | 5,000 | Yes |
| 6 | Sarah's search terms (30 days) by frequency and time of day | MongoDB | 0.792 | 0.494 | 0.473 | 0.494 | 4 | Yes |
| 7 | Active carts: device, item count, total | MySQL | 31.051 | 23.821 | 26.487 | 26.487 | 3,647 | Yes |
| 8 | Sarah's orders with items, payment, shipping, status | MySQL | 1.274 | 1.160 | 0.964 | 1.160 | 13 | Yes |
| 9 | Sarah's returns | MySQL | 0.822 | 0.664 | 0.658 | 0.664 | 2 | Yes |
| 10 | Average days between Sarah's purchases | MySQL | 0.688 | 0.597 | 0.564 | 0.597 | 1 | Yes |
| 11 | % of carts (30 days) never converted | MySQL | 10.496 | 9.993 | 10.237 | 10.237 | 1 | Yes |
| 12 | Top 3 products bought with headphones | Neo4j | 235.025 | 62.667 | 43.653 | 62.667 | 3 | Yes |
| 13 | Days since last purchase and order count, per user | MySQL | 85.689 | 82.304 | 83.893 | 83.893 | 10,000 | Yes |

All medians are below 2,000 ms; no threshold-triggered optimization or second benchmark was necessary. The query corrections address semantics rather than a measured performance bottleneck.

## Assumptions

- **Query 2:** Returns the five most recently viewed distinct products within six calendar months in UTC. Month-end dates are clamped to the last valid day of the target month. Redis and the MongoDB fallback use the same cutoff. These measured runs used Redis and MySQL; the MongoDB fallback was not exercised.
- **Query 4:** Blue means exactly `blue`; available means positive stock and active product and variant.
- **Query 6:** Time-of-day periods use UTC.
- **Query 7:** Item count sums quantities; the cart total is the merchandise subtotal at current variant prices, before checkout tax and shipping.
- **Query 8:** Selects one payment attempt per order: an approved/refunded/partially-refunded attempt takes priority, then the latest `created_at` and highest `payment_id`. If no successful attempt exists, the latest attempt is used. Orders without a payment remain visible with a null payment method. This prevents multiple payment attempts from duplicating order items.
- **Query 10:** Excludes cancelled orders.
- **Query 11:** Currently open carts without an order count as not converted as of measurement time.
- **Query 12:** Excludes cancelled orders. Counts distinct orders containing a headphones product and a different product; the other product may itself be headphones. Ties are broken by `product_id`.
- **Query 13:** Total orders includes cancelled orders; days since last purchase excludes cancelled orders. Users with no qualifying purchase have a null days-since value.

## Queries, answers, and execution plans

Answers below come from the third timed run. Tasks with at most 13 returned records show the complete answer; larger outputs show the first three records in query order and the full record count. Nested variant and item lists in displayed records are complete. Monetary decimals and timestamps are rendered as strings to preserve their values; MySQL timestamps are UTC by project convention.

MySQL plans use `EXPLAIN` with the executed SQL and parameters. MongoDB plans use `explain` with `executionStats`. Neo4j uses `PROFILE`, which executes a separate plan-collection run outside the three timed runs. Redis has no execution planner. Long arrays in plan output are shortened after ten elements and explicitly marked; execution counters are unchanged. MongoDB server metadata is omitted.

### Query 1: Fashion products with attributes

MySQL retrieves fashion products and variants; MongoDB supplies category-specific attributes. Python groups variants and attaches the documents by shared product_id.

<details>
<summary>Results: 625 records; first three records shown.</summary>

```json
[
  {
    "product_id": 2,
    "name": "Summer Dress",
    "base_price": "148.39",
    "variants": [
      {
        "variant_id": 3,
        "size": "Small",
        "color": "blue",
        "price": "152.17",
        "stock_quantity": 5
      },
      {
        "variant_id": 4,
        "size": "Medium",
        "color": "blue",
        "price": "152.93",
        "stock_quantity": 35
      },
      {
        "variant_id": 5,
        "size": "Large",
        "color": "blue",
        "price": "150.84",
        "stock_quantity": 8
      },
      {
        "variant_id": 6,
        "size": "Small",
        "color": "aqua-blue",
        "price": "149.77",
        "stock_quantity": 4
      },
      {
        "variant_id": 7,
        "size": "Medium",
        "color": "aqua-blue",
        "price": "148.92",
        "stock_quantity": 4
      },
      {
        "variant_id": 8,
        "size": "Large",
        "color": "aqua-blue",
        "price": "150.93",
        "stock_quantity": 32
      },
      {
        "variant_id": 9,
        "size": "Small",
        "color": "black",
        "price": "149.54",
        "stock_quantity": 22
      },
      {
        "variant_id": 10,
        "size": "Medium",
        "color": "black",
        "price": "150.59",
        "stock_quantity": 30
      },
      {
        "variant_id": 11,
        "size": "Large",
        "color": "black",
        "price": "149.94",
        "stock_quantity": 14
      }
    ],
    "attributes": {
      "material": "polyester",
      "style": "summer dress",
      "care_instructions": "Machine wash cold"
    }
  },
  {
    "product_id": 10,
    "name": "Summer Dress 00010",
    "base_price": "147.35",
    "variants": [
      {
        "variant_id": 21,
        "size": "Small",
        "color": "blue",
        "price": "151.20",
        "stock_quantity": 34
      },
      {
        "variant_id": 22,
        "size": "Medium",
        "color": "blue",
        "price": "150.25",
        "stock_quantity": 2
      },
      {
        "variant_id": 23,
        "size": "Large",
        "color": "blue",
        "price": "151.45",
        "stock_quantity": 0
      },
      {
        "variant_id": 24,
        "size": "Small",
        "color": "aqua-blue",
        "price": "151.82",
        "stock_quantity": 15
      },
      {
        "variant_id": 25,
        "size": "Medium",
        "color": "aqua-blue",
        "price": "151.51",
        "stock_quantity": 3
      },
      {
        "variant_id": 26,
        "size": "Large",
        "color": "aqua-blue",
        "price": "147.74",
        "stock_quantity": 3
      },
      {
        "variant_id": 27,
        "size": "Small",
        "color": "black",
        "price": "147.99",
        "stock_quantity": 28
      },
      {
        "variant_id": 28,
        "size": "Medium",
        "color": "black",
        "price": "148.27",
        "stock_quantity": 18
      },
      {
        "variant_id": 29,
        "size": "Large",
        "color": "black",
        "price": "147.57",
        "stock_quantity": 20
      }
    ],
    "attributes": {
      "material": "polyester",
      "style": "summer dress",
      "care_instructions": "Machine wash cold"
    }
  },
  {
    "product_id": 18,
    "name": "Cotton Dress 00018",
    "base_price": "146.62",
    "variants": [
      {
        "variant_id": 39,
        "size": "Small",
        "color": "blue",
        "price": "151.48",
        "stock_quantity": 31
      },
      {
        "variant_id": 40,
        "size": "Medium",
        "color": "blue",
        "price": "148.05",
        "stock_quantity": 5
      },
      {
        "variant_id": 41,
        "size": "Large",
        "color": "blue",
        "price": "147.66",
        "stock_quantity": 8
      },
      {
        "variant_id": 42,
        "size": "Small",
        "color": "aqua-blue",
        "price": "150.92",
        "stock_quantity": 33
      },
      {
        "variant_id": 43,
        "size": "Medium",
        "color": "aqua-blue",
        "price": "147.80",
        "stock_quantity": 19
      },
      {
        "variant_id": 44,
        "size": "Large",
        "color": "aqua-blue",
        "price": "150.41",
        "stock_quantity": 35
      },
      {
        "variant_id": 45,
        "size": "Small",
        "color": "black",
        "price": "147.69",
        "stock_quantity": 7
      },
      {
        "variant_id": 46,
        "size": "Medium",
        "color": "black",
        "price": "148.52",
        "stock_quantity": 9
      },
      {
        "variant_id": 47,
        "size": "Large",
        "color": "black",
        "price": "146.80",
        "stock_quantity": 15
      }
    ],
    "attributes": {
      "material": "polyester",
      "style": "summer dress",
      "care_instructions": "Machine wash cold"
    }
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT p.product_id, p.name, p.base_price,
            v.variant_id, v.size, v.color, v.price, v.stock_quantity
        FROM products p
        JOIN categories c ON c.category_id = p.category_id
        JOIN product_variants v ON v.product_id = p.product_id
        WHERE c.slug = %s
        ORDER BY p.product_id, v.variant_id
```

Parameters: `["fashion"]`.

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "c",
    "partitions": null,
    "type": "const",
    "possible_keys": "PRIMARY,slug",
    "key": "slug",
    "key_len": "402",
    "ref": "const",
    "rows": 1,
    "filtered": 100.0,
    "Extra": "Using index; Using temporary; Using filesort"
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "p",
    "partitions": null,
    "type": "ref",
    "possible_keys": "PRIMARY,idx_products_category",
    "key": "idx_products_category",
    "key_len": "8",
    "ref": "const",
    "rows": 625,
    "filtered": 100.0,
    "Extra": null
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "v",
    "partitions": null,
    "type": "ref",
    "possible_keys": "idx_variants_product",
    "key": "idx_variants_product",
    "key_len": "8",
    "ref": "ecommerce.p.product_id",
    "rows": 2,
    "filtered": 100.0,
    "Extra": null
  }
]
```

</details>

<details>
<summary>MongoDB query and execution plan</summary>

```json
{
  "find": "product_attributes",
  "filter": {
    "product_id": {
      "$in": [
        2,
        10,
        18,
        26,
        34,
        42,
        50,
        58,
        66,
        74,
        "... 615 more elements omitted"
      ]
    }
  },
  "projection": {
    "_id": 0,
    "product_id": 1,
    "attributes": 1
  }
}
```

```json
{
  "explainVersion": "1",
  "queryPlanner": {
    "namespace": "ecommerce.product_attributes",
    "parsedQuery": {
      "product_id": {
        "$in": [
          2,
          10,
          18,
          26,
          34,
          42,
          50,
          58,
          66,
          74,
          "... 615 more elements omitted"
        ]
      }
    },
    "indexFilterSet": false,
    "queryHash": "AE65514B",
    "planCacheShapeHash": "AE65514B",
    "planCacheKey": "BA67F01B",
    "optimizationTimeMillis": 0,
    "maxIndexedOrSolutionsReached": false,
    "maxIndexedAndSolutionsReached": false,
    "maxScansToExplodeReached": false,
    "prunedSimilarIndexes": false,
    "winningPlan": {
      "isCached": false,
      "stage": "PROJECTION_SIMPLE",
      "transformBy": {
        "_id": 0,
        "product_id": 1,
        "attributes": 1
      },
      "inputStage": {
        "stage": "FETCH",
        "inputStage": {
          "stage": "IXSCAN",
          "keyPattern": {
            "product_id": 1
          },
          "indexName": "product_id_1",
          "isMultiKey": false,
          "multiKeyPaths": {
            "product_id": []
          },
          "isUnique": true,
          "isSparse": false,
          "isPartial": false,
          "indexVersion": 2,
          "direction": "forward",
          "indexBounds": {
            "product_id": [
              "[2, 2]",
              "[10, 10]",
              "[18, 18]",
              "[26, 26]",
              "[34, 34]",
              "[42, 42]",
              "[50, 50]",
              "[58, 58]",
              "[66, 66]",
              "[74, 74]",
              "... 615 more elements omitted"
            ]
          }
        }
      }
    },
    "rejectedPlans": []
  },
  "executionStats": {
    "executionSuccess": true,
    "nReturned": 625,
    "executionTimeMillis": 1,
    "totalKeysExamined": 1250,
    "totalDocsExamined": 625,
    "executionStages": {
      "isCached": false,
      "stage": "PROJECTION_SIMPLE",
      "nReturned": 625,
      "executionTimeMillisEstimate": 0,
      "works": 1250,
      "advanced": 625,
      "needTime": 624,
      "needYield": 0,
      "saveState": 0,
      "restoreState": 0,
      "isEOF": 1,
      "transformBy": {
        "_id": 0,
        "product_id": 1,
        "attributes": 1
      },
      "inputStage": {
        "stage": "FETCH",
        "nReturned": 625,
        "executionTimeMillisEstimate": 0,
        "works": 1250,
        "advanced": 625,
        "needTime": 624,
        "needYield": 0,
        "saveState": 0,
        "restoreState": 0,
        "isEOF": 1,
        "docsExamined": 625,
        "alreadyHasObj": 0,
        "inputStage": {
          "stage": "IXSCAN",
          "nReturned": 625,
          "executionTimeMillisEstimate": 0,
          "works": 1250,
          "advanced": 625,
          "needTime": 624,
          "needYield": 0,
          "saveState": 0,
          "restoreState": 0,
          "isEOF": 1,
          "keyPattern": {
            "product_id": 1
          },
          "indexName": "product_id_1",
          "isMultiKey": false,
          "multiKeyPaths": {
            "product_id": []
          },
          "isUnique": true,
          "isSparse": false,
          "isPartial": false,
          "indexVersion": 2,
          "direction": "forward",
          "indexBounds": {
            "product_id": [
              "[2, 2]",
              "[10, 10]",
              "[18, 18]",
              "[26, 26]",
              "[34, 34]",
              "[42, 42]",
              "[50, 50]",
              "[58, 58]",
              "[66, 66]",
              "[74, 74]",
              "... 615 more elements omitted"
            ]
          },
          "keysExamined": 1250,
          "seeks": 625,
          "dupsTested": 0,
          "dupsDropped": 0
        }
      }
    }
  },
  "ok": 1.0
}
```

</details>

### Query 2: Sarah's last 5 viewed products (6 months)

Redis uses ZREVRANGEBYSCORE on recent:1, with the six-calendar-month timestamp as the minimum score and a limit of five. MySQL fetches product details by primary key. On fewer than five cached matches, the implementation instead groups MongoDB views by product, sorts by last view time, and takes five. No MongoDB fallback plan was collected because these runs were cache hits.

<details>
<summary>Results: 5 records; complete output.</summary>

```json
[
  {
    "product_id": 1,
    "name": "Wireless Headphones",
    "base_price": "35.89",
    "viewed_at": "2026-11-19 19:51:24.982009+00:00"
  },
  {
    "product_id": 2,
    "name": "Summer Dress",
    "base_price": "148.39",
    "viewed_at": "2026-11-17 19:51:24.982009+00:00"
  },
  {
    "product_id": 163,
    "name": "Stoneware Vase 00163",
    "base_price": "211.40",
    "viewed_at": "2026-11-16 05:23:17.314157+00:00"
  },
  {
    "product_id": 3,
    "name": "Ceramic Vase",
    "base_price": "19.02",
    "viewed_at": "2026-11-15 19:51:24.982009+00:00"
  },
  {
    "product_id": 4037,
    "name": "Chef Knife 04037",
    "base_price": "176.73",
    "viewed_at": "2026-10-26 19:09:35.804782+00:00"
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT product_id, name, base_price FROM products WHERE product_id IN (%s, %s, %s, %s, %s)
```

Parameters: `[1, 2, 163, 3, 4037]`.

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "products",
    "partitions": null,
    "type": "range",
    "possible_keys": "PRIMARY",
    "key": "PRIMARY",
    "key_len": "8",
    "ref": null,
    "rows": 5,
    "filtered": 100.0,
    "Extra": "Using where"
  }
]
```

</details>

### Query 3: Variants with stock under 5

MySQL filters authoritative variant stock below five, then joins product details.

<details>
<summary>Results: 1,579 records; first three records shown.</summary>

```json
[
  {
    "variant_id": 20,
    "sku": "SKU-0000020",
    "size": null,
    "color": "blue",
    "stock_quantity": 0,
    "product_id": 9,
    "name": "Studio Headphones 00009"
  },
  {
    "variant_id": 23,
    "sku": "SKU-0000023",
    "size": "Large",
    "color": "blue",
    "stock_quantity": 0,
    "product_id": 10,
    "name": "Summer Dress 00010"
  },
  {
    "variant_id": 72,
    "sku": "SKU-0000072",
    "size": null,
    "color": null,
    "stock_quantity": 0,
    "product_id": 32,
    "name": "Cookbook 00032"
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT v.variant_id, v.sku, v.size, v.color, v.stock_quantity,
            p.product_id, p.name
        FROM product_variants v
        JOIN products p ON p.product_id = v.product_id
        WHERE v.stock_quantity < %s
        ORDER BY v.stock_quantity, v.variant_id
```

Parameters: `[5]`.

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "v",
    "partitions": null,
    "type": "range",
    "possible_keys": "idx_variants_product,idx_variants_stock",
    "key": "idx_variants_stock",
    "key_len": "4",
    "ref": null,
    "rows": 1579,
    "filtered": 100.0,
    "Extra": "Using index condition"
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "p",
    "partitions": null,
    "type": "eq_ref",
    "possible_keys": "PRIMARY",
    "key": "PRIMARY",
    "key_len": "8",
    "ref": "ecommerce.v.product_id",
    "rows": 1,
    "filtered": 100.0,
    "Extra": null
  }
]
```

</details>

### Query 4: Fashion products in blue or size Large

MySQL filters fashion variants for blue or Large, positive stock, and active status. The plan below shows the access path actually chosen; the schema also provides color/stock and size/stock indexes.

<details>
<summary>Results: 625 records; first three records shown.</summary>

```json
[
  {
    "product_id": 2,
    "name": "Summer Dress",
    "base_price": "148.39",
    "variants": [
      {
        "variant_id": 3,
        "size": "Small",
        "color": "blue",
        "price": "152.17",
        "stock_quantity": 5
      },
      {
        "variant_id": 4,
        "size": "Medium",
        "color": "blue",
        "price": "152.93",
        "stock_quantity": 35
      },
      {
        "variant_id": 5,
        "size": "Large",
        "color": "blue",
        "price": "150.84",
        "stock_quantity": 8
      },
      {
        "variant_id": 8,
        "size": "Large",
        "color": "aqua-blue",
        "price": "150.93",
        "stock_quantity": 32
      },
      {
        "variant_id": 11,
        "size": "Large",
        "color": "black",
        "price": "149.94",
        "stock_quantity": 14
      }
    ]
  },
  {
    "product_id": 10,
    "name": "Summer Dress 00010",
    "base_price": "147.35",
    "variants": [
      {
        "variant_id": 21,
        "size": "Small",
        "color": "blue",
        "price": "151.20",
        "stock_quantity": 34
      },
      {
        "variant_id": 22,
        "size": "Medium",
        "color": "blue",
        "price": "150.25",
        "stock_quantity": 2
      },
      {
        "variant_id": 26,
        "size": "Large",
        "color": "aqua-blue",
        "price": "147.74",
        "stock_quantity": 3
      },
      {
        "variant_id": 29,
        "size": "Large",
        "color": "black",
        "price": "147.57",
        "stock_quantity": 20
      }
    ]
  },
  {
    "product_id": 18,
    "name": "Cotton Dress 00018",
    "base_price": "146.62",
    "variants": [
      {
        "variant_id": 39,
        "size": "Small",
        "color": "blue",
        "price": "151.48",
        "stock_quantity": 31
      },
      {
        "variant_id": 40,
        "size": "Medium",
        "color": "blue",
        "price": "148.05",
        "stock_quantity": 5
      },
      {
        "variant_id": 41,
        "size": "Large",
        "color": "blue",
        "price": "147.66",
        "stock_quantity": 8
      },
      {
        "variant_id": 44,
        "size": "Large",
        "color": "aqua-blue",
        "price": "150.41",
        "stock_quantity": 35
      },
      {
        "variant_id": 47,
        "size": "Large",
        "color": "black",
        "price": "146.80",
        "stock_quantity": 15
      }
    ]
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT p.product_id, p.name, p.base_price,
            v.variant_id, v.size, v.color, v.price, v.stock_quantity
        FROM products p
        JOIN categories c ON c.category_id = p.category_id
        JOIN product_variants v ON v.product_id = p.product_id
        WHERE c.slug = %s
        AND (v.color = %s OR v.size = %s)
        AND v.stock_quantity > 0
        AND v.is_active = 1
        AND p.is_active = 1
        ORDER BY p.product_id, v.variant_id
```

Parameters: `["fashion", "blue", "Large"]`.

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "c",
    "partitions": null,
    "type": "const",
    "possible_keys": "PRIMARY,slug",
    "key": "slug",
    "key_len": "402",
    "ref": "const",
    "rows": 1,
    "filtered": 100.0,
    "Extra": "Using index; Using temporary; Using filesort"
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "p",
    "partitions": null,
    "type": "ref",
    "possible_keys": "PRIMARY,idx_products_category",
    "key": "idx_products_category",
    "key_len": "8",
    "ref": "const",
    "rows": 625,
    "filtered": 10.0,
    "Extra": "Using where"
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "v",
    "partitions": null,
    "type": "ref",
    "possible_keys": "idx_variants_product,idx_variants_stock,idx_variants_color_stock,idx_variants_size_stock",
    "key": "idx_variants_product",
    "key_len": "8",
    "ref": "ecommerce.p.product_id",
    "rows": 2,
    "filtered": 2.26,
    "Extra": "Using where"
  }
]
```

</details>

### Query 5: Page-view count per product

MongoDB groups product_view events by product_id; MySQL supplies all products, including those with zero views. Python combines and sorts the answer.

<details>
<summary>Results: 5,000 records; first three records shown.</summary>

```json
[
  {
    "product_id": 1101,
    "name": "Chef Knife 01101",
    "views": 86
  },
  {
    "product_id": 430,
    "name": "Skin Cleanser 00430",
    "views": 82
  },
  {
    "product_id": 1213,
    "name": "Cutting Board 01213",
    "views": 82
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT product_id, name FROM products
```

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "products",
    "partitions": null,
    "type": "ALL",
    "possible_keys": null,
    "key": null,
    "key_len": null,
    "ref": null,
    "rows": 4869,
    "filtered": 100.0,
    "Extra": null
  }
]
```

</details>

<details>
<summary>MongoDB query and execution plan</summary>

```json
{
  "aggregate": "events",
  "pipeline": [
    {
      "$match": {
        "event_type": "product_view"
      }
    },
    {
      "$group": {
        "_id": "$product_id",
        "views": {
          "$sum": 1
        }
      }
    }
  ],
  "cursor": {}
}
```

```json
{
  "explainVersion": "2",
  "queryPlanner": {
    "namespace": "ecommerce.events",
    "parsedQuery": {
      "event_type": {
        "$eq": "product_view"
      }
    },
    "indexFilterSet": false,
    "queryHash": "3DD87EB4",
    "planCacheShapeHash": "3DD87EB4",
    "planCacheKey": "54E01FBF",
    "optimizationTimeMillis": 0,
    "optimizedPipeline": true,
    "maxIndexedOrSolutionsReached": false,
    "maxIndexedAndSolutionsReached": false,
    "maxScansToExplodeReached": false,
    "prunedSimilarIndexes": false,
    "winningPlan": {
      "isCached": false,
      "queryPlan": {
        "stage": "GROUP",
        "planNodeId": 3,
        "inputStage": {
          "stage": "PROJECTION_COVERED",
          "planNodeId": 2,
          "transformBy": {
            "product_id": true,
            "_id": false
          },
          "inputStage": {
            "stage": "IXSCAN",
            "planNodeId": 1,
            "keyPattern": {
              "event_type": 1,
              "product_id": 1
            },
            "indexName": "event_type_1_product_id_1",
            "isMultiKey": false,
            "multiKeyPaths": {
              "event_type": [],
              "product_id": []
            },
            "isUnique": false,
            "isSparse": false,
            "isPartial": false,
            "indexVersion": 2,
            "direction": "forward",
            "indexBounds": {
              "event_type": [
                "[\"product_view\", \"product_view\"]"
              ],
              "product_id": [
                "[MinKey, MaxKey]"
              ]
            }
          }
        }
      },
      "slotBasedPlan": {
        "slots": "$$RESULT=s7 env: {  }",
        "stages": "[3] project [s7 = newBsonObj(\"_id\", s4, \"views\", s6)] \n[3] project [s6 = (convert ( s5, int32) ?: s5)] \n[3] group [s4] [s5 = count()] spillSlots[s3] mergingExprs[sum(s3)] \n[3] project [s4 = (s1 ?: null)] \n[1] ixseek KS(3C70726F647563745F76696577000A0104) KS(3C70726F647563745F7669657700F0FE04) none s2 none none [s1 = 1] @\"5f7be3c4-91d6-4f31-8cc7-2e7282b07620\" @\"event_type_1_product_id_1\" true "
      }
    },
    "rejectedPlans": []
  },
  "executionStats": {
    "executionSuccess": true,
    "nReturned": 5000,
    "executionTimeMillis": 46,
    "totalKeysExamined": 275491,
    "totalDocsExamined": 0,
    "executionStages": {
      "stage": "project",
      "planNodeId": 3,
      "nReturned": 5000,
      "executionTimeMillisEstimate": 39,
      "opens": 1,
      "closes": 1,
      "saveState": 2,
      "restoreState": 2,
      "isEOF": 1,
      "projections": {
        "7": "newBsonObj(\"_id\", s4, \"views\", s6) "
      },
      "inputStage": {
        "stage": "project",
        "planNodeId": 3,
        "nReturned": 5000,
        "executionTimeMillisEstimate": 39,
        "opens": 1,
        "closes": 1,
        "saveState": 2,
        "restoreState": 2,
        "isEOF": 1,
        "projections": {
          "6": "(convert ( s5, int32) ?: s5) "
        },
        "inputStage": {
          "stage": "group",
          "planNodeId": 3,
          "nReturned": 5000,
          "executionTimeMillisEstimate": 39,
          "opens": 1,
          "closes": 1,
          "saveState": 2,
          "restoreState": 2,
          "isEOF": 1,
          "groupBySlots": [
            4
          ],
          "expressions": {
            "5": "count() ",
            "initExprs": {
              "5": null
            }
          },
          "mergingExprs": {
            "3": "sum(s3) "
          },
          "usedDisk": false,
          "spills": 0,
          "spilledBytes": 0,
          "spilledRecords": 0,
          "spilledDataStorageSize": 0,
          "inputStage": {
            "stage": "project",
            "planNodeId": 3,
            "nReturned": 275491,
            "executionTimeMillisEstimate": 39,
            "opens": 1,
            "closes": 1,
            "saveState": 2,
            "restoreState": 2,
            "isEOF": 1,
            "projections": {
              "4": "(s1 ?: null) "
            },
            "inputStage": {
              "stage": "ixseek",
              "planNodeId": 1,
              "nReturned": 275491,
              "executionTimeMillisEstimate": 39,
              "opens": 1,
              "closes": 1,
              "saveState": 2,
              "restoreState": 2,
              "isEOF": 1,
              "indexName": "event_type_1_product_id_1",
              "keysExamined": 275491,
              "seeks": 1,
              "numReads": 275492,
              "recordIdSlot": 2,
              "outputSlots": [
                1
              ],
              "indexKeysToInclude": "00000000000000000000000000000010",
              "seekKeyLow": "KS(3C70726F647563745F76696577000A0104) ",
              "seekKeyHigh": "KS(3C70726F647563745F7669657700F0FE04) "
            }
          }
        }
      }
    }
  },
  "ok": 1.0
}
```

</details>

### Query 6: Sarah's search terms (30 days) by frequency and time of day

MongoDB retrieves Sarah’s recent searches through the user/type/time filter. Python groups terms into the four UTC time periods and sorts by frequency.

<details>
<summary>Results: 4 records; complete output.</summary>

```json
[
  {
    "search_term": "headphones",
    "total": 4,
    "night": 0,
    "morning": 2,
    "afternoon": 0,
    "evening": 2
  },
  {
    "search_term": "blue dress",
    "total": 2,
    "night": 0,
    "morning": 0,
    "afternoon": 2,
    "evening": 0
  },
  {
    "search_term": "ceramic vase",
    "total": 1,
    "night": 1,
    "morning": 0,
    "afternoon": 0,
    "evening": 0
  },
  {
    "search_term": "summer dress",
    "total": 1,
    "night": 1,
    "morning": 0,
    "afternoon": 0,
    "evening": 0
  }
]
```

</details>

<details>
<summary>MongoDB query and execution plan</summary>

```json
{
  "find": "events",
  "filter": {
    "user_id": 1,
    "event_type": "search",
    "occurred_at": {
      "$gte": "2026-10-25 02:14:23.425600+00:00"
    }
  },
  "projection": {
    "_id": 0,
    "search_term": 1,
    "occurred_at": 1
  }
}
```

```json
{
  "explainVersion": "1",
  "queryPlanner": {
    "namespace": "ecommerce.events",
    "parsedQuery": {
      "$and": [
        {
          "event_type": {
            "$eq": "search"
          }
        },
        {
          "user_id": {
            "$eq": 1
          }
        },
        {
          "occurred_at": {
            "$gte": "2026-10-25 02:14:23.425000"
          }
        }
      ]
    },
    "indexFilterSet": false,
    "queryHash": "4BE82C45",
    "planCacheShapeHash": "4BE82C45",
    "planCacheKey": "E760AD78",
    "optimizationTimeMillis": 0,
    "maxIndexedOrSolutionsReached": false,
    "maxIndexedAndSolutionsReached": false,
    "maxScansToExplodeReached": false,
    "prunedSimilarIndexes": false,
    "winningPlan": {
      "isCached": true,
      "stage": "PROJECTION_SIMPLE",
      "transformBy": {
        "_id": 0,
        "search_term": 1,
        "occurred_at": 1
      },
      "inputStage": {
        "stage": "FETCH",
        "inputStage": {
          "stage": "IXSCAN",
          "keyPattern": {
            "user_id": 1,
            "event_type": 1,
            "occurred_at": -1
          },
          "indexName": "user_id_1_event_type_1_occurred_at_-1",
          "isMultiKey": false,
          "multiKeyPaths": {
            "user_id": [],
            "event_type": [],
            "occurred_at": []
          },
          "isUnique": false,
          "isSparse": false,
          "isPartial": false,
          "indexVersion": 2,
          "direction": "forward",
          "indexBounds": {
            "user_id": [
              "[1, 1]"
            ],
            "event_type": [
              "[\"search\", \"search\"]"
            ],
            "occurred_at": [
              "[new Date(9223372036854775807), new Date(1792894463425)]"
            ]
          }
        }
      }
    },
    "rejectedPlans": [
      {
        "isCached": false,
        "stage": "PROJECTION_SIMPLE",
        "transformBy": {
          "_id": 0,
          "search_term": 1,
          "occurred_at": 1
        },
        "inputStage": {
          "stage": "FETCH",
          "filter": {
            "$and": [
              {
                "occurred_at": {
                  "$gte": "2026-10-25 02:14:23.425000"
                }
              },
              {
                "user_id": {
                  "$eq": 1
                }
              }
            ]
          },
          "inputStage": {
            "stage": "IXSCAN",
            "keyPattern": {
              "event_type": 1,
              "product_id": 1
            },
            "indexName": "event_type_1_product_id_1",
            "isMultiKey": false,
            "multiKeyPaths": {
              "event_type": [],
              "product_id": []
            },
            "isUnique": false,
            "isSparse": false,
            "isPartial": false,
            "indexVersion": 2,
            "direction": "forward",
            "indexBounds": {
              "event_type": [
                "[\"search\", \"search\"]"
              ],
              "product_id": [
                "[MinKey, MaxKey]"
              ]
            }
          }
        }
      }
    ]
  },
  "executionStats": {
    "executionSuccess": true,
    "nReturned": 8,
    "executionTimeMillis": 0,
    "totalKeysExamined": 8,
    "totalDocsExamined": 8,
    "executionStages": {
      "isCached": true,
      "stage": "PROJECTION_SIMPLE",
      "nReturned": 8,
      "executionTimeMillisEstimate": 0,
      "works": 10,
      "advanced": 8,
      "needTime": 0,
      "needYield": 0,
      "saveState": 0,
      "restoreState": 0,
      "isEOF": 1,
      "transformBy": {
        "_id": 0,
        "search_term": 1,
        "occurred_at": 1
      },
      "inputStage": {
        "stage": "FETCH",
        "nReturned": 8,
        "executionTimeMillisEstimate": 0,
        "works": 10,
        "advanced": 8,
        "needTime": 0,
        "needYield": 0,
        "saveState": 0,
        "restoreState": 0,
        "isEOF": 1,
        "docsExamined": 8,
        "alreadyHasObj": 0,
        "inputStage": {
          "stage": "IXSCAN",
          "nReturned": 8,
          "executionTimeMillisEstimate": 0,
          "works": 9,
          "advanced": 8,
          "needTime": 0,
          "needYield": 0,
          "saveState": 0,
          "restoreState": 0,
          "isEOF": 1,
          "keyPattern": {
            "user_id": 1,
            "event_type": 1,
            "occurred_at": -1
          },
          "indexName": "user_id_1_event_type_1_occurred_at_-1",
          "isMultiKey": false,
          "multiKeyPaths": {
            "user_id": [],
            "event_type": [],
            "occurred_at": []
          },
          "isUnique": false,
          "isSparse": false,
          "isPartial": false,
          "indexVersion": 2,
          "direction": "forward",
          "indexBounds": {
            "user_id": [
              "[1, 1]"
            ],
            "event_type": [
              "[\"search\", \"search\"]"
            ],
            "occurred_at": [
              "[new Date(9223372036854775807), new Date(1792894463425)]"
            ]
          },
          "keysExamined": 8,
          "seeks": 1,
          "dupsTested": 0,
          "dupsDropped": 0
        }
      }
    }
  },
  "ok": 1.0
}
```

</details>

### Query 7: Active carts: device, item count, total

MySQL left joins active carts to items and variants, preserving empty carts and summing quantities and current prices.

<details>
<summary>Results: 3,647 records; first three records shown.</summary>

```json
[
  {
    "cart_id": 100001,
    "user_id": 1,
    "last_device": "laptop",
    "item_count": 4,
    "total_amount": "227.74"
  },
  {
    "cart_id": 100002,
    "user_id": 4686,
    "last_device": "phone",
    "item_count": 1,
    "total_amount": "162.06"
  },
  {
    "cart_id": 100004,
    "user_id": 4479,
    "last_device": "laptop",
    "item_count": 1,
    "total_amount": "64.26"
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT c.cart_id, c.user_id, c.last_device,
            CAST(COALESCE(SUM(i.quantity), 0) AS UNSIGNED) AS item_count,
            COALESCE(SUM(i.quantity * v.price), 0) AS total_amount
        FROM carts c
        LEFT JOIN cart_items i ON i.cart_id = c.cart_id
        LEFT JOIN product_variants v ON v.variant_id = i.variant_id
        WHERE c.status = 'active'
        GROUP BY c.cart_id, c.user_id, c.last_device
        ORDER BY c.cart_id
```

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "c",
    "partitions": null,
    "type": "ALL",
    "possible_keys": null,
    "key": null,
    "key_len": null,
    "ref": null,
    "rows": 105728,
    "filtered": 33.33,
    "Extra": "Using where; Using temporary; Using filesort"
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "i",
    "partitions": null,
    "type": "ref",
    "possible_keys": "PRIMARY",
    "key": "PRIMARY",
    "key_len": "8",
    "ref": "ecommerce.c.cart_id",
    "rows": 1,
    "filtered": 100.0,
    "Extra": null
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "v",
    "partitions": null,
    "type": "eq_ref",
    "possible_keys": "PRIMARY",
    "key": "PRIMARY",
    "key_len": "8",
    "ref": "ecommerce.i.variant_id",
    "rows": 1,
    "filtered": 100.0,
    "Extra": null
  }
]
```

</details>

### Query 8: Sarah's orders with items, payment, shipping, status

A correlated subquery selects one payment_id per order, prioritizing successful payment states. The left join prevents missing payments from removing orders and avoids multiplying item rows across attempts.

<details>
<summary>Results: 13 records; complete output.</summary>

```json
[
  {
    "order_id": 95177,
    "placed_at": "2025-12-01 10:09:32.836195",
    "status": "delivered",
    "total_amount": "465.97",
    "shipping_option": "Express",
    "payment_method": "bank_account",
    "items": [
      {
        "product_name": "Running Shoes 00119",
        "size": null,
        "color": null,
        "quantity": 1,
        "unit_price": "218.89"
      },
      {
        "product_name": "Decorative Vase 00219",
        "size": null,
        "color": "blue",
        "quantity": 2,
        "unit_price": "100.27"
      }
    ]
  },
  {
    "order_id": 1,
    "placed_at": "2025-12-15 19:51:24.982009",
    "status": "delivered",
    "total_amount": "225.87",
    "shipping_option": "Overnight",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Studio Headphones 03137",
        "size": null,
        "color": "black",
        "quantity": 2,
        "unit_price": "93.00"
      }
    ]
  },
  {
    "order_id": 13760,
    "placed_at": "2026-01-01 06:04:09.187906",
    "status": "delivered",
    "total_amount": "382.41",
    "shipping_option": "Overnight",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Water Bottle 02191",
        "size": null,
        "color": null,
        "quantity": 2,
        "unit_price": "165.47"
      }
    ]
  },
  {
    "order_id": 25257,
    "placed_at": "2026-01-16 16:59:31.231025",
    "status": "delivered",
    "total_amount": "209.02",
    "shipping_option": "Express",
    "payment_method": "bank_account",
    "items": [
      {
        "product_name": "Coffee Grinder 00093",
        "size": null,
        "color": null,
        "quantity": 1,
        "unit_price": "95.23"
      },
      {
        "product_name": "Skin Cleanser 01334",
        "size": null,
        "color": null,
        "quantity": 1,
        "unit_price": "49.62"
      },
      {
        "product_name": "Notebook 00624",
        "size": null,
        "color": null,
        "quantity": 1,
        "unit_price": "36.66"
      }
    ]
  },
  {
    "order_id": 2,
    "placed_at": "2026-02-13 19:51:24.982009",
    "status": "delivered",
    "total_amount": "204.21",
    "shipping_option": "Standard",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Notebook 02976",
        "size": null,
        "color": null,
        "quantity": 2,
        "unit_price": "75.49"
      },
      {
        "product_name": "Decorative Vase 00619",
        "size": null,
        "color": "blue",
        "quantity": 2,
        "unit_price": "16.28"
      }
    ]
  },
  {
    "order_id": 32814,
    "placed_at": "2026-02-19 20:48:27.177345",
    "status": "delivered",
    "total_amount": "243.95",
    "shipping_option": "Overnight",
    "payment_method": "bank_account",
    "items": [
      {
        "product_name": "Stoneware Vase 03907",
        "size": null,
        "color": "blue",
        "quantity": 2,
        "unit_price": "101.37"
      }
    ]
  },
  {
    "order_id": 31750,
    "placed_at": "2026-03-05 09:22:28.199958",
    "status": "delivered",
    "total_amount": "300.68",
    "shipping_option": "Standard",
    "payment_method": "bank_account",
    "items": [
      {
        "product_name": "Cookbook 00648",
        "size": null,
        "color": null,
        "quantity": 1,
        "unit_price": "34.83"
      },
      {
        "product_name": "Paperback Novel 00240",
        "size": null,
        "color": null,
        "quantity": 1,
        "unit_price": "71.67"
      },
      {
        "product_name": "Running Shoes 03831",
        "size": null,
        "color": null,
        "quantity": 2,
        "unit_price": "83.18"
      }
    ]
  },
  {
    "order_id": 3,
    "placed_at": "2026-04-24 19:51:24.982009",
    "status": "delivered",
    "total_amount": "452.28",
    "shipping_option": "Overnight",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Ceramic Vase 02739",
        "size": null,
        "color": "white",
        "quantity": 1,
        "unit_price": "198.18"
      },
      {
        "product_name": "Skin Cleanser 04342",
        "size": null,
        "color": null,
        "quantity": 2,
        "unit_price": "98.73"
      }
    ]
  },
  {
    "order_id": 85616,
    "placed_at": "2026-04-28 06:24:56.358020",
    "status": "delivered",
    "total_amount": "507.86",
    "shipping_option": "Overnight",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Notebook 03712",
        "size": null,
        "color": null,
        "quantity": 2,
        "unit_price": "52.39"
      },
      {
        "product_name": "Ceramic Vase 04555",
        "size": null,
        "color": "white",
        "quantity": 2,
        "unit_price": "171.16"
      }
    ]
  },
  {
    "order_id": 4,
    "placed_at": "2026-07-13 19:51:24.982009",
    "status": "delivered",
    "total_amount": "338.80",
    "shipping_option": "Express",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Summer Dress",
        "size": "Large",
        "color": "blue",
        "quantity": 2,
        "unit_price": "150.84"
      }
    ]
  },
  {
    "order_id": 5,
    "placed_at": "2026-10-11 19:51:24.982009",
    "status": "delivered",
    "total_amount": "402.85",
    "shipping_option": "Express",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Wireless Headphones",
        "size": null,
        "color": "blue",
        "quantity": 1,
        "unit_price": "37.66"
      },
      {
        "product_name": "Summer Dress",
        "size": "Small",
        "color": "aqua-blue",
        "quantity": 2,
        "unit_price": "149.77"
      },
      {
        "product_name": "Ceramic Vase",
        "size": null,
        "color": "white",
        "quantity": 1,
        "unit_price": "23.78"
      }
    ]
  },
  {
    "order_id": 6,
    "placed_at": "2026-11-02 19:51:24.982009",
    "status": "delivered",
    "total_amount": "676.12",
    "shipping_option": "Overnight",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Decorative Vase 04179",
        "size": null,
        "color": "white",
        "quantity": 2,
        "unit_price": "205.34"
      },
      {
        "product_name": "Studio Headphones 00777",
        "size": null,
        "color": "black",
        "quantity": 1,
        "unit_price": "15.36"
      },
      {
        "product_name": "Portable Speaker 00020",
        "size": null,
        "color": null,
        "quantity": 1,
        "unit_price": "176.86"
      }
    ]
  },
  {
    "order_id": 7,
    "placed_at": "2026-11-15 19:51:24.982009",
    "status": "processing",
    "total_amount": "714.44",
    "shipping_option": "Express",
    "payment_method": "credit_card",
    "items": [
      {
        "product_name": "Studio Headphones 02057",
        "size": null,
        "color": "blue",
        "quantity": 1,
        "unit_price": "111.68"
      },
      {
        "product_name": "Summer Dress 02018",
        "size": "Large",
        "color": "blue",
        "quantity": 2,
        "unit_price": "177.00"
      },
      {
        "product_name": "Cotton Dress 03666",
        "size": "Large",
        "color": "black",
        "quantity": 1,
        "unit_price": "183.81"
      }
    ]
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT o.order_id, o.placed_at, o.status, o.total_amount,
            s.name AS shipping_option, pay.method_type AS payment_method,
            i.product_name_snapshot AS product_name, v.size, v.color,
            i.quantity, i.unit_price
        FROM orders o
        JOIN shipping_options s ON s.shipping_option_id = o.shipping_option_id
        LEFT JOIN payments pay ON pay.payment_id = (
            SELECT candidate.payment_id
            FROM payments candidate
            WHERE candidate.order_id = o.order_id
            ORDER BY
                (candidate.status IN ('approved', 'refunded', 'partially_refunded')) DESC,
                candidate.created_at DESC, candidate.payment_id DESC
            LIMIT 1
        )
        JOIN order_items i ON i.order_id = o.order_id
        JOIN product_variants v ON v.variant_id = i.variant_id
        WHERE o.user_id = %s
        ORDER BY o.placed_at, o.order_id, i.order_item_id
```

Parameters: `[1]`.

```json
[
  {
    "id": 1,
    "select_type": "PRIMARY",
    "table": "o",
    "partitions": null,
    "type": "ref",
    "possible_keys": "PRIMARY,idx_orders_user_date,fk_orders_shipping_option",
    "key": "idx_orders_user_date",
    "key_len": "8",
    "ref": "const",
    "rows": 13,
    "filtered": 100.0,
    "Extra": "Using temporary; Using filesort"
  },
  {
    "id": 1,
    "select_type": "PRIMARY",
    "table": "s",
    "partitions": null,
    "type": "eq_ref",
    "possible_keys": "PRIMARY",
    "key": "PRIMARY",
    "key_len": "8",
    "ref": "ecommerce.o.shipping_option_id",
    "rows": 1,
    "filtered": 100.0,
    "Extra": null
  },
  {
    "id": 1,
    "select_type": "PRIMARY",
    "table": "pay",
    "partitions": null,
    "type": "eq_ref",
    "possible_keys": "PRIMARY",
    "key": "PRIMARY",
    "key_len": "8",
    "ref": "func",
    "rows": 1,
    "filtered": 100.0,
    "Extra": "Using where"
  },
  {
    "id": 1,
    "select_type": "PRIMARY",
    "table": "i",
    "partitions": null,
    "type": "ref",
    "possible_keys": "idx_order_items_order,idx_order_items_variant",
    "key": "idx_order_items_order",
    "key_len": "8",
    "ref": "ecommerce.o.order_id",
    "rows": 2,
    "filtered": 100.0,
    "Extra": null
  },
  {
    "id": 1,
    "select_type": "PRIMARY",
    "table": "v",
    "partitions": null,
    "type": "eq_ref",
    "possible_keys": "PRIMARY",
    "key": "PRIMARY",
    "key_len": "8",
    "ref": "ecommerce.i.variant_id",
    "rows": 1,
    "filtered": 100.0,
    "Extra": null
  },
  {
    "id": 2,
    "select_type": "DEPENDENT SUBQUERY",
    "table": "candidate",
    "partitions": null,
    "type": "ref",
    "possible_keys": "idx_payments_order",
    "key": "idx_payments_order",
    "key_len": "8",
    "ref": "ecommerce.o.order_id",
    "rows": 1,
    "filtered": 100.0,
    "Extra": "Using filesort"
  }
]
```

</details>

### Query 9: Sarah's returns

MySQL joins Sarah’s orders to returned order items and exposes return, refund, and exchange statuses and amounts.

<details>
<summary>Results: 2 records; complete output.</summary>

```json
[
  {
    "return_id": 1,
    "order_id": 4,
    "product_name": "Summer Dress",
    "quantity": 1,
    "resolution": "refund",
    "status": "completed",
    "refund_status": "processed",
    "exchange_status": "not_applicable",
    "refund_amount": "143.30",
    "restocking_fee": "7.54",
    "requested_at": "2026-07-25 19:51:24.982009"
  },
  {
    "return_id": 2,
    "order_id": 5,
    "product_name": "Summer Dress",
    "quantity": 1,
    "resolution": "exchange",
    "status": "completed",
    "refund_status": "not_applicable",
    "exchange_status": "completed",
    "refund_amount": "0.00",
    "restocking_fee": "0.00",
    "requested_at": "2026-10-23 19:51:24.982009"
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT r.return_id, o.order_id, i.product_name_snapshot AS product_name,
            r.quantity, r.resolution, r.status, r.refund_status, r.exchange_status,
            r.refund_amount, r.restocking_fee, r.requested_at
        FROM `returns` r
        JOIN order_items i ON i.order_item_id = r.order_item_id
        JOIN orders o ON o.order_id = i.order_id
        WHERE o.user_id = %s
        ORDER BY r.requested_at
```

Parameters: `[1]`.

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "o",
    "partitions": null,
    "type": "ref",
    "possible_keys": "PRIMARY,idx_orders_user_date",
    "key": "idx_orders_user_date",
    "key_len": "8",
    "ref": "const",
    "rows": 13,
    "filtered": 100.0,
    "Extra": "Using index; Using temporary; Using filesort"
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "i",
    "partitions": null,
    "type": "ref",
    "possible_keys": "PRIMARY,idx_order_items_order",
    "key": "idx_order_items_order",
    "key_len": "8",
    "ref": "ecommerce.o.order_id",
    "rows": 2,
    "filtered": 100.0,
    "Extra": null
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "r",
    "partitions": null,
    "type": "ref",
    "possible_keys": "idx_returns_order_item",
    "key": "idx_returns_order_item",
    "key_len": "8",
    "ref": "ecommerce.i.order_item_id",
    "rows": 1,
    "filtered": 100.0,
    "Extra": null
  }
]
```

</details>

### Query 10: Average days between Sarah's purchases

MySQL returns Sarah’s non-cancelled purchase times in order; Python averages consecutive elapsed-time gaps in days.

<details>
<summary>Results: 1 record; complete output.</summary>

```json
[
  {
    "orders": 13,
    "avg_days_between_purchases": 29.12
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT placed_at FROM orders WHERE user_id = %s AND status <> 'cancelled' ORDER BY placed_at
```

Parameters: `[1]`.

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "orders",
    "partitions": null,
    "type": "ref",
    "possible_keys": "idx_orders_user_date,idx_orders_status",
    "key": "idx_orders_user_date",
    "key_len": "8",
    "ref": "const",
    "rows": 13,
    "filtered": 83.33,
    "Extra": "Using where"
  }
]
```

</details>

### Query 11: % of carts (30 days) never converted

MySQL counts recent carts and those without an associated order; Python calculates the percentage.

<details>
<summary>Results: 1 record; complete output.</summary>

```json
[
  {
    "carts_created": 16521,
    "never_converted": 5357,
    "percent_never_converted": 32.43
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT COUNT(*) AS carts_created,
            CAST(COALESCE(SUM(o.order_id IS NULL), 0) AS UNSIGNED) AS never_converted
        FROM carts c
        LEFT JOIN orders o ON o.cart_id = c.cart_id
        WHERE c.created_at >= NOW() - INTERVAL 30 DAY
```

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "c",
    "partitions": null,
    "type": "range",
    "possible_keys": "idx_carts_created",
    "key": "idx_carts_created",
    "key_len": "8",
    "ref": null,
    "rows": 32968,
    "filtered": 100.0,
    "Extra": "Using where; Using index"
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "o",
    "partitions": null,
    "type": "eq_ref",
    "possible_keys": "cart_id",
    "key": "cart_id",
    "key_len": "8",
    "ref": "ecommerce.c.cart_id",
    "rows": 1,
    "filtered": 100.0,
    "Extra": "Using index"
  }
]
```

</details>

### Query 12: Top 3 products bought with headphones

Neo4j traverses from headphones products to non-cancelled orders and other distinct products. Counting distinct orders prevents multiple matching headphones or variant lines from inflating co-purchase frequency.

<details>
<summary>Results: 3 records; complete output.</summary>

```json
[
  {
    "product_id": 5000,
    "name": "Notebook 05000",
    "orders_together": 17
  },
  {
    "product_id": 600,
    "name": "Cookbook 00600",
    "orders_together": 16
  },
  {
    "product_id": 4526,
    "name": "Hair Brush 04526",
    "orders_together": 16
  }
]
```

</details>

<details>
<summary>Neo4j query and execution plan</summary>

```cypher
MATCH (:Category {name: 'Headphones'})<-[:IN_CATEGORY]-(headphones:Product)<-[:CONTAINS]-(o:Order)
            WHERE o.status <> 'cancelled'
            WITH DISTINCT o, headphones
            MATCH (o)-[:CONTAINS]->(other:Product)
            WHERE other.product_id <> headphones.product_id
            RETURN other.product_id AS product_id, other.name AS name,
                count(DISTINCT o) AS orders_together
            ORDER BY orders_together DESC, product_id
            LIMIT 3
```

```json
{
  "args": {
    "Order": "orders_together DESC, product_id ASC",
    "GlobalMemory": 4486752,
    "planner-impl": "IDP",
    "Memory": 0,
    "string-representation": "Cypher 5\n\nPlanner COST\n\nRuntime SLOTTED\n\nRuntime version 5.26.33\n\n+-------------------+----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| Operator          | Id | Details                                                                                         | Estimated Rows | Rows  | DB Hits | Memory (Bytes) | Page Cache Hits/Misses | Ordered by                           |\n+-------------------+----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +ProduceResults   |  0 | product_id, name, orders_together                                                               |              3 |     3 |       0 |              0 |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+                                      |\n| +Top              |  1 | orders_together DESC, product_id ASC LIMIT 3                                                    |              3 |     3 |       0 |            880 |                    0/0 | orders_together DESC, product_id ASC |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +EagerAggregation |  2 | cache[other.product_id] AS product_id, other.name AS name, count(DISTINCT o) AS orders_together |             48 |  4990 |   31967 |        3017880 |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +Filter           |  3 | NOT cache[other.product_id] = cache[headphones.product_id] AND other:Product                    |           2266 | 31967 |   87820 |                |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +Expand(All)      |  4 | (o)-[anon_3:CONTAINS]->(other)                                                                  |           2266 | 55853 |  103625 |                |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +Distinct         |  5 | o, headphones                                                                                   |           1131 | 23886 |       0 |        1468816 |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +Filter           |  6 | NOT o.status = $autostring_1 AND o:Order                                                        |           1190 | 23886 |   48766 |                |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +Expand(All)      |  7 | (headphones)<-[anon_2:CONTAINS]-(o)                                                             |           2505 | 24880 |   27380 |                |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +CacheProperties  |  8 | cache[headphones.product_id]                                                                    |             63 |   625 |     625 |                |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +Filter           |  9 | headphones:Product                                                                              |             63 |   625 |     625 |                |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +Expand(All)      | 10 | (anon_0)<-[anon_1:IN_CATEGORY]-(headphones)                                                     |             63 |   625 |     627 |                |                    0/0 |                                      |\n| |                 +----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n| +NodeIndexSeek    | 11 | RANGE INDEX anon_0:Category(name) WHERE name = $autostring_0                                    |              0 |     1 |       2 |                |                    0/0 |                                      |\n+-------------------+----+-------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+\n\nTotal database accesses: 301437, total allocated memory: 4486752\n",
    "runtime": "SLOTTED",
    "runtime-impl": "SLOTTED",
    "version": "5",
    "DbHits": 0,
    "Details": "product_id, name, orders_together",
    "planner-version": "5.26.33",
    "runtime-version": "5.26.33",
    "Id": 0,
    "EstimatedRows": 3.0,
    "planner": "COST",
    "PageCacheMisses": 0,
    "Rows": 3,
    "PageCacheHits": 0
  },
  "pageCacheMisses": 0,
  "children": [
    {
      "args": {
        "Order": "orders_together DESC, product_id ASC",
        "Details": "orders_together DESC, product_id ASC LIMIT 3",
        "Memory": 880,
        "Id": 1,
        "EstimatedRows": 3.0,
        "PageCacheMisses": 0,
        "DbHits": 0,
        "Rows": 3,
        "PageCacheHits": 0
      },
      "pageCacheMisses": 0,
      "children": [
        {
          "args": {
            "Details": "cache[other.product_id] AS product_id, other.name AS name, count(DISTINCT o) AS orders_together",
            "Memory": 3017880,
            "Id": 2,
            "EstimatedRows": 47.59878940695845,
            "PageCacheMisses": 0,
            "DbHits": 31967,
            "Rows": 4990,
            "PageCacheHits": 0
          },
          "pageCacheMisses": 0,
          "children": [
            {
              "args": {
                "Details": "NOT cache[other.product_id] = cache[headphones.product_id] AND other:Product",
                "Id": 3,
                "PageCacheMisses": 0,
                "EstimatedRows": 2265.64475300798,
                "DbHits": 87820,
                "Rows": 31967,
                "PageCacheHits": 0
              },
              "pageCacheMisses": 0,
              "children": [
                {
                  "args": {
                    "Details": "(o)-[anon_3:CONTAINS]->(other)",
                    "Id": 4,
                    "PageCacheMisses": 0,
                    "EstimatedRows": 2266.0979726025002,
                    "DbHits": 103625,
                    "Rows": 55853,
                    "PageCacheHits": 0
                  },
                  "pageCacheMisses": 0,
                  "children": [
                    {
                      "args": {
                        "Details": "o, headphones",
                        "Memory": 1468816,
                        "Id": 5,
                        "EstimatedRows": 1130.5843125000001,
                        "PageCacheMisses": 0,
                        "DbHits": 0,
                        "Rows": 23886,
                        "PageCacheHits": 0
                      },
                      "pageCacheMisses": 0,
                      "children": [
                        {
                          "args": {
                            "Details": "NOT o.status = $autostring_1 AND o:Order",
                            "Id": 6,
                            "PageCacheMisses": 0,
                            "EstimatedRows": 1190.0887500000001,
                            "DbHits": 48766,
                            "Rows": 23886,
                            "PageCacheHits": 0
                          },
                          "pageCacheMisses": 0,
                          "children": [
                            {
                              "args": {
                                "Details": "(headphones)<-[anon_2:CONTAINS]-(o)",
                                "Id": 7,
                                "PageCacheMisses": 0,
                                "EstimatedRows": 2505.4500000000003,
                                "DbHits": 27380,
                                "Rows": 24880,
                                "PageCacheHits": 0
                              },
                              "pageCacheMisses": 0,
                              "children": [
                                {
                                  "args": {
                                    "Details": "cache[headphones.product_id]",
                                    "Id": 8,
                                    "PageCacheMisses": 0,
                                    "EstimatedRows": 62.5,
                                    "DbHits": 625,
                                    "Rows": 625,
                                    "PageCacheHits": 0
                                  },
                                  "pageCacheMisses": 0,
                                  "children": [
                                    {
                                      "args": {
                                        "Details": "headphones:Product",
                                        "Id": 9,
                                        "PageCacheMisses": 0,
                                        "EstimatedRows": 62.5,
                                        "DbHits": 625,
                                        "Rows": 625,
                                        "PageCacheHits": 0
                                      },
                                      "pageCacheMisses": 0,
                                      "children": [
                                        {
                                          "args": {
                                            "Details": "(anon_0)<-[anon_1:IN_CATEGORY]-(headphones)",
                                            "Id": 10,
                                            "PageCacheMisses": 0,
                                            "EstimatedRows": 62.5,
                                            "DbHits": 627,
                                            "Rows": 625,
                                            "PageCacheHits": 0
                                          },
                                          "pageCacheMisses": 0,
                                          "children": [
                                            {
                                              "args": {
                                                "Details": "RANGE INDEX anon_0:Category(name) WHERE name = $autostring_0",
                                                "Id": 11,
                                                "PageCacheMisses": 0,
                                                "EstimatedRows": 0.125,
                                                "DbHits": 2,
                                                "Rows": 1,
                                                "PageCacheHits": 0
                                              },
                                              "pageCacheMisses": 0,
                                              "dbHits": 2,
                                              "identifiers": [
                                                "anon_0"
                                              ],
                                              "operatorType": "NodeIndexSeek@neo4j",
                                              "rows": 1,
                                              "pageCacheHitRatio": 0.0,
                                              "pageCacheHits": 0
                                            }
                                          ],
                                          "dbHits": 627,
                                          "identifiers": [
                                            "anon_0",
                                            "anon_1",
                                            "headphones"
                                          ],
                                          "operatorType": "Expand(All)@neo4j",
                                          "rows": 625,
                                          "pageCacheHitRatio": 0.0,
                                          "pageCacheHits": 0
                                        }
                                      ],
                                      "dbHits": 625,
                                      "identifiers": [
                                        "anon_0",
                                        "anon_1",
                                        "headphones"
                                      ],
                                      "operatorType": "Filter@neo4j",
                                      "rows": 625,
                                      "pageCacheHitRatio": 0.0,
                                      "pageCacheHits": 0
                                    }
                                  ],
                                  "dbHits": 625,
                                  "identifiers": [
                                    "anon_0",
                                    "anon_1",
                                    "headphones"
                                  ],
                                  "operatorType": "CacheProperties@neo4j",
                                  "rows": 625,
                                  "pageCacheHitRatio": 0.0,
                                  "pageCacheHits": 0
                                }
                              ],
                              "dbHits": 27380,
                              "identifiers": [
                                "anon_2",
                                "headphones",
                                "o",
                                "anon_0",
                                "anon_1"
                              ],
                              "operatorType": "Expand(All)@neo4j",
                              "rows": 24880,
                              "pageCacheHitRatio": 0.0,
                              "pageCacheHits": 0
                            }
                          ],
                          "dbHits": 48766,
                          "identifiers": [
                            "anon_2",
                            "headphones",
                            "o",
                            "anon_0",
                            "anon_1"
                          ],
                          "operatorType": "Filter@neo4j",
                          "rows": 23886,
                          "pageCacheHitRatio": 0.0,
                          "pageCacheHits": 0
                        }
                      ],
                      "dbHits": 0,
                      "identifiers": [
                        "o",
                        "headphones"
                      ],
                      "operatorType": "Distinct@neo4j",
                      "rows": 23886,
                      "pageCacheHitRatio": 0.0,
                      "pageCacheHits": 0
                    }
                  ],
                  "dbHits": 103625,
                  "identifiers": [
                    "o",
                    "headphones",
                    "anon_3",
                    "other"
                  ],
                  "operatorType": "Expand(All)@neo4j",
                  "rows": 55853,
                  "pageCacheHitRatio": 0.0,
                  "pageCacheHits": 0
                }
              ],
              "dbHits": 87820,
              "identifiers": [
                "o",
                "headphones",
                "anon_3",
                "other"
              ],
              "operatorType": "Filter@neo4j",
              "rows": 31967,
              "pageCacheHitRatio": 0.0,
              "pageCacheHits": 0
            }
          ],
          "dbHits": 31967,
          "identifiers": [
            "product_id",
            "name",
            "orders_together"
          ],
          "operatorType": "EagerAggregation@neo4j",
          "rows": 4990,
          "pageCacheHitRatio": 0.0,
          "pageCacheHits": 0
        }
      ],
      "dbHits": 0,
      "identifiers": [
        "product_id",
        "name",
        "orders_together"
      ],
      "operatorType": "Top@neo4j",
      "rows": 3,
      "pageCacheHitRatio": 0.0,
      "pageCacheHits": 0
    }
  ],
  "dbHits": 0,
  "identifiers": [
    "product_id",
    "name",
    "orders_together"
  ],
  "operatorType": "ProduceResults@neo4j",
  "rows": 3,
  "pageCacheHitRatio": 0.0,
  "pageCacheHits": 0
}
```

</details>

### Query 13: Days since last purchase and order count, per user

MySQL left joins every user to all orders. COUNT includes all orders, while a conditional MAX excludes cancellations only from the last-purchase date.

<details>
<summary>Results: 10,000 records; first three records shown.</summary>

```json
[
  {
    "user_id": 1,
    "full_name": "Sarah",
    "total_orders": 13,
    "days_since_last_purchase": 9
  },
  {
    "user_id": 2,
    "full_name": "Michelle Miles",
    "total_orders": 11,
    "days_since_last_purchase": 23
  },
  {
    "user_id": 3,
    "full_name": "Monica Herrera",
    "total_orders": 8,
    "days_since_last_purchase": 32
  }
]
```

</details>

<details>
<summary>MySQL query and execution plan</summary>

```sql
SELECT u.user_id, u.full_name,
            COUNT(o.order_id) AS total_orders,
            DATEDIFF(NOW(), MAX(CASE WHEN o.status <> 'cancelled'
                THEN o.placed_at END)) AS days_since_last_purchase
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.user_id
        GROUP BY u.user_id, u.full_name
        ORDER BY u.user_id
```

```json
[
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "u",
    "partitions": null,
    "type": "ALL",
    "possible_keys": null,
    "key": null,
    "key_len": null,
    "ref": null,
    "rows": 9508,
    "filtered": 100.0,
    "Extra": "Using temporary; Using filesort"
  },
  {
    "id": 1,
    "select_type": "SIMPLE",
    "table": "o",
    "partitions": null,
    "type": "ref",
    "possible_keys": "idx_orders_user_date",
    "key": "idx_orders_user_date",
    "key_len": "8",
    "ref": "ecommerce.u.user_id",
    "rows": 9,
    "filtered": 100.0,
    "Extra": null
  }
]
```

</details>
