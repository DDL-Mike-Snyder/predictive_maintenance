import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_metadata_create_all_against_sqlite(db_session: AsyncSession) -> None:
    """The `db_session` fixture (tests/conftest.py) already ran
    `Base.metadata.create_all()` -- this test just asserts that succeeded
    without raising, exercising every CHECK constraint's syntax at once."""
    assert db_session is not None
