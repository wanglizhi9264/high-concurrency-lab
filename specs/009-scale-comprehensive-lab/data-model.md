# Data model
Independent ScaleBase and scale_alembic_version, never root commerce metadata. Ownership purpose scale-lab-v1 +ready dataset enforce literal009targets. Dataset SHA/seed/count/version identifies immutable twins.

Query twins: BIGINTid,UTC-naiveDATETIME(6)created_at,syntheticuser_idBIGINT,totalDECIMAL14,2,statusVARCHAR16,payloadVARCHAR160;PK(id,created_at),nonnegative total,validstatus. All unique keys include partition column; single-id uniqueness is generated/verified, no businessFK. Partitioned twin uses quarterly2025RANGE plusfutureMAXVALUE. EqualordinaryPK avoids a partitionPKconfounder.

Three empty write probes use samecolumns/PK and appropriate baseline/composite/cover indexes; separate from querytwins. Committed50kfresh-table writes do not represent million-stockupdate amplification. Everyphase actualschema captured.

ScaleRun: immutable manifest/source/window/environment,DatasetIdentity,phasebaseline/composite/covering with2twins/querycases/rawsamples/TREE/JSON/rows/resultdigest,writeprobe batches,approximateallocationstatistics,typed resources/nulls/limits. Completeonly afterphaseorder/identity/page/summary/source checks. Partial records retained but not exposedascomplete. Queryresultpagesstablecreated_atDESC,idDESC. Resourcepoint actualtimestamp/source/scope/unit, no cross-scope summing.

CleanCloneAcceptance: uniqueproject/ports/container/volume identity,sourceHEAD, orderedStepRecords(argvredacted,start/end/elapsed/exitcode/assertion/evidencepaths),featurejourneyobservations,completefalseuntilallactualassertions. Credentials never recorded.
