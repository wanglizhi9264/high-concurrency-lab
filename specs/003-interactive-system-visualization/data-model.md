# Data Model
无数据库Schema变化。DTO：SourceRef(path,label,url)仅仓库相对路径；ArchitectureNode(id,label,kind,status,responsibility,input,output,bottleneck,validation,source)。
ExperimentResult完整验证002JSON所需字段：schema_version1、phase/revision、dataset/order_count/checksums、repeats、querymetrics及原始TREE；环境和空间元数据为受校验JSON对象。QueryMetric包含7样本及P50/P95/P99，不重新计算成其他口径。
PlanNode(id,label,metrics?,children)从indent与原始解析节点构建，未执行节点metrics=null。
TraceEvent(id,name,component,state,offset_ms,source,evidence,detail)；evidence=measured或simulation；时间单位ms、服务器相对handler。TraceResponse(mode,http_status,events,server_elapsed_ms,limitations)，browser roundtrip前端独立。
PoolSnapshot(mode=live,configured_size,checked_out,overflow,waiting=null,pure_wait_ms=null,observed_at)。PoolFrame(mode=simulation,at_ms,action,request_id,slots,waiting,completed,timed_out)，不从API伪造真实数据。
