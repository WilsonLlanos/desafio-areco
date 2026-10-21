import dataclasses

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.ingestion import ingerir
from app.main import create_app


@pytest.fixture(scope="session")
def settings(tmp_path_factory) -> Settings:
    s = load_settings()
    return dataclasses.replace(s, log_dir=tmp_path_factory.mktemp("logs"))


@pytest.fixture(scope="session")
def db_settings(settings) -> Settings:
    """Settings com banco carregado; testes que dependem dele são ignorados se o banco não responder."""
    try:
        ingerir(settings)
    except psycopg.OperationalError as e:
        pytest.skip(f"PostgreSQL indisponível: {e}")
    return settings


@pytest.fixture()
def client(db_settings) -> TestClient:
    return TestClient(create_app(db_settings))


@pytest.fixture()
def client_sem_banco(settings) -> TestClient:
    quebrado = dataclasses.replace(settings, db_host="127.0.0.1", db_port=1)
    return TestClient(create_app(quebrado))


@pytest.fixture()
def conn(db_settings):
    from app.db import connect_ro
    with connect_ro(db_settings) as c:
        yield c
