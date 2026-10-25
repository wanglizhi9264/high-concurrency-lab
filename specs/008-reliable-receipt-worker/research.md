# Research: Durable receipt tasks

## Decision and alternatives
Use MySQL durable task/outbox/attempt/event/receipt records and Redis7 Streams as at-least-once transport. Existing dependencies suffice. Celery/RQ add an unnecessary framework for one handler; DB polling alone does not demonstrate a broker; in-process callbacks are not durable. ADR0006 accepted before implementation.

## Verified protocol details
Official Plan read-only agents audited current resources,007transactions and redis-py7.4.1. Explicit XGROUP id0-0 avoids dropping already published messages. XAUTOCLAIM has three return items in Redis7; continue its cursor. XREADGROUP BLOCK100ms stays below socket timeout1s; no noack or Redis8-only options. XACK removes PEL, not stream data.

Database lease/token and database UTC time fence all final success/failure. Claim commits before handler and releases Session. Receipt(order_id) uniqueness uses explicit no-op duplicate update plus current read; never continue a failed Session or INSERT IGNORE. Publisher candidates are ordinary reads; actual lock order Task→Outbox is explicit. Periodic due/cooldown scans heal Redis loss, trimming and stale running ownership. A final exhausted crash becomes retained failed.

Creation acceptance, publication, receipt success and ACK are separate observations. Missing outbox confirmation may follow successful XADD; missing ACK event may follow successful ACK. XLEN/pending/group lag/database counts have different scopes. Controlled fault plans are configuration, actual attempts/timings are measured; crash times stay unknown. Commit/transport ACK loss is unknown outcome with stable UUID retries.

## Real test design
Actual unavailable broker, post-XADD/pre-mark crash, post-DB/pre-ACK failure, same-order concurrent tasks, deadline/fail-first/exhaustion/linked retry, subprocess crash after committed claim, stale token, exact-scope stream deletion and repair, malformed/wrong-scope delivery. Every worker/stream/database scope is explicit, no FLUSH or developer resets. Child process test observes committed claim/exit, not arbitrary sleeps. Fixtures are UI contract tests only.

## Sources
https://redis.io/docs/latest/commands/xgroup-create/
https://redis.io/docs/latest/commands/xreadgroup/
https://redis.io/docs/latest/commands/xautoclaim/
https://redis.io/docs/latest/commands/xack/
https://redis.io/docs/latest/commands/xlen/
https://redis.io/docs/latest/commands/xpending/
https://redis.io/docs/latest/commands/xinfo-groups/
https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html

No unresolved design clarification.
