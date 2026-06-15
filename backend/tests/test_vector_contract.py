"""Contract: finalize's vector update uses the canonical store interface and
reports an explicit status. Uses in-memory stubs (no network, no DB)."""

import asyncio
from typing import Any, Dict, List, Optional

from app.services.finalize_service import FinalizeService


class StubLLMService:
    async def get_embedding(self, text: str, *, user_id: Optional[int] = None, model: Optional[str] = None) -> List[float]:
        return [0.1, 0.2, 0.3]


class StubVectorStore:
    def __init__(self) -> None:
        self.add_calls: List[Dict[str, Any]] = []

    async def upsert_chunks(self, records: List[Dict[str, Any]]):
        self.add_calls.extend(records)

    async def upsert_summaries(self, records: List[Dict[str, Any]]):
        self.add_calls.extend(records)

    async def delete_by_chapters(self, project_id: str, chapters: List[int]):
        return


async def _run() -> None:
    vector = StubVectorStore()
    service = FinalizeService(db=None, llm_service=StubLLMService(), vector_store_service=vector)  # type: ignore[arg-type]

    status = await service._update_vector_store(
        project_id="proj",
        chapter_number=1,
        chapter_text="这是一段用于切分与向量化的章节正文，足够触发分块逻辑。",
        user_id=1,
    )

    assert status["status"] == "updated", status
    assert vector.add_calls, "vector store should receive records"


def test_finalize_updates_vector_store():
    asyncio.run(_run())
