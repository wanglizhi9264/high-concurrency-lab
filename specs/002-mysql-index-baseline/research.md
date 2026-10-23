# Research: official documentation
Checked 2026-10-23; research delegated by official Plan skill.
- Decision: physical two-stage migrations (0002 baseline,0003 indexes). FK user_id index retained. Alternatives: invisible indexes still consume space and write cost, cannot prove full baseline.
  https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html
  https://dev.mysql.com/doc/refman/8.4/en/invisible-indexes.html
- Decision: actual TREE raw plan + per-iterator rows/loops; leaf access rows*loops reported with definition. actual times ms, iterator time includes children and averages per loop; do not sum node times or call root LIMIT output scanned rows.
  https://dev.mysql.com/doc/refman/8.4/en/explain.html
- Decision: stable DESC (created_at,id), disjunctive keyset predicate. Cursor lookup cost separately measured. No mutation during queries; tuple comparison not assumed optimal.
  https://dev.mysql.com/doc/refman/8.4/en/limit-optimization.html
  https://dev.mysql.com/doc/refman/8.4/en/row-constructor-optimization.html
- Decision: table DATA_LENGTH clustered allocated estimate, INDEX_LENGTH secondary allocated estimate, count(*) exact; ANALYZE before snapshots.
  https://dev.mysql.com/doc/refman/8.4/en/information-schema-tables-table.html
- Decision: DBeaver properties and Explain UI for inspection, actual ANALYZE explicitly in SQL editor; UI/edition differences documented.
  https://dbeaver.com/docs/dbeaver/Properties-Editor/
  https://dbeaver.com/docs/dbeaver/Creating-Indexes/
  https://dbeaver.com/docs/dbeaver/Query-Execution-Plan/
No unresolved technical unknowns. Isolation via separate instance avoids shared foundation data/benchmark interference. New databases provisioned only from fixed allowlist, never deleted by experiment scripts.
