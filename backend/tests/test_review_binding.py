"""Version/content/review binding and stale-review propagation across retries."""

import asyncio
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import (
    Chapter,
    ChapterOutline,
    ChapterSnapshot,
    ChapterVersion,
    ChapterVersionReview,
    NovelProject,
    User,
)
from app.schemas.novel import ChapterGenerationStatus
from app.services.finalize_service import FinalizeService
from app.services.novel_service import NovelService


class StubLLMService:
    async def generate(self, *args, **kwargs):
        return "stubbed"

    async def get_embedding(self, text: str, *, user_id=None, model=None):
        return [0.1, 0.2, 0.3]


async def _run_async(async_url: str):
    engine = create_async_engine(async_url)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with Session() as session:
            user = User(username="review-user", hashed_password="x", email="review@example.com")
            session.add(user)
            await session.flush()

            project = NovelProject(id="proj-review", user_id=user.id, title="Review Binding Project")
            outline = ChapterOutline(project_id=project.id, chapter_number=1, title="Chapter 1", summary="Outline")
            chapter = Chapter(project_id=project.id, chapter_number=1, status="not_generated")
            session.add_all([project, outline, chapter])
            await session.commit()
            await session.refresh(chapter)

            service = NovelService(session)

            v1 = (await service.replace_chapter_versions(
                chapter,
                ["first draft"],
                metadata=[{"lineage": {"label": "v1"}, "validation": {"ok": True, "action": "accept"}}],
            ))[0]
            reviews_v1 = (await session.execute(
                select(ChapterVersionReview).where(ChapterVersionReview.chapter_version_id == v1.id)
            )).scalars().all()
            assert reviews_v1, "v1 should have a review"
            assert reviews_v1[0].content_hash == v1.content_hash
            assert reviews_v1[0].is_stale is False

            v2 = (await service.replace_chapter_versions(
                chapter,
                ["second draft with changes"],
                metadata=[{"lineage": {"label": "v2", "parent_label": "v1"}, "validation": {"ok": True, "action": "accept"}}],
            ))[0]
            assert v1.content_hash != v2.content_hash, "hash must change when text changes"

            stale = (await session.execute(
                select(ChapterVersionReview).where(ChapterVersionReview.chapter_version_id == v1.id)
            )).scalars().all()
            assert all(r.is_stale for r in stale), "old reviews must be stale"

            fresh = (await session.execute(
                select(ChapterVersionReview).where(ChapterVersionReview.chapter_version_id == v2.id)
            )).scalars().all()
            assert fresh and fresh[0].content_hash == v2.content_hash
            assert fresh[0].is_stale is False

            return project.id, v2.id, v2.content, v2.content_hash
    finally:
        await engine.dispose()


def _finalize_sync(sync_url: str, project_id: str, v2_id: int, v2_content: str, v2_hash: str):
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    try:
        with Session() as session:
            chapter_row = session.query(Chapter).filter(
                Chapter.project_id == project_id, Chapter.chapter_number == 1
            ).first()
            chapter_row.selected_version_id = v2_id
            chapter_row.status = ChapterGenerationStatus.WAITING_FOR_CONFIRM.value
            session.commit()

            finalize = FinalizeService(session, StubLLMService(), vector_store_service=None)

            async def _noop(*args, **kwargs):
                return None

            # Stub heavy LLM/memory updates so the test stays deterministic.
            finalize._update_global_summary = _noop  # type: ignore[attr-defined]
            finalize._update_character_state = _noop  # type: ignore[attr-defined]
            finalize._save_character_state = _noop  # type: ignore[attr-defined]
            finalize._update_plot_arcs = _noop  # type: ignore[attr-defined]
            finalize._generate_chapter_summary = _noop  # type: ignore[attr-defined]

            asyncio.run(finalize.finalize_chapter(
                project_id=project_id,
                chapter_number=1,
                chapter_text=v2_content,
                user_id=1,
                skip_vector_update=True,
                chapter_version_id=v2_id,
            ))

            snapshot = session.query(ChapterSnapshot).filter(
                ChapterSnapshot.project_id == project_id,
                ChapterSnapshot.chapter_number == 1,
            ).first()
            assert snapshot is not None, "snapshot must be created"
            assert snapshot.version_id == v2_id, "snapshot should bind version_id"
            assert snapshot.content_hash == v2_hash, "snapshot should store content_hash"
    finally:
        engine.dispose()


def test_review_binding_and_stale_propagation():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "review_binding.db"
        async_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        sync_url = f"sqlite:///{db_path.as_posix()}"
        project_id, v2_id, v2_content, v2_hash = asyncio.run(_run_async(async_url))
        _finalize_sync(sync_url, project_id, v2_id, v2_content, v2_hash)
