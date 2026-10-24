# API Contract
GET /api/v1/business/products/{id}; users/{id}/orders?limit=20&offset=0 idASC; users/{id}/order-page?limit=20&offset=0&before_time=...&before_id=... timeDESC/idDESC; orders/{id} withitems via fixedJOIN.
IDs1..9223372036854775807; limit1..100; offset0..100000. Cursor fields paired and incompatible with nonzerooffset. Invalid422; missing404; disabled/notowned/db/pool503; requestbudget504. Typed data/error/trace and decimal strings. Allbusinessresponses including422 have server-generated X-Request-ID and X-Process-Time-Ms (response-start preparation, not network). No arbitrarySQL/HTTPtargetDB.
Explicit BUSINESS_ENABLED; BUSINESS_DATABASE development/test allowlist. Existing001/003 contracts unchanged.
