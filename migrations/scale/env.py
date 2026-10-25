"""Independent analytical migration context; only accepts an explicitly guarded connection."""

from alembic import context

from concurrency_lab.models.scale import metadata

connection = context.config.attributes.get("connection")
if connection is None:
    raise ValueError("Use the guarded009CLI; no implicit URL or startup migration")
context.configure(
    connection=connection, target_metadata=metadata, version_table="scale_alembic_version"
)
with context.begin_transaction():
    context.run_migrations()
