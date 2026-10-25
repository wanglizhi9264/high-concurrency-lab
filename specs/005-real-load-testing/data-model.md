# Data model
No migration. Existing owned business dataset identity is retained per run.
Manifest: safe ID, UTC start/end, monotonic duration, users/spawn/pacing/pool, dataset identity, versions/revision, peakusers/rawfiles.
Summary: requests/failures, exact raw-sample P50/P95/P99, completionRPS, observed SQL attempts/coverage, HTTP504/pool/transport timeout categories (overlap; not mutually exclusive failure totals).
HistorySample: timestamp/elapsed, completion count/rate, received SQL attempts and actual user count if observed. Original rolling Locust history separately referenced.
ResourceSample: UTC/elapsed, source/scope, nullable CPU/memory/pool/MySQL status, actual interval.
RecordedLoadRun: schema_version1, evidence=recorded, complete=true, manifest/summary/history/resources/semantics/limitations. API returns validated results, never raw exception logs. Unknowns null; nonfinite/time-order violations rejected.
