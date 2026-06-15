"""The single-entry vector retry service reports an explicit status."""

import asyncio
from typing import Optional

from app.services.vector_retry_service import VectorRetryService


class StubLLM:
    async def get_embedding(self, text: str, *, user_id: Optional[int] = None, model: Optional[str] = None):
        return [0.1, 0.2, 0.3]


class StubVectorStore:
    def __init__(self) -> None:
        self.chunks: list = []

    async def delete_by_chapters(self, project_id: str, chapters):
        return

    async def upsert_chunks(self, records):
        self.chunks.extend(records)

    async def upsert_summaries(self, records):
        self.chunks.extend(records)


async def _run() -> None:
    service = VectorRetryService(llm_service=StubLLM(), vector_store=StubVectorStore())  # type: ignore[arg-type]
    status = await service.retry(
        project_id="p1",
        chapter_number=1,
        title="第1章",
        content="这里是正文，用于切分和向量化。",
        user_id=1,
    )
    assert status["status"] == "updated", status


def test_vector_retry_reports_updated():
    asyncio.run(_run())
