# Research — 009
Read-only research dispatched per official speckit-plan to business_research and frontend_audit; neither edited files, ran containers or mutated data. All technical unknowns resolved.

## Decisions
Two evolving full-data twins use identical PK(id,created_at), columns and eachphase indexes; separate empty writeprobes avoid querydatasetmutation. Independent ScaleBase/migrations/009allowlist preserves002 and global0001–0005. Single-columnuser baseline→user/time+globaltime→user/time/id/total/status covering. Real chosenpath mustprovecoverage; projectiontotal/status matters. Using index condition is ICP, notcoverage. RANGE COLUMNS quarterly2025 plusfutureMAXVALUE; actualEXPLAIN selectedpartitions, neverassume functionpredicatealwaysnonpruning. Analyticalcopy has noFK/id-onlyDBunique; generator and streamingDBvalidation verifyiduniqueness/content.

Batchgenerator year-distributed,tiedtimestamps,canonicalrowSHAindependentbatchsize. Stream orderedDBrows forSHA/count/yearcounts; avoid onlyCHECKSUMoraggregate identity. DDL/indexbuild/ANALYZE/identityvalidation excludedfromquerytimers. Writeprobe50kfromempty,execute+COMMIT perbatch,rotateorder,actualsizes/indexDDL;cannotinfermillion-existing-rowwriteamplification. No redo/globalparameter changes. Source009identity includes scripts/migrations, not onlyoldsource_identity subset.

Reuse percentiles/actualTREEparser and exclusive savepattern; extract actuallyshared005resource samplers preservingexports. Do not reuse002dataset/query/database validators (oldtables/single-day/frozenstages). Per-indexpartitionstats names must retainpartitionidentity andunknownreasons.

API/UI separate009DTOs, fixedtrustedrecords, ID/size/symlink/containment/manifestvalidation. IncludeDockerfile009records. RenderSQLparams/actualcoverage/partitions/write/approximateallocation/resourceunits/nulls; no fakecurves or heavyHTTPstart.

Cleanclone needs explicituniqueCOMPOSE_PROJECT_NAME (env overtop-levelname; -p strongest), newports/volumes, CONCURRENCY_LAB_ROOT=clone. provision_index_lab --project-name mandatorybecauseitoverridesenv; businessprovision/LocustDockerps inheritenv. Locustforcesbusinessdatabase=concurrency_lab_business,soinitializebothbusiness/test. PlaywrightmustconfigurenewAPI/frontportsandproxy,reusepolicy;fixed18002/5174wouldhitdeveloperpreview. Never useoldacceptance_local.py(defaultstop/down). Existingworkeracceptanceuniqueclone008outputcanbereferenced/exported; no overwrite.

## Primary sources verified
- https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations-partitioning-keys-unique-keys.html
- https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations-storage-engines.html
- https://dev.mysql.com/doc/refman/8.4/en/explain-output.html
- https://dev.mysql.com/doc/refman/8.4/en/partitioning-pruning.html
- https://dev.mysql.com/doc/refman/8.4/en/optimizing-innodb-bulk-data-loading.html
- https://dev.mysql.com/doc/refman/8.4/en/optimization-indexes.html
- https://docs.docker.com/compose/how-tos/project-name/

Alternatives rejected:full-sizecopiesfor3indexstagesaddunnecessaryload;businessFKpartitionmodelnotlegal;PK-onlybaselinewouldnotfulfillsingle-columncomparison;asynchronousbackgroundHTTPexperimentsunsafe/unneeded;automaticshardingnotjustified. Shardingcomplexityreviewfollowsactualresults.
