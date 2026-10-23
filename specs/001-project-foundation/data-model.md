# Data Model
当前迁移仅 lab_marker(id BIGINT PRIMARY KEY AUTO_INCREMENT)，InnoDB/utf8mb4，无业务数据、关联或状态机。alembic_version 由 Alembic 自身管理。downgrade 删除 marker 表，属于本地验证命令，会删除该表数据。
未来订单/库存 ER 仅见 docs/database/design.md，不包含在迁移中。
