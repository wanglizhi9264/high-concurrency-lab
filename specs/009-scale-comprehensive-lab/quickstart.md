# Quickstart validation

实际10k/1m已运行并通过只读验收；保留数据库不能重置重跑。新实验先准备独立实验实例和本地ignored.env；详见[完整操作指南](../../docs/guides/scale-lab.md)。

```powershell
uv sync --frozen
docker compose -f compose.yaml -f compose.experiments.yaml --profile experiments up -d --wait mysql-experiment
uv run python scripts/provision_scale_lab.py --project-name high-concurrency-lab
# 只在尚未运行的固定空库执行，源码先提交，串行运行
uv run python scripts/run_scale_experiment.py --orders 10000 --project-name high-concurrency-lab
uv run python scripts/run_scale_experiment.py --orders 1000000 --project-name high-concurrency-lab
uv run python scripts/verify_scale_lab.py
# 实际新克隆/新项目/端口/卷；不会清除已有结果
uv run python scripts/verify_end_to_end.py
```

验收顺序与断言：
1. Frozeninstall and healthyexperimentCompose; explicitprovision009targets.
2. Run10000smoke; verifybaselinefirst→composite→covering, immutableequalquerydata/pages, actualplans/partitions and50kwriteprobes. Rerunmustrefuseexistingadvanceddata/outputs.
3. Atstablecleancheckpoint, run1000000formalalone;nootherload/test/build/sourceedits. Optional10000000requiresoptin and isnotstartupprerequisite.
4. GETtrustedcatalogue and Vue/scale-lab compare rawobservations; verifyunknown/error/selectionstates.
5. Execute verify_end_to_end.py withuniqueclone/project/ports;confirmnewcontainer/volume IDs, allrealfeaturesteps andfullquality/browsergates. Preserveoutputs/volumes, stoponlyownedservices.
6. Final report/ER/callgraph/source-reading/review/Converge,protectedPRactualCI/mergebeforedeclaring004–009complete. Neveroverwrite002orpreviousrecords.
