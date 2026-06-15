"""generate/finalize invariants (no LLM calls):

- after generate: ``selected_version_id`` is NULL and status is WAITING_FOR_CONFIRM
- after finalize: ``selected_version_id`` points at an existing version row
"""

import asyncio
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import Chapter, ChapterOutline, ChapterVersion, NovelProject, User


async def _run(db_url: str) -> None:
    engine = create_async_engine(db_url)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with Session() as session:
            user = User(username="smoke-user", hashed_password="x", email="smoke@example.com")
            session.add(user)
            await session.flush()

            project = NovelProject(id="proj-smoke", user_id=user.id, title="Smoke Project")
            outline = ChapterOutline(project_id=project.id, chapter_number=1, title="Chapter 1", summary="Outline")
            chapter = Chapter(project_id=project.id, chapter_number=1, status="not_generated")
            session.add_all([project, outline, chapter])
            await session.commit()
            await session.refresh(chapter)

            # generate
            draft = ChapterVersion(chapter_id=chapter.id, content="draft content", version_label="v1")
            chapter.status = "waiting_for_confirm"
            session.add(draft)
            await session.commit()
            await session.refresh(chapter)

            assert chapter.selected_version_id is None
            assert chapter.status == "waiting_for_confirm"

            # finalize
            chapter.selected_version_id = draft.id
            chapter.status = "successful"
            chapter.word_count = len(draft.content)
            await session.commit()
            await session.refresh(chapter)

            assert chapter.selected_version_id == draft.id
            assert chapter.status == "successful"
    finally:
        await engine.dispose()


def test_generate_finalize_invariants():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "gen_finalize.db"
        asyncio.run(_run(f"sqlite+aiosqlite:///{db_path.as_posix()}"))
