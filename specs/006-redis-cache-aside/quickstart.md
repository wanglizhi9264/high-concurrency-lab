# Quickstart validation
Use existing business-lab.md to initialize concurrency_lab_business/test and start Docker. Enable BUSINESS_ENABLED and fixedbusinessdatabase; uv sync --frozen, uv run uvicorn concurrency_lab.main:app --host127.0.0.1 --port18002, npm run dev infrontend.
Open /cache-lab: invalidateproduct1, readcached twice (miss thenhit), inspectPTTL/memory, waitpastPTTL andreadagain, bypass andcompareSQL. Actualexpiry is inferredfromwaitandmiss, not a fabricatedevent. Follow source links.
Run unit/realintegration/VTU/E2E gates described in tasks; CACHE_INTEGRATION=1 enables isolatedcachetests. verify_cache_lab.py saves boundedactualseries andconcurrency evidence; commands/options finalizedin guide duringimplement. No FLUSH or developerdatareset.
