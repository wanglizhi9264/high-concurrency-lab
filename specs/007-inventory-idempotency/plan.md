# Implementation Plan: Transactional Inventory and Idempotency
**Branch**:feature/007-inventory-idempotency | **Date**:2026-10-25 | **Spec**:[spec.md](spec.md)

## Summary
Add independently identified single-product stock experiments and purchase orders in new Alembic0004tables. All writes use guarded owned business transactions, database constraints, conditional updates and a consistent scenario→order locking order. UUID intent keys support safe replay. Vue performs actual writes/query/audit; an acceptance script verifies committed invariants. Generated lab_order data remains untouched.

## Technical Context
Python3.12/FastAPI/SQLAlchemy2/asyncmy/MySQL8.4/Alembic, Vue3/strictTS/VTU/Playwright. No dependency changes. Single SKU per order; stock0..10000, orderquantity1..100, productID1..1000, positive bounded user/order IDs. Writes opt-in BUSINESS_WRITES_ENABLED=false by default. Existing business pool/sessionmaker reused; no Redis stock or new pool. When writes are enabled, a business-pool connect listener uniformly sets session innodb_lock_wait_timeout (default1s, bounded1..10); initialization is part of acquisition, not an invented separate request SQL span. Overall configured requestbudget; no infiniteautomaticretry.

## Constitution Check
All11principles pass pre/postdesign. I/II: real state rules in narrowdomain module, SQL repositories, transactionworkflow service, typedHTTP. III: Alembic0004only; no startupDDL. IV: MySQLconstraints/conditionalupdates/rowlocks/uniqueness, explicitcommit/rollback and outcome uncertainty. V: noRedisdependency forcorrectness; productcacheunchanged. VI: actualtransaction/DML/clientroundtrip spans, no purelockwait estimate. VII/VIII: docs/ER/ADR/unchangedlock. IX: realFK/CHECK/unique/rollback/rowlock/concurrency tests andVue/E2E. X: fixedownedDBs/writeoptin/noreset/nocredentials. XI: independentSDD/PR after006main f3ad675. Constitution2.0.0 unchanged; nohooks.

## Research decisions
Use a fresh UUID InventoryScenario rather than resetting developer stock or modifying immutable generatedorders. Scope is one product per order, exactunitprice/total snapshots fromMySQL. ScenarioUUID is also creationintent identity: matching repeatedcreate returns existing; changed product/initial under sameUUID conflicts. PurchaseOrder has globallyunique UUID idempotencykey pluscanonical payloadSHA256(scenario,user,quantity), not clientprice.

Foreign-key parent locks make insert-first orders thenstock updates prone to S→X upgrade deadlocks. Uniformwriteorder: lockScenario first, then insert/lockOrder. Creation may do an initial ordinaryidempotencylookup forquickreplay; otherwiseSELECTscenarioFORUPDATE, readauthoritativeprice, INSERTuniqueOrder, conditionalUPDATEstock(available>=quantity). FK parentXlock alreadyheld. If RR ownershipread established an oldsnapshot and INSERT hits1062, unwind/rollbackentiretransaction and readwinner in a freshSession/transaction; neverSAVEPOINT-replay in the oldsnapshot. Matchingfingerprintreplays, mismatch409. Noautochangekey.

Transition firstordinarilyreadsorder tofindimmutableScenarioID, locksScenario, then currentSELECTOrderFORUPDATE. Reserved→paid shiftsreserved→sold; reserved→cancelled shiftsreserved→available; duplicatefinaltargetno-op; paid↔cancelled rejected. No reverseorder locks in normalimplementation. Conditionalstockupdates andCHECK constraints remain authoritative evenwithlocks. Allstate changes atomic.

MySQL DDL implicitly commits: migration failures retain the scene and never auto-drop/rebuild. MySQL1213(deadlock) and1205(lockwait) explicitly causewholeapplicationtransactionrollback and safe409transaction_conflict withRetry-After. 1205onlyrollsbackstatement onserverbydefault, so applicationmustexittransaction. Unique1062resolvedasabove; FK1452mapsinvalidreference; unexpectedDBfaultsredacted. No transparentwrite retries. asyncio/clienttimeout aroundCOMMIT mayleaveunknownoutcome: preserveUUIDintent, query/replaytocheck; doNOTassertalltimeoutsmeanrollback.

## Model and migration
models/inventory.py plus0004_inventory_orders.py:
- InventoryScenario: idVARCHAR32ascii_binPK, product_idFKlab_product, initial/available/reserved/soldINTEGERnonnegative, CHECKavailable+reserved+sold=initial, created_atDATETIME(6); productFKsupportindex.
- PurchaseOrder: idBIGINTautoPK, scenario_idVARCHAR32matchingFK, user_idFKlab_user, idempotency_keyVARCHAR36ascii_binUNIQUE, payload_sha256VARCHAR64, quantityINTEGER>0<=100, unit_priceDECIMAL12,2,totalDECIMAL14,2CHECKtotal=quantity*unit_price, statusreserved/paid/cancelled, created_at/updated_atDATETIME(6), scenario/statusindex anduserFKsupportindex.
- Nochange toexistingcommercefixtures. Independentbusiness_schema CLI checksliteralDB/actualDATABASE/purpose/ready thenupgrades0004; baseinit/seed remainsfrozen0003. NormalfoundationCI mayupgrade/downgradeempty0004tables; immutable002runnerscontinuetarget0002/0003only.

## Source structure and responsibilities
- domain/inventory.py: state enum/allowedtransition, canonicalfingerprint and pureaudit arithmetic; noSQL/HTTP.
- schemas/inventory.py: UUID/bounds/exactDecimal request/ScenarioResult/OrderResult/Audit/InventoryResponse; old004dataunionunchanged.
- db/business.py: centralobservedDMLexecute helper withactualaffectedrows/insertedID, existingfetchuntouched; kindsql_execute_change separatefromfetch.
- repositories/inventory_repository.py: fixedscenario/product/order SQL, conditionalstockcounts, SELECTFORUPDATE, aggregateordersbystate. NoHTTP,Redis ortransactionownership.
- services/inventory_service.py: explicitfreshsessiontransactions, uniformlocks, idempotencyresolve, lifecycle/stateworkflow, finitebudgets andsafeerrorclassification. Sharedprivate_transaction/_bounded helpers existonlyforactualreusedresourceboundaries, not agenericframework.
- api/routes/inventory.py pluscoreconfig/exceptions/businessHTTPmapping: typedendpoints/writegate/safestatus/retryheader. mainregistersrouter, no startupmigration.
- experiments/business_schema.py: safe explicitmigrationCLI; scripts/verify_inventory_lab.py: actualbounded concurrent order/replay/state/audit evidence withfreshscenarios, uniqueoutput/noreset.
- frontend/types/observed.ts andapi/observed.ts: narrowtrace/error/sharedHTTPboundary forGET/DELETE/POSTJSON, preserve executeBusinessRequestcompatibility andoldbusiness/cachetypes. Newtypes/inventory.ts/api/inventory.ts/composables/useInventoryLab.ts/views/InventoryLabView.vue. BusinessTracePanel transaction/DMLlabels/affectedrows. Router/nav/architecturelabelsupdated.
- unit/integrationtest_inventory.py, frontend/tests/inventoryLab.test.ts, e2e/inventoryLab.spec.ts; CIexplicitmigration+INVENTORY_INTEGRATION/writeoptin; docsADR0005/inventoryguide/ER/report/README/AGENTS.

## Audit and frontend semantics
Auditreadsconsistenttransaction snapshot andindependentlySUMsreserved/paid/cancelled orderquantities. Verifyavailable+reserved+sold=initial, reservedorders=reserved, paidorders=sold; cancelledhistoricalquantityisnotcurrentoccupancy. Historicalcreatedquantitymayexceedinitial afterlegitimatecancel/reorder. TraceSQLattemptsareactual, notexpectedmultipliers. Transactionspanincludesactualcommit/rollbackexit, buterror/timeoutdoesnotproveunknowncommitabsence.

Vueprovidesnewscenario, savedorderintent, explicitnewkey, retryoriginalpayload/key, querybykey/orderID, actualpaid/cancelled, currentstock/audit. Noresetbutton. DistinguishperHTTPrequestID, stableidempotencykey andpersistentorderID. Onretry neverregenerateintent; alteredpayloadsamekeyisexplicitconflictexperiment. Vue also offers a bounded2..20client-call contest with saved per-intent UUID/payloads, actual responses, unique-order deduplication and a real GET audit afterward; eachaction loading/empty/error/retry; genuineSQL/transactionsourceinspection. Auditneverusesallhistoricalquantitiestoclaimoversell.

## Validation strategy
Testsfirstforfingerprint/states/input/writegate/drivercodes/sharedHTTPcompatibility. MigrateonlyownedtestDB. EachintegrationtestcreatesfreshscenarioUUID/intents, noresetofexistingstock/tables. Verifyactualconstraints/FKs/commits/rollback, pricefromMySQL, matching/mismatchedkeyconcurrency, distinctkeyoversellprevention, samefinalno-op/paycancelrace, insufficientstockandinvalidreferencesleavenoorder. Realrowlockheldbyindependentconnectioninduces1205androllback/retry; a controlledexternalinverselockorderexercisesactual1213, keepinginversionoutofapplication. Canceltestpausesbeforewritecommit andchecksrollback; separateunknowncommitguidancekeepsnooverclaim. Allauditsusepersistedstate. CLIcontestbounded20requests/stock5 plusduplicatereplay, transitions andfinalaudit; data/source/window/units/outcomesretained, nofakeperformance. Fullgates/review/Converge/protectedmergebefore008.
