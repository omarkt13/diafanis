import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient

import models  # noqa: F401  registers ORM models on Base.metadata
from database import Base, SessionLocal, engine


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    from main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
