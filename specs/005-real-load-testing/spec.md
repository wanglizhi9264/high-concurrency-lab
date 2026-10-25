# Feature Specification: Real Concurrent Load Testing
**Feature Branch**: feature/005-real-load-testing | **Created**:2026-10-25 | **Status**:Ready
## User Scenarios & Testing *(mandatory)*
### User Story1 - Run controlled actual workloads (Priority:P1)
Learners execute real business reads with10/50/100/500simulatedusers, configurable startup/pacing and connectionpoolconfigurations.
**Why**: Business reads exist; concurrent evidence is required before caching claims.
**Independent Test**: Real short runs preserve rawstats/history/errors/resource observations and exactparameter/window metadata.
**Acceptance**: Given an initialized ownedbusinessDB, when running hotspot/normal/deeppaging requests, then actualrequest/error/timeout/latency/throughput values and achievedusers are saved, without modifying002evidence. Sameparameterpair differs only inpoolsize; a pacingpair differs only inpacing. Closedloop targets are never mislabeledopenarrival guarantees.
### User Story2 - Compare honest measurements (Priority:P1)
Learners choose two recorded runs and inspect genuine time-series, parameters, sample windows and resource scopes.
**Independent Test**: Frontend values matchvalidatedstoredrecords; missing metrics displayunmeasured, notzero.
**Acceptance**: Given two runs, when comparing, then RPS, instrumentedSQLQPS, P50/95/99,errorrate,timeouts,poolgauges,MySQLconnections andCPU/memory are explained by actualsources/units/windows. Historypercentiles are neveraveraged intooverallpercentiles.
### User Story3 - Maintain safe reproducibility (Priority:P2)
Developers run normalCI withoutlongload and independentlytrigger boundedperformance suites.
**Independent Test**: Unit/API/parser/browserchecks run inCI; dedicatedmanualperformanceworkflow andlocalrunbook reproduciblycreateactualrecords.
**Acceptance**: Arbitraryfile/SQL/shell/path requests refused; partialruns retained butnotpublished ascomplete; noCLI run can overwritepreviousdata.
### Edge Cases
Dependency/poolerrors are measured outcomes, not runnerfailure. Rejectedsettings/unsafehosts/invalidIDs refusedbeforestart. CSVN/A becomesnull. Short runs include ramp and warm-up/cachelimitations. CurrentRPS/currentpercentiles and cumulativecounts have differentwindows. Resources may beunavailable; samples recordfailure explicitly. Runtime<=300seconds, usersallowlist, loopbacktargetonly; measurements readonly againstownedbusinessDB.
## Requirements *(mandatory)*
- **FR-001** MUST offer10/50/100/500users, distinct users/s startup and per-userclosedloop pacing, real hotspot/normal/deeppage cases and configurablebusinesspool.
- **FR-002** MUST preserve actualrawLocustCSV/counters, actualstart/end window, dataset/environment/versions/configuration, explicitunits/semantics, errors andtimeoutcategories.
- **FR-003** MUST observe RPS, instrumentedSQLQPS, latencypercentiles, errors,timeouts,poolgauges,MySQLconnections and scopedCPU/memory with unmeasurednulls and monitoring-overhead notes.
- **FR-004** MUST expose bounded validatedrecordedresults through readonlyallowlistedAPI andrealVuecomparison/time-series; never runload fromHTTP.
- **FR-005** MUST runactualmatrix andcontrolledpool/pacingcomparisons, retainallresults withoutpromisinglargerpoolsarebetter.
- **FR-006** MUST testmetrics/parsing/safety/API/frontend, preservegates, keepheavyloadmanuallytriggered anddocument/review/Converge/PR.
### Key Entities
RunManifest, LocustSummary, HistorySample, ResourceSample, Counters, RecordedLoadRun.
## Success Criteria *(mandatory)*
- **SC-001** Allfourconcurrencysettings produceactualretainedruns with genuinewindowandparameters.
- **SC-002** Atleastonecontrolledpoolpair andonepacingpair can beinspected andcompared withno fabricatedmeasurements.
- **SC-003** UI curves andsummaries reproduce savedvalues anddistinguish missing/cumulative/rolling/scopedmetrics.
- **SC-004** Normalquality/regressionCI andreadonlyresultAPItests pass; longperformanceload isopt-in, reviewedevidence available.
## Assumptions
Locallearning only, no productioncapacityclaim. Short15secondsmoke matrix, explicitlyramp-inclusive; user-configurablelongerruns requiredforcapacityconclusions. Reuse004owned10000orderdataset, addfixedglobaltimepagedordersread fortruedeepOFFSET onthisdataset. NoRedis cache/inventory/workerbeforetheirfeatures. No newruntimeframework.
