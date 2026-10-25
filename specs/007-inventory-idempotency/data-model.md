# Data Model
InventoryScenario(UUIDhexPK, productFK, initial, available,reserved,sold,createdUTC): allcountsnonnegative, sum=initial. Scenarioidentityimmutable; createwithsameid+sameproduct/initialreplays, mismatchconflicts.
PurchaseOrder(BIGINTPK, scenarioFK,userFK,UUIDkeyUNIQUE,payloadSHA256,qty1..100,unitpriceDECIMAL12,2,totalDECIMAL14,2,status,created/updatedUTC). total=qty*price. FingerprintcanonicalJSONscenario/user/qty; UUIDcanonicalized. OneSKUperorder, pricecapturedfromMySQL, notRedis/client.
State: initialreserved; reserved→paid orcancelled. Samefinaltargetidempotent; crossfinaltransitioninvalid. CountersmoveinoneDBtransaction. Constraintsalwaysenforced.
Audit: scenario, bystatequantities/ordercounts, sampledUTC, checksavailable_balance/reserved_matches/paid_matches, all_pass. Cancelledhistoricalunitsseparate, notconsumedstock.
ScenarioResult/OrderResult include replay/appliedflags; InventoryResponse holdsfeaturedata/error/BusinessTrace. Old004BusinessResponse.dataunionnotexpanded. RequestIDdistinctfromkey/orderID.
