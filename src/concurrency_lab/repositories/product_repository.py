"""Fixed primary-key product lookup; no HTTP or resource creation."""

from sqlalchemy import RowMapping, select

from concurrency_lab.db.business import ObservedDatabase
from concurrency_lab.models.commerce import LabProduct

SOURCE = "src/concurrency_lab/repositories/product_repository.py"


class ProductRepository:
    def __init__(self, database: ObservedDatabase) -> None:
        self.database = database

    async def get_product_by_id(self, product_id: int) -> RowMapping | None:
        with self.database.observation.span(
            "ProductRepository.get_product_by_id", "repository", SOURCE
        ):
            rows = await self.database.fetch_rows(
                select(LabProduct.__table__).where(LabProduct.id == product_id), SOURCE
            )
            return rows[0] if rows else None
