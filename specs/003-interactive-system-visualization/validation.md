# 003 Validation evidence
Date:2026-10-24 (Asia/Shanghai). Branch feature/003-interactive-system-visualization.

## SDD
Official installed Spec Kit1.2.3 Agent Skills used in order Specify -> Plan -> Tasks -> Analyze -> Implement. Clarify skipped because no material architecture ambiguity; plan explicitly fixes local-only Vite proxy, replay rather than live stepping, current Engine-based health path, separate evidence modes. spec-template resolver/setup-plan/setup-tasks/check-prerequisites executed. No extension hooks configured. Constitution1.0.0 unchanged; all11principles checked before/after design. Plan used a read-only official-doc research task as requested by the skill. Sites skill local-only path used, no registration/hosting/deployment.

## Actual local checks
- Initial backend tests failed with missing visualization module before implementation; final pytest unit suite30passed.
- Ruff check/format and mypy passed (27source files).
- Frontend npm lock created; dependencies include Vue3,TypeScript,Vite8,VueRouter4,VueFlow,ECharts6,ElementPlus. No Pinia: page-local state and composables sufficient.
- npm run check: strict vue-tsc, ESLint10, Prettier all passed. Formatting conflicts were resolved by assigning formatting to Prettier, not by disabling logic checks.
- npm run test:4files/10tests passed: deterministic FIFO/timeout/deadline ties, replay pause/reset/dispose, API errors/failed trace retention, selected node synchronization, comparison numbers from actual002JSON.
- npm run build passed. Routes lazy-load; ECharts uses modular bars/components. Vendor chunks still produce Vite size warnings; not a performance benchmark failure.
- npm run test:e2e with PLAYWRIGHT_CHANNEL=msedge:2passed on actual browser, actual FastAPI+MySQL+Redis. Main test uses no mock API: graph/node details/startup, exact million-order numeric values, actual plan node rows, Live Trace HTTP200, simulation controls, experiment detail, theme and no page errors. Separate error test deliberately injects503 to check retry UI.
- CUA in-app-browser independently opened the local page, selectedMySQL and verified matching details/source. Actual collect health request showedHTTP200 and10events (2browser events plus8server events), distinct browser/server clocks. Screenshot inspection prompted a more readable compact graph layout; E2E then reran successfully.
- Existing integrations with opt-in experiments:6passed/1skipped. Skip is the002test full pipeline already completed in the retained optimized test database; no reset/destructive downgrade was used. CI fresh database runs the full4-test experiment pipeline.
- scripts/verify_index_lab.py --verify-only accepted all3scales. Git diff confirmed no002raw result changes.
- Docker image high-concurrency-lab:visualization built successfully; temporary non-root container loaded packaged002JSON (results200) and actual health trace200, then removed. Dockerfile includes trusted evidence and CONCURRENCY_LAB_ROOT=/app; frontend/node_modules excluded from context.

## Failures repaired and environment observations
First Vue build caught a multiline template handler after formatting; it was moved to an explicit typed function and build/E2E passed. First browser test used an ambiguous badge locator; scoped it to page heading, both E2E tests passed. No unexecuted test marked passed.
Local Chromium download was slow; owned installer stopped in favor of already-installedEdge. CI installs official Chromium. Initial final npm ci hit Windows EPERM because the runningVite process held the nativeRolldown library; stopped that owned process, then reran locked install and restored preview. Locked npm ci then succeeded (264packages), followed by passing npm check and10tests; local preview was restored.

## Trust and limits
No network/router match/pure pool-wait/standalone SQL duration is fabricated. Probe spans include acquisition/pre-ping/commands/close; overlapping spans not summed. Startup is lazy object creation, not dependency connection success. Browser fetch+JSON interval uses its own clock. Simulationvirtual time/650ms replay speed is not measured latency; actual DB operations are never paused by playback controls. Pool real view only instant gauges, waiting metrics null. Original002warm-cache/7sample/single-client limitations visible.
No production deployment, authentication, Locust/Prometheus/OpenTelemetry platform. Python3.11 not separately executed. UpstreamStarlette httpxTestClient deprecation warning remains. No real credentials/build output/node_modules committed. API/source paths are repository-relative public references; no arbitrary paths or SQL accepted.

## Delivery
See PR checks for exact remote commit outcomes; local checks alone do not imply remote CI passed. Final Converge reviews10FR/5SC/11principles and all10tasks before protected-branch PR merge. Actual screenshots are under docs/experiments/003-interactive-system-visualization/.
