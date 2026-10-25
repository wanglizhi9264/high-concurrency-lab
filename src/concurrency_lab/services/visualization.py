"""Curated architecture and allowlisted, schema-validated recorded evidence."""

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from concurrency_lab.schemas.visualization import (
    Architecture,
    ArchitectureEdge,
    ArchitectureNode,
    ExperimentDetail,
    ExperimentSummary,
    PlanNode,
    QueryMetric,
    RecordedResult,
    ResultPair,
    SourceRef,
)

EXPERIMENT_ID = "002-mysql-index-baseline"
ROOT = Path(os.environ.get("CONCURRENCY_LAB_ROOT", Path(__file__).resolve().parents[3])).resolve()
RESULT_ROOT = ROOT / "docs/experiments/002-mysql-index-baseline/runs"
SCALES = (10000, 100000, 1000000)
QUERIES = ("primary_key", "by_user", "user_time", "offset", "keyset", "email")
LIMITATIONS = [
    "真实002记录：7次暖缓存采样、单客户端、并发1，不代表线上P99或并发API RPS。",
    ("访问行数=scan/lookup节点actual rows×loops，不是物理IO或LIMIT输出。"),
    "CPU/内存利用率未采集；游标定位成本单独记录，不能当成免费随机跳页。",
]


class DataUnavailable(Exception):
    pass


def source(path: str, label: str = "源码", revision: str = "main") -> SourceRef:
    return SourceRef(
        path=path,
        label=label,
        url=f"https://github.com/wanglizhi9264/high-concurrency-lab/blob/{revision}/{path}",
    )


def result_source(scale: int, phase: str) -> SourceRef:
    path = (
        "docs/experiments/002-mysql-index-baseline/runs/"
        f"concurrency_lab_exp_002_{scale}-{phase}.json"
    )
    return source(path, f"{phase} 原始JSON", "881a638ba5c17b58d0751cd296249361b8ee762c")


def load_result(scale: int, phase: Literal["baseline", "optimized"]) -> RecordedResult:
    if scale not in SCALES or phase not in ("baseline", "optimized"):
        raise ValueError("Unsupported scale")
    root = RESULT_ROOT.resolve()
    path = root / f"concurrency_lab_exp_002_{scale}-{phase}.json"
    try:
        if path.resolve().parent != root or path.stat().st_size > 2_000_000:
            raise DataUnavailable()
        result = RecordedResult.model_validate_json(path.read_bytes())
        if (
            result.phase != phase
            or result.dataset.order_count != scale
            or result.database != f"concurrency_lab_exp_002_{scale}"
            or result.dataset.counts.get("lab_order") != scale
            or result.dataset.counts.get("lab_order_item") != scale * 2
        ):
            raise DataUnavailable()
        return result
    except (OSError, ValidationError, ValueError) as exc:
        raise DataUnavailable() from exc


def result_pair(scale: int) -> ResultPair:
    baseline, optimized = load_result(scale, "baseline"), load_result(scale, "optimized")
    if baseline.dataset != optimized.dataset:
        raise DataUnavailable()
    return ResultPair(
        baseline=baseline,
        optimized=optimized,
        sources=[result_source(scale, "baseline"), result_source(scale, "optimized")],
        limitations=LIMITATIONS,
    )


def parse_plan_tree(query: QueryMetric) -> list[PlanNode]:
    roots: list[PlanNode] = []
    stack: list[tuple[int, PlanNode]] = []
    metrics = iter(query.iterators)
    for number, line in enumerate(query.explain_analyze_tree.splitlines()):
        if not line.strip():
            continue
        depth = len(line) - len(line.lstrip())
        node = PlanNode(
            id=f"plan-{number}",
            label=line.strip().removeprefix("-> ").split(" (cost=")[0].split(" (actual time=")[0],
            metrics=next(metrics, None) if "(actual time=" in line else None,
        )
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if stack:
            stack[-1][1].children.append(node)
        else:
            roots.append(node)
        stack.append((depth, node))
    return roots


def experiment_detail() -> ExperimentDetail:
    return ExperimentDetail(
        id=EXPERIMENT_ID,
        title="MySQL 索引与分页基线",
        status="measured",
        scales=list(SCALES),
        source=source("docs/experiments/002-mysql-index-baseline/report.md", "实验报告"),
        objective="用真实数据解释索引、排序与深分页的工作量变化。",
        question="为什么只返回20行，底层却可能访问100万行？",
        hypothesis="合适的复合索引减少排序；已知边界的Keyset减少深页跳过。",
        parameters=[
            "订单10k / 100k / 1m，每单两明细",
            "seed=20261023，batch=1000",
            "基线0002 → 索引0003，保留主键及外键索引",
            "固定6类SQL，7次预热后wall采样",
        ],
        observations=[
            "百万OFFSET P50：414.68 → 153.84ms",
            "已知游标Keyset P50：172.30 → 2.89ms",
            "部分小规模查询没有变快，原始结果完整保留。",
        ],
        explanation=[
            "先对照访问路径：Table scan → Index scan/range scan，再看访问行数。",
            "索引增加存储与写入维护成本，不是无代价的提速。",
            "通过相同数据摘要、CHECKSUM和同页ID验证对照对象一致。",
        ],
        limitations=LIMITATIONS + ["没有冷缓存、写入前后或并发负载对照。"],
        sources=[
            source("src/concurrency_lab/experiments/queries.py", "查询定义"),
            source("src/concurrency_lab/experiments/dataset.py", "数据生成"),
            source("docs/experiments/002-mysql-index-baseline/dbeaver.md", "DBeaver教程"),
        ],
    )


def summaries() -> list[ExperimentSummary]:
    return [
        ExperimentSummary.model_validate(
            experiment_detail().model_dump(include=set(ExperimentSummary.model_fields))
        )
    ]


def architecture() -> Architecture:
    entries: list[tuple[Any, ...]] = [
        (
            "client",
            "Client / 浏览器",
            "入口",
            "connected",
            "发送HTTP，展示响应与浏览器往返时间。",
            "用户操作",
            "HTTP请求",
            "浏览器渲染/网络",
            "DevTools与performance.now对照",
            "frontend/src/views/TraceView.vue",
            0,
            0,
        ),
        (
            "router",
            "FastAPI Router",
            "HTTP",
            "connected",
            "匹配端点并将结果映射为HTTP状态。",
            "HTTP请求",
            "响应模型",
            "同步阻塞/序列化",
            "比较handler区间，不伪造路由匹配耗时",
            "src/concurrency_lab/api/routes/visualization.py",
            235,
            0,
        ),
        (
            "service",
            "Health Service",
            "逻辑",
            "connected",
            "并发执行有超时的MySQL和Redis探针。",
            "共享资源",
            "ok/unavailable",
            "慢依赖/超时",
            "对照两个真实probe事件区间",
            "src/concurrency_lab/services/health.py",
            470,
            0,
        ),
        (
            "pool",
            "SQLAlchemy / Pool",
            "资源",
            "connected",
            "Engine复用连接池，通过engine.connect获取连接。",
            "SELECT 1",
            "结果/连接归还",
            "容量/连接获取",
            "真实gauges；纯排队时间尚未独立观测",
            "src/concurrency_lab/db/session.py",
            470,
            150,
        ),
        (
            "mysql",
            "MySQL 8.4",
            "存储",
            "connected",
            "健康探针实际执行SELECT 1；002独立库保存实验数据。",
            "固定SQL",
            "查询结果",
            "扫描行数/排序/IO",
            "EXPLAIN ANALYZE与真实索引对照",
            "src/concurrency_lab/experiments/runner.py",
            235,
            150,
        ),
        (
            "session",
            "ORM Session",
            "教学旁路",
            "teaching",
            "已定义请求级Session DI；当前健康探针直接使用Engine，不经过此节点。",
            "业务事务（后续）",
            "事务作用域",
            "长事务/共享Session",
            "get_session与已有Session集成测试",
            "src/concurrency_lab/db/session.py",
            0,
            150,
        ),
        (
            "redis",
            "Redis 7 / PING",
            "健康依赖",
            "connected",
            "此健康路径仅执行PING；独立业务缓存也复用lifespan客户端。",
            "PING",
            "PONG",
            "连接/命令超时",
            "真实trace中的Redis probe",
            "src/concurrency_lab/cache/client.py",
            470,
            -150,
        ),
        (
            "cache",
            "Redis 业务缓存",
            "商品副本",
            "connected",
            "006已实现独立商品Cache-Aside，健康PING不经过此路径；实际状态见缓存实验页。",
            "缓存实验商品读",
            "校验后的商品副本",
            "命令预算/TTL/版本与lease发布检查",
            "实际命中、回源、失效与降级Trace",
            "src/concurrency_lab/services/product_cache.py",
            235,
            -150,
        ),
    ]
    nodes = [
        ArchitectureNode(
            id=e[0],
            label=e[1],
            kind=e[2],
            status=e[3],
            responsibility=e[4],
            input=e[5],
            output=e[6],
            bottleneck=e[7],
            validation=e[8],
            source=source(e[9]),
            x=e[10],
            y=e[11],
        )
        for e in entries
    ]
    pairs = [
        ("client", "router", False),
        ("router", "service", False),
        ("service", "pool", False),
        ("pool", "mysql", False),
        ("service", "redis", False),
        ("service", "session", True),
        ("redis", "cache", True),
    ]
    edges = [
        ArchitectureEdge(
            id=f"{a}-{b}", source=a, target=b, teaching=t, label="教学 / 未执行" if t else ""
        )
        for a, b, t in pairs
    ]
    return Architecture(
        nodes=nodes,
        edges=edges,
        startup=[],
        limitations=[
            "健康检查实际使用Engine，不经过ORM Session。虚线为教学/未来路径。",
            "Engine和Redis客户端创建为lazy，不证明启动时已经连上依赖。",
        ],
    )
