# 02 async 的作用：把等待时间让出来

## 问题与解释

请求 A 等数据库，事件循环可以推进 B；数据库没有因此计算得更快。`await` 表示等待一个可等待对象，它不保证每次都切换，也不会把同步重计算自动变成非阻塞。把 `time.sleep()` 或大循环放进 async 函数，会占住同一事件循环。

进程有独立运行环境，线程通常共享进程内存，协程由事件循环协调。传统启用 GIL 的 CPython 中，多线程不等于 Python 字节码 CPU 并行；I/O 等待与扩展释放 GIL 又是另一回事。本项目不依赖自由线程构建。CPU 任务需要评估进程或专用执行器，不能盲目加 `async`。

Engine 管理连接池，Session 管理一次工作中的数据库交互状态，Transaction 是提交/回滚边界。三个不是同一个对象。每个请求自己的 Session，但共用 lifespan 持有的 Engine/池。共享 Session 给并发 Task，就像两个人同时用同一张未结账单，彼此提交和回滚会冲突。

`async with` 控制进入/退出：正常退出 begin 提交，异常退出回滚，退出 Session 释放资源。取消也要经过清理，不能随手 `except BaseException` 然后返回成功。`asyncio.timeout` 只限定等待预算，不证明远端数据库操作从未提交。

## 源码入口

[main lifespan](../../src/concurrency_lab/main.py) 创建/关闭资源；[Engine](../../src/concurrency_lab/db/session.py) 配池；[owned_session](../../src/concurrency_lab/db/business.py) 建每次事务；[库存服务](../../src/concurrency_lab/services/inventory_service.py) 将超时/冲突分类。

## 动手操作

在仓库根目录用 `uv run python` 进入交互解释器，粘贴：

```python
import asyncio, time


async def job():
    await asyncio.sleep(0.1)


async def main():
    started = time.perf_counter()
    await asyncio.gather(job(), job())
    print(time.perf_counter() - started)


asyncio.run(main())
```

只在这个独立例子里把 await sleep 改成 `time.sleep(0.1)`，重新运行比较。再运行 `uv run pytest tests/unit/test_health.py -q`。真实取消回归在[库存集成测试](../../tests/integration/test_inventory.py)的 cancel_before_commit 与 request_budget 用例，需要 owned test 库及 `INVENTORY_INTEGRATION=1`。

## 预期现象

异步等待可重叠，同步 sleep 会串行占用事件循环；具体耗时以本机为准，调度与系统负载会引入误差。这是调度示例，不是数据库吞吐测试。

池大小5不代表只能有5个 HTTP 请求；其余可能校验、查缓存或等待。请求数远超池时，等待会吃掉预算，继续加并发可能只增加超时。

## 反例

每次请求新建 Engine，会不断建立池和连接；无限增大池，则可能把排队转移到数据库。两者都没有自动扩大数据库容量。

## 自测与答案

问：`async def` 内调用同步函数会自动开线程吗？答：不会，要看框架边界或显式执行器。

问：为什么生成数据用 generator/分批？答：只保留当前批，而不是百万条对象常驻内存。列表可变与对象引用还要求避免多个并发任务共享并修改同一批状态。

## 精选参考

[Python3.12 asyncio 开发指南](https://docs.python.org/3.12/library/asyncio-dev.html)，重点看 blocking code；[SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)，看生命周期与并发使用。
