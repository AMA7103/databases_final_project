# Performance Evaluation


## Instructions:
Run all 13 tasks from Part 2 against your full dataset. For each task, record:

- the runtime, as the median of 3 runs (for tasks that span several stores, the total time including your application code), and
- the execution plan, where the store provides one (for example, EXPLAIN in MySQL or explain() in MongoDB).

Each task should finish within 2 seconds. If a task takes longer, identify the bottleneck and propose or implement an optimization, such as an index, a denormalization, or a cache, and report the runtime again after the change.

## Results

All 13 queries were run against the full generated dataset. For queries that use more than one store, the time covers every database call plus the application code that combines the results. Opening the database connections is not included.

| # | Task | Stores | Median (ms) | Rows returned | Within 2 s |
|---|---|---|---|---|---|
| 1 | Fashion products with attributes | MySQL, MongoDB | 33.0 | 625 | Yes |
| 2 | Sarah's last 5 viewed products (6 months) | Redis, MySQL (MongoDB fallback) | 1.1 | 5 | Yes |
| 3 | Variants with stock under 5 | MySQL | 3.4 | 1,579 | Yes |
| 4 | Fashion products in blue or size Large | MySQL | 12.4 | 625 | Yes |
| 5 | Page-view count per product | MongoDB, MySQL | 69.2 | 5,000 | Yes |
| 6 | Sarah's search terms (30 days) by frequency and time of day | MongoDB | 0.6 | 4 | Yes |
| 7 | Active carts: device, item count, total | MySQL | 25.1 | 3,647 | Yes |
| 8 | Sarah's orders with items, payment, shipping, status | MySQL | 0.9 | 13 | Yes |
| 9 | Sarah's returns | MySQL | 0.7 | 2 | Yes |
| 10 | Average days between Sarah's purchases | MySQL | 0.6 | 1 | Yes |
| 11 | % of carts (30 days) never converted | MySQL | 11.5 | 1 | Yes |
| 12 | Top 3 products bought with headphones | Neo4j | 126.1 | 3 | Yes |
| 13 | Days since last purchase and order count, per user | MySQL | 92.6 | 10,000 | Yes |

## Assumptions

- **Query 4**
  - assumes "blue" means JUST blue, not blue-variants like "aqua-blue"
  - assumes "available" means inventory (stock_quantity) > 0
- **Query 6**
  - time-of-day periods are by UTC since event times are stored in UTC
- **Query 10**
  - Excludes cancelled orders
- **Query 11**
  - Assumes currently-open carts count as "never converted to an order."
- **Query 12**
  - Excludes items with "headphones" category
  - Ties are broken by product_id
- **Query 13**
  - Excludes cancelled orders

## Execution plans

For each query I described in words what it does and provided the raw output of the execution plan. Below are the functions I used to get the execution plans:

- **MySQL:** `EXPLAIN`, run in the `mysql` client.
- **MongoDB:** the `explain` command with `executionStats` verbosity, as returned by the server. The only change is that arrays of more than 10 items (long product-id lists) are cut off with `... N more`.
- **Neo4j:** `PROFILE`, run in `cypher-shell`.
- **Redis:** has no explain or query planner, so there is no plan to show.

### Query 1: Fashion products with attributes

MySQL finds the fashion category using the unique `slug` index, then reads its products with `idx_products_category` and their variants with `idx_variants_product`. No table is scanned. The filesort is just the `ORDER BY`. MongoDB then looks up those product ids in `product_attributes` using the `product_id` index, and every document it gets is returned.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT p.product_id, p.name, p.base_price, v.variant_id, v.size, v.color, v.price, v.stock_quantity FROM products p JOIN categories c ON c.category_id = p.category_id JOIN product_variants v ON v.product_id = p.product_id WHERE c.slug = 'fashion' ORDER BY p.product_id, v.variant_id;
```

```
+----+-------------+-------+------------+-------+-------------------------------+-----------------------+---------+------------------------+------+----------+----------------------------------------------+
| id | select_type | table | partitions | type  | possible_keys                 | key                   | key_len | ref                    | rows | filtered | Extra                                        |
+----+-------------+-------+------------+-------+-------------------------------+-----------------------+---------+------------------------+------+----------+----------------------------------------------+
|  1 | SIMPLE      | c     | NULL       | const | PRIMARY,slug                  | slug                  | 402     | const                  |    1 |   100.00 | Using index; Using temporary; Using filesort |
|  1 | SIMPLE      | p     | NULL       | ref   | PRIMARY,idx_products_category | idx_products_category | 8       | const                  |  625 |   100.00 | NULL                                         |
|  1 | SIMPLE      | v     | NULL       | ref   | idx_variants_product          | idx_variants_product  | 8       | ecommerce.p.product_id |    2 |   100.00 | NULL                                         |
+----+-------------+-------+------------+-------+-------------------------------+-----------------------+---------+------------------------+------+----------+----------------------------------------------+
```

</details>

<details>
<summary>Raw MongoDB explain: db.product_attributes.find(...)</summary>

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
          "... 615 more"
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
              "... 615 more"
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
              "... 615 more"
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
  "queryShapeHash": "D8B98C31809CF03142C54BF071CD2FFCE0365E137F2DB212170878424AFF733D",
  "command": {
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
          "... 615 more"
        ]
      }
    },
    "projection": {
      "_id": 0,
      "product_id": 1,
      "attributes": 1
    },
    "$db": "ecommerce"
  },
  "serverInfo": {
    "host": "63c422aab0b2",
    "port": 27017,
    "version": "8.0.38",
    "gitVersion": "b2f7afe3a6838999fd375c7a7ea678189f795568"
  },
  "serverParameters": {
    "internalQueryFacetBufferSizeBytes": 104857600,
    "internalQueryFacetMaxOutputDocSizeBytes": 104857600,
    "internalLookupStageIntermediateDocumentMaxSizeBytes": 104857600,
    "internalDocumentSourceGroupMaxMemoryBytes": 104857600,
    "internalQueryMaxBlockingSortMemoryUsageBytes": 104857600,
    "internalQueryProhibitBlockingMergeOnMongoS": 0,
    "internalQueryMaxAddToSetBytes": 104857600,
    "internalDocumentSourceSetWindowFieldsMaxMemoryBytes": 104857600,
    "internalQueryFrameworkControl": "trySbeRestricted",
    "internalQueryPlannerIgnoreIndexWithCollationForRegex": 1
  },
  "ok": 1.0
}
```

</details>

### Query 2: Sarah's last 5 viewed products

Redis has no plan and does a sorted-set lookup by score. MySQL looks up the 5 product ids by primary key. If we get less than 5 results back from the Redis cache then we check MongoDB. It uses the `(user_id, event_type, occurred_at)` index and examines only 17 documents.

Redis has no explain, so there is no raw plan for it. The command is `ZREVRANGEBYSCORE recent:1 +inf <six months ago> WITHSCORES LIMIT 0 5`.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT product_id, name, base_price FROM products WHERE product_id IN (1, 2, 163, 3, 4037);
```

```
+----+-------------+----------+------------+-------+---------------+---------+---------+------+------+----------+-------------+
| id | select_type | table    | partitions | type  | possible_keys | key     | key_len | ref  | rows | filtered | Extra       |
+----+-------------+----------+------------+-------+---------------+---------+---------+------+------+----------+-------------+
|  1 | SIMPLE      | products | NULL       | range | PRIMARY       | PRIMARY | 8       | NULL |    5 |   100.00 | Using where |
+----+-------------+----------+------------+-------+---------------+---------+---------+------+------+----------+-------------+
```

</details>

<details>
<summary>Raw MongoDB explain: db.events.aggregate(...) (fallback only)</summary>

```json
{
  "explainVersion": "2",
  "stages": [
    {
      "$cursor": {
        "queryPlanner": {
          "namespace": "ecommerce.events",
          "parsedQuery": {
            "$and": [
              {
                "event_type": {
                  "$eq": "product_view"
                }
              },
              {
                "user_id": {
                  "$eq": 1
                }
              },
              {
                "occurred_at": {
                  "$gte": {
                    "$date": "2026-05-24T17:35:04.911Z"
                  }
                }
              }
            ]
          },
          "indexFilterSet": false,
          "queryHash": "3C8E1208",
          "planCacheShapeHash": "3C8E1208",
          "planCacheKey": "99E9DE79",
          "optimizationTimeMillis": 1,
          "maxIndexedOrSolutionsReached": false,
          "maxIndexedAndSolutionsReached": false,
          "maxScansToExplodeReached": false,
          "prunedSimilarIndexes": false,
          "winningPlan": {
            "isCached": false,
            "queryPlan": {
              "stage": "GROUP",
              "planNodeId": 4,
              "inputStage": {
                "stage": "FETCH",
                "planNodeId": 2,
                "inputStage": {
                  "stage": "IXSCAN",
                  "planNodeId": 1,
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
                      "[\"product_view\", \"product_view\"]"
                    ],
                    "occurred_at": [
                      "[new Date(9223372036854775807), new Date(1779644104911)]"
                    ]
                  }
                }
              }
            },
            "slotBasedPlan": {
              "slots": "$$RESULT=s14 env: { s5 = {\"user_id\" : 1, \"event_type\" : 1, \"occurred_at\" : -1} }",
              "stages": "[4] project [s14 = newObj(\"_id\", s11, \"viewed_at\", s13)] \n[4] project [s13 = (s12 ?: null)] \n[4] group [s11] [s12 = max(fillType(s8, 1088, Nothing))] spillSlots[s10] mergingExprs[max(fillType(s10, 1088, Nothing))] \n[4] project [s11 = (s9 ?: null)] \n[2] nlj inner [] [s1, s2, s3, s4, s5] \n    left \n        [1] ixseek KS(2B023C70726F647563745F76696577008700000000000000000104) KS(2B023C70726F647563745F7669657700877FFFFE61A4F1FF30FE04) s4 s1 s2 s3 [] @\"e193b9a5-a961-4041-87cf-375a36e497c1\" @\"user_id_1_event_type_1_occurred_at_-1\" true \n    right \n        [2] limit 1ll \n        [2] seek s1 s6 s7 s2 s3 s4 s5 none none [s8 = occurred_at, s9 = product_id] @\"e193b9a5-a961-4041-87cf-375a36e497c1\" true false \n"
            }
          },
          "rejectedPlans": [
            {
              "isCached": false,
              "stage": "PROJECTION_SIMPLE",
              "transformBy": {
                "occurred_at": 1,
                "product_id": 1,
                "_id": 0
              },
              "inputStage": {
                "stage": "FETCH",
                "filter": {
                  "$and": [
                    {
                      "occurred_at": {
                        "$gte": {
                          "$date": "2026-05-24T17:35:04.911Z"
                        }
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
                      "[\"product_view\", \"product_view\"]"
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
          "nReturned": 14,
          "executionTimeMillis": 1,
          "totalKeysExamined": 17,
          "totalDocsExamined": 17,
          "executionStages": {
            "stage": "project",
            "planNodeId": 4,
            "nReturned": 14,
            "executionTimeMillisEstimate": 0,
            "opens": 1,
            "closes": 1,
            "saveState": 1,
            "restoreState": 1,
            "isEOF": 1,
            "projections": {
              "14": "newObj(\"_id\", s11, \"viewed_at\", s13) "
            },
            "inputStage": {
              "stage": "project",
              "planNodeId": 4,
              "nReturned": 14,
              "executionTimeMillisEstimate": 0,
              "opens": 1,
              "closes": 1,
              "saveState": 1,
              "restoreState": 1,
              "isEOF": 1,
              "projections": {
                "13": "(s12 ?: null) "
              },
              "inputStage": {
                "stage": "group",
                "planNodeId": 4,
                "nReturned": 14,
                "executionTimeMillisEstimate": 0,
                "opens": 1,
                "closes": 1,
                "saveState": 1,
                "restoreState": 1,
                "isEOF": 1,
                "groupBySlots": [
                  11
                ],
                "expressions": {
                  "12": "max(fillType(s8, 1088, Nothing)) ",
                  "initExprs": {
                    "12": null
                  }
                },
                "mergingExprs": {
                  "10": "max(fillType(s10, 1088, Nothing)) "
                },
                "usedDisk": false,
                "spills": 0,
                "spilledBytes": 0,
                "spilledRecords": 0,
                "spilledDataStorageSize": 0,
                "inputStage": {
                  "stage": "project",
                  "planNodeId": 4,
                  "nReturned": 17,
                  "executionTimeMillisEstimate": 0,
                  "opens": 1,
                  "closes": 1,
                  "saveState": 1,
                  "restoreState": 1,
                  "isEOF": 1,
                  "projections": {
                    "11": "(s9 ?: null) "
                  },
                  "inputStage": {
                    "stage": "nlj",
                    "planNodeId": 2,
                    "nReturned": 17,
                    "executionTimeMillisEstimate": 0,
                    "opens": 1,
                    "closes": 1,
                    "saveState": 1,
                    "restoreState": 1,
                    "isEOF": 1,
                    "totalDocsExamined": 17,
                    "totalKeysExamined": 17,
                    "collectionScans": 0,
                    "collectionSeeks": 17,
                    "indexScans": 0,
                    "indexSeeks": 1,
                    "indexesUsed": [
                      "user_id_1_event_type_1_occurred_at_-1"
                    ],
                    "innerOpens": 17,
                    "innerCloses": 1,
                    "outerProjects": [],
                    "outerCorrelated": [
                      1,
                      2,
                      3,
                      4,
                      5
                    ],
                    "outerStage": {
                      "stage": "ixseek",
                      "planNodeId": 1,
                      "nReturned": 17,
                      "executionTimeMillisEstimate": 0,
                      "opens": 1,
                      "closes": 1,
                      "saveState": 1,
                      "restoreState": 1,
                      "isEOF": 1,
                      "indexName": "user_id_1_event_type_1_occurred_at_-1",
                      "keysExamined": 17,
                      "seeks": 1,
                      "numReads": 18,
                      "indexKeySlot": 4,
                      "recordIdSlot": 1,
                      "snapshotIdSlot": 2,
                      "indexIdentSlot": 3,
                      "outputSlots": [],
                      "indexKeysToInclude": "00000000000000000000000000000000",
                      "seekKeyLow": "KS(2B023C70726F647563745F76696577008700000000000000000104) ",
                      "seekKeyHigh": "KS(2B023C70726F647563745F7669657700877FFFFE61A4F1FF30FE04) "
                    },
                    "innerStage": {
                      "stage": "limit",
                      "planNodeId": 2,
                      "nReturned": 17,
                      "executionTimeMillisEstimate": 0,
                      "opens": 17,
                      "closes": 1,
                      "saveState": 1,
                      "restoreState": 1,
                      "isEOF": 1,
                      "limit": 1,
                      "inputStage": {
                        "stage": "seek",
                        "planNodeId": 2,
                        "nReturned": 17,
                        "executionTimeMillisEstimate": 0,
                        "opens": 17,
                        "closes": 1,
                        "saveState": 1,
                        "restoreState": 1,
                        "isEOF": 0,
                        "numReads": 17,
                        "recordSlot": 6,
                        "recordIdSlot": 7,
                        "seekRecordIdSlot": 1,
                        "snapshotIdSlot": 2,
                        "indexIdentSlot": 3,
                        "indexKeySlot": 4,
                        "indexKeyPatternSlot": 5,
                        "scanFieldNames": [
                          "occurred_at",
                          "product_id"
                        ],
                        "scanFieldSlots": [
                          8,
                          9
                        ]
                      }
                    }
                  }
                }
              }
            }
          }
        }
      },
      "nReturned": 14,
      "executionTimeMillisEstimate": 1
    },
    {
      "$sort": {
        "sortKey": {
          "viewed_at": -1
        },
        "limit": 5
      },
      "totalDataSizeSortedBytesEstimate": 1265,
      "usedDisk": false,
      "spills": 0,
      "spilledDataStorageSize": 0,
      "nReturned": 5,
      "executionTimeMillisEstimate": 1
    }
  ],
  "queryShapeHash": "F334AF56822681E3C1C680C79F31269F1726E0DF28BED5FF8C40CBC0F464BA08",
  "serverInfo": {
    "host": "63c422aab0b2",
    "port": 27017,
    "version": "8.0.38",
    "gitVersion": "b2f7afe3a6838999fd375c7a7ea678189f795568"
  },
  "serverParameters": {
    "internalQueryFacetBufferSizeBytes": 104857600,
    "internalQueryFacetMaxOutputDocSizeBytes": 104857600,
    "internalLookupStageIntermediateDocumentMaxSizeBytes": 104857600,
    "internalDocumentSourceGroupMaxMemoryBytes": 104857600,
    "internalQueryMaxBlockingSortMemoryUsageBytes": 104857600,
    "internalQueryProhibitBlockingMergeOnMongoS": 0,
    "internalQueryMaxAddToSetBytes": 104857600,
    "internalDocumentSourceSetWindowFieldsMaxMemoryBytes": 104857600,
    "internalQueryFrameworkControl": "trySbeRestricted",
    "internalQueryPlannerIgnoreIndexWithCollationForRegex": 1
  },
  "command": {
    "aggregate": "events",
    "pipeline": [
      {
        "$match": {
          "user_id": 1,
          "event_type": "product_view",
          "occurred_at": {
            "$gte": {
              "$date": "2026-05-24T17:35:04.911Z"
            }
          }
        }
      },
      {
        "$group": {
          "_id": "$product_id",
          "viewed_at": {
            "$max": "$occurred_at"
          }
        }
      },
      {
        "$sort": {
          "viewed_at": -1
        }
      },
      {
        "$limit": 5
      }
    ],
    "cursor": {},
    "$db": "ecommerce"
  },
  "ok": 1.0
}
```

</details>

### Query 3: Variants with stock under 5

MySQL only. A range scan on `idx_variants_stock` finds all the variants under 5 units. Each product name comes from a primary key lookup.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT v.variant_id, v.sku, v.size, v.color, v.stock_quantity, p.product_id, p.name FROM product_variants v JOIN products p ON p.product_id = v.product_id WHERE v.stock_quantity < 5 ORDER BY v.stock_quantity, v.variant_id;
```

```
+----+-------------+-------+------------+--------+-----------------------------------------+--------------------+---------+------------------------+------+----------+-----------------------+
| id | select_type | table | partitions | type   | possible_keys                           | key                | key_len | ref                    | rows | filtered | Extra                 |
+----+-------------+-------+------------+--------+-----------------------------------------+--------------------+---------+------------------------+------+----------+-----------------------+
|  1 | SIMPLE      | v     | NULL       | range  | idx_variants_product,idx_variants_stock | idx_variants_stock | 4       | NULL                   | 1579 |   100.00 | Using index condition |
|  1 | SIMPLE      | p     | NULL       | eq_ref | PRIMARY                                 | PRIMARY            | 8       | ecommerce.v.product_id |    1 |   100.00 | NULL                  |
+----+-------------+-------+------------+--------+-----------------------------------------+--------------------+---------+------------------------+------+----------+-----------------------+
```

</details>

### Query 4: Fashion products in blue or size Large

MySQL only. The fashion products and their variants are found through indexes (`slug`, `idx_products_category`, `idx_variants_product`). The blue/Large and stock conditions are applied afterward as filters. Note that we don't use an index on this last filter since size+color indexes would be too much overhead.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT p.product_id, p.name, p.base_price, v.variant_id, v.size, v.color, v.price, v.stock_quantity FROM products p JOIN categories c ON c.category_id = p.category_id JOIN product_variants v ON v.product_id = p.product_id WHERE c.slug = 'fashion' AND (v.color = 'blue' OR v.size = 'Large') AND v.stock_quantity > 0 AND v.is_active = 1 AND p.is_active = 1 ORDER BY p.product_id, v.variant_id;
```

```
+----+-------------+-------+------------+-------+------------------------------------------------------------------------------------------+-----------------------+---------+------------------------+------+----------+----------------------------------------------+
| id | select_type | table | partitions | type  | possible_keys                                                                            | key                   | key_len | ref                    | rows | filtered | Extra                                        |
+----+-------------+-------+------------+-------+------------------------------------------------------------------------------------------+-----------------------+---------+------------------------+------+----------+----------------------------------------------+
|  1 | SIMPLE      | c     | NULL       | const | PRIMARY,slug                                                                             | slug                  | 402     | const                  |    1 |   100.00 | Using index; Using temporary; Using filesort |
|  1 | SIMPLE      | p     | NULL       | ref   | PRIMARY,idx_products_category                                                            | idx_products_category | 8       | const                  |  625 |    10.00 | Using where                                  |
|  1 | SIMPLE      | v     | NULL       | ref   | idx_variants_product,idx_variants_stock,idx_variants_color_stock,idx_variants_size_stock | idx_variants_product  | 8       | ecommerce.p.product_id |    2 |     2.21 | Using where                                  |
+----+-------------+-------+------------+-------+------------------------------------------------------------------------------------------+-----------------------+---------+------------------------+------+----------+----------------------------------------------+
```

</details>

### Query 5: Page-view count per product

MongoDB counts the `product_view` events with an index scan on `(event_type, product_id)`: it reads 275,491 index entries and 0 documents. MySQL then reads every product name with a full table scan, which is fine because the answer includes all 5,000 products anyways. The sort is done in Python since we need the results from MongoDB and MySQL to sort.

<details>
<summary>Raw MongoDB explain: db.events.aggregate(...)</summary>

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
        "stages": "[3] project [s7 = newBsonObj(\"_id\", s4, \"views\", s6)] \n[3] project [s6 = (convert ( s5, int32) ?: s5)] \n[3] group [s4] [s5 = count()] spillSlots[s3] mergingExprs[sum(s3)] \n[3] project [s4 = (s1 ?: null)] \n[1] ixseek KS(3C70726F647563745F76696577000A0104) KS(3C70726F647563745F7669657700F0FE04) none s2 none none [s1 = 1] @\"e193b9a5-a961-4041-87cf-375a36e497c1\" @\"event_type_1_product_id_1\" true "
      }
    },
    "rejectedPlans": []
  },
  "executionStats": {
    "executionSuccess": true,
    "nReturned": 5000,
    "executionTimeMillis": 50,
    "totalKeysExamined": 275491,
    "totalDocsExamined": 0,
    "executionStages": {
      "stage": "project",
      "planNodeId": 3,
      "nReturned": 5000,
      "executionTimeMillisEstimate": 46,
      "opens": 1,
      "closes": 1,
      "saveState": 3,
      "restoreState": 3,
      "isEOF": 1,
      "projections": {
        "7": "newBsonObj(\"_id\", s4, \"views\", s6) "
      },
      "inputStage": {
        "stage": "project",
        "planNodeId": 3,
        "nReturned": 5000,
        "executionTimeMillisEstimate": 46,
        "opens": 1,
        "closes": 1,
        "saveState": 3,
        "restoreState": 3,
        "isEOF": 1,
        "projections": {
          "6": "(convert ( s5, int32) ?: s5) "
        },
        "inputStage": {
          "stage": "group",
          "planNodeId": 3,
          "nReturned": 5000,
          "executionTimeMillisEstimate": 46,
          "opens": 1,
          "closes": 1,
          "saveState": 3,
          "restoreState": 3,
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
            "executionTimeMillisEstimate": 42,
            "opens": 1,
            "closes": 1,
            "saveState": 3,
            "restoreState": 3,
            "isEOF": 1,
            "projections": {
              "4": "(s1 ?: null) "
            },
            "inputStage": {
              "stage": "ixseek",
              "planNodeId": 1,
              "nReturned": 275491,
              "executionTimeMillisEstimate": 31,
              "opens": 1,
              "closes": 1,
              "saveState": 3,
              "restoreState": 3,
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
  "queryShapeHash": "BEA436D0FDB2F6E544A6744B4A5102B5BA7A90E52B245274F5E2B6C2EF75944F",
  "command": {
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
    "cursor": {},
    "$db": "ecommerce"
  },
  "serverInfo": {
    "host": "63c422aab0b2",
    "port": 27017,
    "version": "8.0.38",
    "gitVersion": "b2f7afe3a6838999fd375c7a7ea678189f795568"
  },
  "serverParameters": {
    "internalQueryFacetBufferSizeBytes": 104857600,
    "internalQueryFacetMaxOutputDocSizeBytes": 104857600,
    "internalLookupStageIntermediateDocumentMaxSizeBytes": 104857600,
    "internalDocumentSourceGroupMaxMemoryBytes": 104857600,
    "internalQueryMaxBlockingSortMemoryUsageBytes": 104857600,
    "internalQueryProhibitBlockingMergeOnMongoS": 0,
    "internalQueryMaxAddToSetBytes": 104857600,
    "internalDocumentSourceSetWindowFieldsMaxMemoryBytes": 104857600,
    "internalQueryFrameworkControl": "trySbeRestricted",
    "internalQueryPlannerIgnoreIndexWithCollationForRegex": 1
  },
  "ok": 1.0
}
```

</details>

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT product_id, name FROM products;
```

```
+----+-------------+----------+------------+------+---------------+------+---------+------+------+----------+-------+
| id | select_type | table    | partitions | type | possible_keys | key  | key_len | ref  | rows | filtered | Extra |
+----+-------------+----------+------------+------+---------------+------+---------+------+------+----------+-------+
|  1 | SIMPLE      | products | NULL       | ALL  | NULL          | NULL | NULL    | NULL | 4940 |   100.00 | NULL  |
+----+-------------+----------+------------+------+---------------+------+---------+------+------+----------+-------+
```

</details>

### Query 6: Sarah's search terms (30 days)

MongoDB only. The `(user_id, event_type, occurred_at)` index matches the filter exactly, so only the 8 matching documents are read. Grouping by term and time of day is done in Python.

<details>
<summary>Raw MongoDB explain: db.events.find(...)</summary>

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
            "$gte": {
              "$date": "2026-10-23T17:35:05.452Z"
            }
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
              "[new Date(9223372036854775807), new Date(1792776905452)]"
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
                  "$gte": {
                    "$date": "2026-10-23T17:35:05.452Z"
                  }
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
              "[new Date(9223372036854775807), new Date(1792776905452)]"
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
  "queryShapeHash": "478B6CC35C84489F60E2CDD4306882B4811AC47AA717A5A18E448E5DFEEFA007",
  "command": {
    "find": "events",
    "filter": {
      "user_id": 1,
      "event_type": "search",
      "occurred_at": {
        "$gte": {
          "$date": "2026-10-23T17:35:05.452Z"
        }
      }
    },
    "projection": {
      "_id": 0,
      "search_term": 1,
      "occurred_at": 1
    },
    "$db": "ecommerce"
  },
  "serverInfo": {
    "host": "63c422aab0b2",
    "port": 27017,
    "version": "8.0.38",
    "gitVersion": "b2f7afe3a6838999fd375c7a7ea678189f795568"
  },
  "serverParameters": {
    "internalQueryFacetBufferSizeBytes": 104857600,
    "internalQueryFacetMaxOutputDocSizeBytes": 104857600,
    "internalLookupStageIntermediateDocumentMaxSizeBytes": 104857600,
    "internalDocumentSourceGroupMaxMemoryBytes": 104857600,
    "internalQueryMaxBlockingSortMemoryUsageBytes": 104857600,
    "internalQueryProhibitBlockingMergeOnMongoS": 0,
    "internalQueryMaxAddToSetBytes": 104857600,
    "internalDocumentSourceSetWindowFieldsMaxMemoryBytes": 104857600,
    "internalQueryFrameworkControl": "trySbeRestricted",
    "internalQueryPlannerIgnoreIndexWithCollationForRegex": 1
  },
  "ok": 1.0
}
```

</details>

### Query 7: Active carts

MySQL only. This scans all of `carts` (about 105,000 rows) to find all the active ones, because the only index with `status` starts with `user_id`. The cart items and prices are then found through primary keys.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT c.cart_id, c.user_id, c.last_device, CAST(COALESCE(SUM(i.quantity), 0) AS UNSIGNED) AS item_count, COALESCE(SUM(i.quantity * v.price), 0) AS total_amount FROM carts c LEFT JOIN cart_items i ON i.cart_id = c.cart_id LEFT JOIN product_variants v ON v.variant_id = i.variant_id WHERE c.status = 'active' GROUP BY c.cart_id, c.user_id, c.last_device ORDER BY c.cart_id;
```

```
+----+-------------+-------+------------+--------+---------------+---------+---------+------------------------+--------+----------+----------------------------------------------+
| id | select_type | table | partitions | type   | possible_keys | key     | key_len | ref                    | rows   | filtered | Extra                                        |
+----+-------------+-------+------------+--------+---------------+---------+---------+------------------------+--------+----------+----------------------------------------------+
|  1 | SIMPLE      | c     | NULL       | ALL    | NULL          | NULL    | NULL    | NULL                   | 105728 |    33.33 | Using where; Using temporary; Using filesort |
|  1 | SIMPLE      | i     | NULL       | ref    | PRIMARY       | PRIMARY | 8       | ecommerce.c.cart_id    |      1 |   100.00 | NULL                                         |
|  1 | SIMPLE      | v     | NULL       | eq_ref | PRIMARY       | PRIMARY | 8       | ecommerce.i.variant_id |      1 |   100.00 | NULL                                         |
+----+-------------+-------+------------+--------+---------------+---------+---------+------------------------+--------+----------+----------------------------------------------+
```

</details>

### Query 8: Sarah's orders

MySQL only. Sarah's orders come from `idx_orders_user_date`, and the shipping option, payment, items and variants are all reached through indexes. This query does no table scans.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT o.order_id, o.placed_at, o.status, o.total_amount, s.name AS shipping_option, pay.method_type AS payment_method, i.product_name_snapshot AS product_name, v.size, v.color, i.quantity, i.unit_price FROM orders o JOIN shipping_options s ON s.shipping_option_id = o.shipping_option_id JOIN payments pay ON pay.order_id = o.order_id JOIN order_items i ON i.order_id = o.order_id JOIN product_variants v ON v.variant_id = i.variant_id WHERE o.user_id = 1 ORDER BY o.placed_at, o.order_id, i.order_item_id;
```

```
+----+-------------+-------+------------+--------+--------------------------------------------------------+-----------------------+---------+--------------------------------+------+----------+---------------------------------+
| id | select_type | table | partitions | type   | possible_keys                                          | key                   | key_len | ref                            | rows | filtered | Extra                           |
+----+-------------+-------+------------+--------+--------------------------------------------------------+-----------------------+---------+--------------------------------+------+----------+---------------------------------+
|  1 | SIMPLE      | o     | NULL       | ref    | PRIMARY,idx_orders_user_date,fk_orders_shipping_option | idx_orders_user_date  | 8       | const                          |   13 |   100.00 | Using temporary; Using filesort |
|  1 | SIMPLE      | s     | NULL       | eq_ref | PRIMARY                                                | PRIMARY               | 8       | ecommerce.o.shipping_option_id |    1 |   100.00 | NULL                            |
|  1 | SIMPLE      | pay   | NULL       | ref    | idx_payments_order                                     | idx_payments_order    | 8       | ecommerce.o.order_id           |    1 |   100.00 | NULL                            |
|  1 | SIMPLE      | i     | NULL       | ref    | idx_order_items_order,idx_order_items_variant          | idx_order_items_order | 8       | ecommerce.o.order_id           |    2 |   100.00 | NULL                            |
|  1 | SIMPLE      | v     | NULL       | eq_ref | PRIMARY                                                | PRIMARY               | 8       | ecommerce.i.variant_id         |    1 |   100.00 | NULL                            |
+----+-------------+-------+------------+--------+--------------------------------------------------------+-----------------------+---------+--------------------------------+------+----------+---------------------------------+
```

</details>

### Query 9: Sarah's returns

MySQL only. Everything is reached through indexes: First with Sarah's orders through `idx_orders_user_date` alone, then their items through `idx_order_items_order`, then the returns through `idx_returns_order_item`.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT r.return_id, o.order_id, i.product_name_snapshot AS product_name, r.quantity, r.resolution, r.status, r.refund_status, r.exchange_status, r.refund_amount, r.restocking_fee, r.requested_at FROM `returns` r JOIN order_items i ON i.order_item_id = r.order_item_id JOIN orders o ON o.order_id = i.order_id WHERE o.user_id = 1 ORDER BY r.requested_at;
```

```
+----+-------------+-------+------------+------+-------------------------------+------------------------+---------+---------------------------+------+----------+----------------------------------------------+
| id | select_type | table | partitions | type | possible_keys                 | key                    | key_len | ref                       | rows | filtered | Extra                                        |
+----+-------------+-------+------------+------+-------------------------------+------------------------+---------+---------------------------+------+----------+----------------------------------------------+
|  1 | SIMPLE      | o     | NULL       | ref  | PRIMARY,idx_orders_user_date  | idx_orders_user_date   | 8       | const                     |   13 |   100.00 | Using index; Using temporary; Using filesort |
|  1 | SIMPLE      | i     | NULL       | ref  | PRIMARY,idx_order_items_order | idx_order_items_order  | 8       | ecommerce.o.order_id      |    2 |   100.00 | NULL                                         |
|  1 | SIMPLE      | r     | NULL       | ref  | idx_returns_order_item        | idx_returns_order_item | 8       | ecommerce.i.order_item_id |    1 |   100.00 | NULL                                         |
+----+-------------+-------+------------+------+-------------------------------+------------------------+---------+---------------------------+------+----------+----------------------------------------------+
```

</details>

### Query 10: Average days between Sarah's purchases

MySQL only. One lookup on `idx_orders_user_date` returns Sarah's orders already in date order, so no sorting is needed. The gaps between dates are calculated in Python.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT placed_at FROM orders WHERE user_id = 1 AND status <> 'cancelled' ORDER BY placed_at;
```

```
+----+-------------+--------+------------+------+----------------------------------------+----------------------+---------+-------+------+----------+-------------+
| id | select_type | table  | partitions | type | possible_keys                          | key                  | key_len | ref   | rows | filtered | Extra       |
+----+-------------+--------+------------+------+----------------------------------------+----------------------+---------+-------+------+----------+-------------+
|  1 | SIMPLE      | orders | NULL       | ref  | idx_orders_user_date,idx_orders_status | idx_orders_user_date | 8       | const |   13 |    83.33 | Using where |
+----+-------------+--------+------------+------+----------------------------------------+----------------------+---------+-------+------+----------+-------------+
```

</details>

### Query 11: Carts created in 30 days that never converted

MySQL only. The 30-day-window is a range scan on `idx_carts_created`. Each cart is checked against the unique `cart_id` index on `orders` to see whether an order exists. MySQL estimates about 38,000 rows for the range scan, but the query actually matches about 18,500 carts.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT COUNT(*) AS carts_created, CAST(COALESCE(SUM(o.order_id IS NULL), 0) AS UNSIGNED) AS never_converted FROM carts c LEFT JOIN orders o ON o.cart_id = c.cart_id WHERE c.created_at >= NOW() - INTERVAL 30 DAY;
```

```
+----+-------------+-------+------------+--------+-------------------+-------------------+---------+---------------------+-------+----------+--------------------------+
| id | select_type | table | partitions | type   | possible_keys     | key               | key_len | ref                 | rows  | filtered | Extra                    |
+----+-------------+-------+------------+--------+-------------------+-------------------+---------+---------------------+-------+----------+--------------------------+
|  1 | SIMPLE      | c     | NULL       | range  | idx_carts_created | idx_carts_created | 8       | NULL                | 38274 |   100.00 | Using where; Using index |
|  1 | SIMPLE      | o     | NULL       | eq_ref | cart_id           | cart_id           | 8       | ecommerce.c.cart_id |     1 |   100.00 | Using index              |
+----+-------------+-------+------------+--------+-------------------+-------------------+---------+---------------------+-------+----------+--------------------------+
```

</details>

### Query 12: Top 3 products bought with headphones

Neo4j only. It finds the Headphones category through the category name index, follows it to its products and all orders that contain them, then to every product in those orders (52,671 rows). Removing the other headphones is the most expensive step. The rest are grouped by product and the top 3 kept.

<details>
<summary>Raw Neo4j PROFILE</summary>

```cypher
PROFILE MATCH (:Category {name: 'Headphones'})<-[:IN_CATEGORY]-(:Product)<-[:CONTAINS]-(o:Order) WITH DISTINCT o MATCH (o)-[:CONTAINS]->(other:Product) WHERE NOT (other)-[:IN_CATEGORY]->(:Category {name: 'Headphones'}) RETURN other.product_id AS product_id, other.name AS name, count(DISTINCT o) AS orders_together ORDER BY orders_together DESC, product_id LIMIT 3;
```

```
+------------------------------------------------------+
| product_id | name                  | orders_together |
+------------------------------------------------------+
| 5000       | "Notebook 05000"      | 18              |
| 966        | "Skin Cleanser 00966" | 17              |
| 600        | "Cookbook 00600"      | 16              |
+------------------------------------------------------+

+-------------------------------------------------------------------------------------------------+
| Plan      | Statement   | Version | Planner | Runtime   | Time | DbHits | Rows | Memory (Bytes) |
+-------------------------------------------------------------------------------------------------+
| "PROFILE" | "READ_ONLY" | "5"     | "COST"  | "SLOTTED" | 150  | 631794 | 3    | 3255368        |
+-------------------------------------------------------------------------------------------------+


Cypher 5

Planner COST

Runtime SLOTTED

Runtime version 5.26.33

+-------------------+----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| Operator          | Id | Details                                                                                              | Estimated Rows | Rows  | DB Hits | Memory (Bytes) | Page Cache Hits/Misses | Ordered by                           |
+-------------------+----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +ProduceResults   |  0 | product_id, name, orders_together                                                                    |              3 |     3 |       0 |              0 |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+                                      |
| +Top              |  1 | orders_together DESC, product_id ASC LIMIT 3                                                         |              3 |     3 |       0 |            880 |                    0/0 | orders_together DESC, product_id ASC |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +EagerAggregation |  2 | cache[other.product_id] AS product_id, cache[other.name] AS name, count(DISTINCT o) AS orders_togeth |             69 |  4368 |       0 |        2686752 |                    0/0 |                                      |
| |                 |    | er                                                                                                   |                |       |         |                |                        |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +CacheProperties  |  3 | cache[other.product_id], cache[other.name]                                                           |           4703 | 27791 |   55582 |                |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +Filter           |  4 | other:Product                                                                                        |           4703 | 27791 |   27791 |                |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +AntiSemiApply    |  5 |                                                                                                      |           4770 | 27791 |       0 |                |                    0/0 |                                      |
| |\                +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| | +Expand(Into)   |  6 | (other)-[anon_5:IN_CATEGORY]->(anon_6)                                                               |              3 |     0 |  291146 |            904 |                    0/0 |                                      |
| | |               +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| | +NodeIndexSeek  |  7 | RANGE INDEX anon_6:Category(name) WHERE name = $autostring_1                                         |            596 | 52671 |  105342 |                |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +Expand(All)      |  8 | (o)-[anon_4:CONTAINS]->(other)                                                                       |           4771 | 52671 |   98419 |                |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +Distinct         |  9 | o                                                                                                    |           2380 | 22874 |       0 |         786512 |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +Filter           | 10 | o:Order                                                                                              |           2505 | 24880 |   24880 |                |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +Expand(All)      | 11 | (anon_2)<-[anon_3:CONTAINS]-(o)                                                                      |           2505 | 24880 |   27380 |                |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +Filter           | 12 | anon_2:Product                                                                                       |             63 |   625 |     625 |                |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +Expand(All)      | 13 | (anon_0)<-[anon_1:IN_CATEGORY]-(anon_2)                                                              |             63 |   625 |     627 |                |                    0/0 |                                      |
| |                 +----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+
| +NodeIndexSeek    | 14 | RANGE INDEX anon_0:Category(name) WHERE name = $autostring_0                                         |              0 |     1 |       2 |                |                    0/0 |                                      |
+-------------------+----+------------------------------------------------------------------------------------------------------+----------------+-------+---------+----------------+------------------------+--------------------------------------+

Total database accesses: 631794, total allocated memory: 3255368

3 rows
ready to start consuming query after 1 ms, results consumed after another 149 ms
```

</details>

### Query 13: Days since last purchase and order count, per user

MySQL only. `users` is fully scanned (about 10,000 rows) because the solution needs every user. Each user's orders come from `idx_orders_user_date` and we filter out cancelled orders.

<details>
<summary>Raw MySQL EXPLAIN</summary>

```sql
EXPLAIN SELECT u.user_id, u.full_name, COUNT(o.order_id) AS total_orders, DATEDIFF(NOW(), MAX(o.placed_at)) AS days_since_last_purchase FROM users u LEFT JOIN orders o ON o.user_id = u.user_id AND o.status <> 'cancelled' GROUP BY u.user_id, u.full_name ORDER BY u.user_id;
```

```
+----+-------------+-------+------------+------+----------------------------------------+----------------------+---------+---------------------+-------+----------+---------------------------------+
| id | select_type | table | partitions | type | possible_keys                          | key                  | key_len | ref                 | rows  | filtered | Extra                           |
+----+-------------+-------+------------+------+----------------------------------------+----------------------+---------+---------------------+-------+----------+---------------------------------+
|  1 | SIMPLE      | u     | NULL       | ALL  | NULL                                   | NULL                 | NULL    | NULL                | 10015 |   100.00 | Using temporary; Using filesort |
|  1 | SIMPLE      | o     | NULL       | ref  | idx_orders_user_date,idx_orders_status | idx_orders_user_date | 8       | ecommerce.u.user_id |    10 |   100.00 | Using where                     |
+----+-------------+-------+------------+------+----------------------------------------+----------------------+---------+---------------------+-------+----------+---------------------------------+
```

</details>
