# Tasks — Scale and Comprehensive Lab

## Phase 1 Setup
- [x] T001 Record ADR0007 and read-onlyPlan research/constitution gates in docs/architecture/decisions/0007-scale-partition-comparison.md and specs/009-scale-comprehensive-lab/research.md; publish008verified status.

## Phase 2 Foundation
- [x] T002 Write generator/target/optin/query identity/plan parser tests first in tests/unit/test_scale.py; enforce batch1..10000/max10000retainedbatches,repeats3..30,ten-millionexplicit,canonicalSHAindependentbatchsize andyear/tie boundaries.
- [x] T003 Add independent ScaleBase models in src/concurrency_lab/models/scale.py and migrations/scale/env.py plus scale001/002/003; identical twinsPK(id,created_at),DECIMAL14,2,quarterpartitions,appropriate indexes/probes/ownership; never editroot0001–0005.
- [x] T004 Implement strict009safety/provision/init/revision/ready checks and scopedCLI advisory lock in src/concurrency_lab/experiments/scale/safety.py and scripts/provision_scale_lab.py; nonempty/loading/foreign targets retained.

## Phase 3 US1 bounded reproducible data
Independenttest: actual1000rowtwins exactSHA/count/IDuniqueness/yearcounts,partialfailure retained; crossbatchgenerator sameidentity.
- [x] T005 [US1] Write real ownership/constraints/batch/partialseed tests in tests/integration/test_scale.py before implementation; implement deterministic streamed generation and bounded transactional twin inserts/readbackSHA in src/concurrency_lab/experiments/scale/dataset.py; fixedseed20261025,year2025,syntheticpayload,exactmoney.

## Phase 4 US2 index/partition/write experiments
Independenttest: baseline→composite→covering,actualplans/coverage/pruning,equivalentresults/pages,separatecommittedprobe counts.
- [x] T006 [US2] Write real phasegate/source/data/equivalentquery/coverage/pruning/writes tests in tests/integration/test_scale.py; implement fixed queries/parameter/result hashing and actual EXPLAIN TREE/JSON interpretation in src/concurrency_lab/experiments/scale/queries.py.
- [x] T007 [US2] Implement phase measurements and saved matching-proof-before-migration gates in src/concurrency_lab/experiments/scale/measurement.py and cli.py; warmup1/repeats7,sourcewindow/schema/rawsamples/percentiles/serialrate/errors,stableOFFSET/keyset andcursorlookupseparate; actualstreamedidentity eachphase.
- [x] T008 [US2] Implement rotating committed50kempty-write-probe comparisons,DDLbuildtime/actualindex/table/partition stats andconfounders in src/concurrency_lab/experiments/scale/writes.py;test1000probe variant; querytwins unchanged.
- [x] T009 [US2] Extract real sharedresource samplers to src/concurrency_lab/experiments/resource_sampling.py with scripts/run_load_test.py compatible reexports/regressiontests and lockeddev-only types-psutil stubs (pyproject.toml/uv.lock); implement scripts/run_scale_experiment.py ownedchild/container scope/source+script+migrationSHA/partialrawresults/CPUunknown handling; no concurrent formal work.

## Phase 5 US3 faithful recorded inspection
Independenttest: safeAPI/UIagreewithactualrecord,invalid/oversize/path/symlink503/404,unknowns/staleselectionhonest.
- [x] T010 [US3] Write recordedDTO/API security/statistic/identity tests first in tests/unit/test_scale_results.py; implement schemas/scale_experiments.py,services/scale_results.py and api/routes/scale_experiments.py strict50catalogue/8MBID/containment/manifestguards;updateDockerfile009records.
- [x] T011 [US3] Write frontend/tests/scaleLab.test.ts first; implement frontend/src/types/scaleExperiments.ts,api/scaleExperiments.ts,composables/useScaleLab.ts,views/ScaleLabView.vue androute/nav/notebooklink; originalSQL/plans/coverage/partition/write/space/resourceunits/nulls/sourceandlimits; clearlate/stale states.
- [x] T012 [US3] Add frontend/e2e/scaleLab.spec.ts comparing actualcommittedresult withAPI/selection, retainallpreviouspages/E2E; verifyvisuals andtypes/lint/build.

## Phase 6 US4 complete isolated acceptance
Independenttest: trulynewclone/project/ports/volumes runsactualfulljourneyandgates,oldresourcespreserved.
- [x] T013 [US4] Test and configure validatedE2EAPI/frontendports/proxy/reuse in frontend/playwright.config.ts, defaultsunchanged; implement scripts/verify_end_to_end.py uniqueclone/project/freeports/newignoredsecrets/safesteps/processcleanup/completefalseonfailure; never useoldacceptance_local.py ordown-v.
- [x] T014 [US4] ExtendexistingCIwithsmall009realDB/evidence/UI checks; addmanual009heavyworkflow with explicit10000..10million choice/optin,normalCInevermilliongeneration; retain3requiredjobs.
- [x] T015 [US4] Actually run source-frozen10000smoke and1000000formal serialexperiments, preserveunique docs/experiments/009-scale-comprehensive-lab/runs/ rawresults/resources/source; addverify_scale_lab.py evidenceacceptance andactualreport with supportedlimits/shardingassessment.
- [x] T016 [US4] Actuallyexecute clean-clone installation/newdependencies/ownedbusiness+testdata/API/Trace/002smoke/shortLocust/pool/cache/inventory/worker/paidreceipt thenfullquality/integration/frontend/E2E; recordallargv/outcomes/resources/evidence in docs/experiments/009-scale-comprehensive-lab/end-to-end/; preserveoldvolumes/data andstoponlyownedservices.
- [x] T017 [US4] Deliver docs/database/scale.md,docs/guides/scale-lab.md,clean-clone.md,source-reading.md and docs/architecture/final-system.md finaltree/architecture/callchain/ER/stageresults/modules/limits;updateREADME/AGENTS/overview andspecquickstart accuratecommands.

## Phase 7 Review and publication
- [x] T018 Runlocalrelatedquality/allrealintegration/frontend/evidencechecks,reviewcorrectness/resources/security/meaningfulassertions;fixandretestfindings andrecord specs/009-scale-comprehensive-lab/validation.md.
- [x] T019 Convergecurrentimplementationagainst9FR/5SC/allstories/plan/constitution;appendonlyremainingtasksifgaps,implement/retestthenrecordcleanassessmentin specs/009-scale-comprehensive-lab/converge.md.
- [ ] T020 Publish/attachindependent009PR,verifyactualprotectedCI,mergeandupdatemain;recordpublicationandfinal004–009handoff in docs/architecture/final-system.md.

## Dependencies / parallel opportunities / strategy
T001→T002→T003→T004→T005→T006→T007→T008→T009;typedrecords thenT010→T011→T012;T013/014followfixedcontracts;T015aftercleancheckpoint/stablegates,neverparalleltests/build/sourceedits;T016afterallsourcefrozen;T017–020closeevidence/docs/review/publication. Planresearchagentsread-only,implementationnotdelegated. Independent pure/APItests andfrontendchecks mayrunconcurrentlyafterchangesstabilize. MVPUS1safe1000smoke,thencompleteUS2/US3/US4beforepublication.
FR001:T002–005;FR002:T006–007;FR003:T008;FR004:T003/T006–008/T017;FR005:T009/T015;FR006:T010–012;FR007:T002/T005–006/T010–014/T018;FR008:T013/T016;FR009:T001/T017–020. SC001:T005–007/T015;SC002:T006–009/T015;SC003:T010–012;SC004:T013–016/T018;SC005:T017–020.
