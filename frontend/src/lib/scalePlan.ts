import type { PlanNode, QueryPlan } from '../types'
import type { QueryObservation } from '../types/scaleExperiments'
export function buildScalePlan(query: QueryObservation, revision: string): QueryPlan {
  const roots: PlanNode[] = [],
    stack: { depth: number; node: PlanNode }[] = []
  let metric = 0
  query.tree.split('\n').forEach((line, index) => {
    if (!line.trim()) return
    const depth = line.length - line.trimStart().length
    const node: PlanNode = {
      id: `scale-plan-${index}`,
      label: line.trim().replace(/^-> /, '').split(' (cost=')[0]!.split(' (actual time=')[0]!,
      metrics: line.includes('(actual time=') ? (query.iterators[metric++] ?? null) : null,
      children: [],
    }
    while (stack.length && stack[stack.length - 1]!.depth >= depth) stack.pop()
    if (stack.length) stack[stack.length - 1]!.node.children.push(node)
    else roots.push(node)
    stack.push({ depth, node })
  })
  return {
    sql: query.sql,
    parameters: query.parameters,
    raw_tree: query.tree,
    tree: roots,
    source: {
      path: 'src/concurrency_lab/experiments/scale/measurement.py',
      label: '实际查询测量源码',
      url: `https://github.com/wanglizhi9264/high-concurrency-lab/blob/${revision}/src/concurrency_lab/experiments/scale/measurement.py`,
    },
    note: '实际迭代器输出行数 × loops 不是物理 I/O；嵌套算子时间不能直接相加。',
  }
}
