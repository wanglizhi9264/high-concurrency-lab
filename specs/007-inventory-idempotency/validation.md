# Validation and review — 007

2026-10-25，feature/007-inventory-idempotency，base main f3ad675（006 PR8已合并）。Constitution2.0.0复核无需修改。Specify→Plan（官方只读研究）→Tasks→只读Analyze→Implement顺序；7FR/4SC/14任务覆盖，16项需求质量检查全通过，无阻塞Analyze findings，无extension hooks。

实际本地检查：
- Ruff/format、mypy56sourcefiles通过；完整73Python unit passed。
- 全部相关真实integration：26passed，4项002opt-in跳过。8项库存测试包含实际CHECK/FK/DECIMAL/事务提交回滚、独立键竞争、RR同键竞争、售罄重放、场景重放/改量冲突、终态竞争、1205、1213和提交前取消恢复；原004/006/foundation保留。
- 真实1213专项 `pytest -k deadlock -s` passed，实际受害者api；409映射、事务结束、外部回滚、重试和所有审计成功。测试也允许记录外部受害者，不伪造API覆盖。
- TypeScript/ESLint/Prettier passed，29Vitest/VTU及build通过；补充历史响应只检查、不改活动库存或伪造请求的回归后，最终前端结果下方补记。
- 全10Edge E2E passed（包括真实原键重放/冲突/状态/SQL影响行数及10客户端争抢3库存后的持久化审计）。改进原始JSON折叠与截图后库存2项专项也通过。
- verify_index_lab.py --verify-only：10000/100000/1000000 accepted；002/005/006原始runs未修改。0004仅显式升级business与business_test，未对实验数据做downgrade/reset。
- 两次实际CLI结果保存，最终checkpoint2fb62d6记录环境/配置/意图/SQL/审计。无并行压测、DB测试或构建干扰这两个功能实验；不作容量结论。

代码审查及修正：
1. FK父行S→X升级死锁风险：统一先Scenario后Order。真实条件UPDATE和约束仍检查影响1行。
2. RR旧快照：1062后退出整个事务，新Session读赢家；重复判断先于库存/终态判断，售罄不使同键重放失败。
3. 状态预读只取不可变场景ID，最终状态用列映射current FOR UPDATE，不依赖ORM旧实例。
4. 1205不是自动整事务回滚：应用完整退出事务；1213也不继续剩余SQL。统一session锁等待配置不改GLOBAL。
5. 初版CHECK测试错误假设asyncmy3819为IntegrityError；实际是OperationalError。改为精确断言OperationalError和3819，没有扩大生产异常捕获或降低约束验证。
6. 事务取消/ACK未知分开：只证明提交前取消回滚，网络/提交确认未知保留键确认。
7. 共享前端HTTP执行器仅依赖trace/error，旧business/cache DTO和GET/DELETE调用保留；新库存数据未塞入旧业务union。写SQL显示影响行数。
8. 前端保存原payload与UUID；新意图才换键。历史检查不计作新HTTP，不改当前库存/操作目标。批量按唯一order ID计数，审计不把cancelled历史量当占用。
9. 验收脚本补充真实业务环境监测，新增完整记录而不重写首次记录；每次只创建新UUID场景，失败/未知保留实际证据。

无新框架、无进程内/Redis锁充当库存权威、无startupDDL/create_all、无任意SQL/重置入口。每个事务使用独立Session，唯一冲突确认明确新事务；资源由lifespan持有。所有金额Decimal，配置/错误不暴露凭据。现有Starlette弃用/Vite大chunk提示保留，未降低门槛。独立PR/远程CI尚待执行，T014保持开放。

## Final review corrections
Explicit REPEATABLE READ is enforced per inventory transaction, independently of server defaults. A real test starts with READ COMMITTED and observes REPEATABLE-READ inside audit. Inventory integration9passed; frontend final30Vitest/VTU passed after historical selection regression. Final CLI rerun at clean2984f42 with actualenvironmentmonitor, retained all earlier records. Final full gates will be appended after completion.

## Final gate and Converge
After explicitRR: Ruff/format/mypy56files and73unit passed; fullintegration27passed/4opt-in skips, then additional real300ms request-budget rollback/retry case passed (28distinct integration tests verified). Frontend final30Vitest/VTU, type/lint/format/build and full10Edge E2E passed. Budget test pauses after actual reservation before commit, verifies504, no order, originalstock and same-key recovery; it does not claim ACK-unknown rollback. Converge readonly assessment covered7FR/4SC/3storygroups/14tasks, plan decisions and11constitutionprinciples. No remaining implementation findings of missing/partial/contradicts/unrequested type, allseverities0. Implementation converged; external publication/check/merge T014 pending. No empty convergence phase or hooks.

Publication verified before008: PR9 merged to protected main c9be2f46099aa07e7810ca1a368011dce1d7573a; required quality/integration/frontend passed in runs40178310514 and40178331182.
