# Contracts
POST /api/v1/business/inventory/scenarios {scenario_id:UUID,product_id:1..1000,initial:0..10000};201new/200matchingreplay/409mismatch.
GET /api/v1/business/inventory/scenarios/{uuid}; currentstock.
GET /api/v1/business/inventory/scenarios/{uuid}/audit; consistentpersistedstate/aggregates, nomutation.
POST /api/v1/business/purchases/orders, Idempotency-Key:UUID, body{scenario_id:UUID,user_id:positive,quantity:1..100};201new/200matchingreplay/409mismatchorinsufficientstock.
GET /api/v1/business/purchases/orders/by-key/{uuid}; resultconfirmationafterunknownoutcome.
GET /api/v1/business/purchases/orders/{id}; persistedorder.
POST /api/v1/business/purchases/orders/{id}/state {target:paid|cancelled};200appliedorno-op/409invalidtransition.
ExplicitBUSINESS_ENABLED+BUSINESS_WRITES_ENABLEDforPOST; safe503disabled. FixedownedbusinessDBonly. Inputs422, absent404, pool503,budget504,transactionconflict409withRetry-After1. Wholewritefailuretransactionrollbackexceptcommitackuncertaintywhichrequiresconfirmationbykey. NoarbitrarySQL/reset orRedisstockroute.
Frontend/inventory-lab retainsoriginalintent/keyonretry; explicitnewintentreplacesUUID. SharedobservedHTTPhandlesJSONPOSTwithoutalteringoldGET/DELETEcontracts. DMLshowaffectedrows, transactiontimingnotpurelockwait.
