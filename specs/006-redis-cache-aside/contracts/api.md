# Contracts
GET /api/v1/business/cache/products/{product_id}?mode=cache|bypass&ttl_seconds=5
GET /api/v1/business/cache/products/{product_id}/state
DELETE /api/v1/business/cache/products/{product_id}
Identifiers1..1000; TTL1..60. Responses carry existingtrace/requestheaders. Successfulread ProductDTO plus CacheObservation; state/invalidate data=null. Existing safe422/404/503/504 envelope retained. Inspectionunavailable containsnullsamples andsafe reason, no rawexception. Bypass has noRediscommands. No arbitrarykey, SQL, host, method or commandinput.
Frontend /cache-lab uses onlythese endpoints, selectedkey inspection, requesthistory/trueSQLcounts and BusinessTracePanel source links. Lastrequesterror neverdisplaysstaledata asnewsuccess. Hit-rate denominator and coverage explicit. Commandparameters never mislabeledSQL.
CLI verify_cache_lab.py targetsloopbackonly, boundedconcurrency, uniqueoutput, no DBreset. Actualresponsesretained; unknownfailedresponsesnot0SQL/hit.
