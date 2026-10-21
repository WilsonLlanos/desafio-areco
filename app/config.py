"""Configuração por variáveis de ambiente."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_ro_user: str
    db_ro_password: str
    gemini_api_key: str
    gemini_model: str
    confidence_threshold: float
    data_dir: Path
    log_dir: Path
    frontend_dir: Path

    def owner_conninfo(self) -> dict:
        return dict(host=self.db_host, port=self.db_port, dbname=self.db_name,
                    user=self.db_user, password=self.db_password)

    def ro_conninfo(self) -> dict:
        return dict(host=self.db_host, port=self.db_port, dbname=self.db_name,
                    user=self.db_ro_user, password=self.db_ro_password)


def load_settings() -> Settings:
    env = os.environ.get
    return Settings(
        db_host=env("POSTGRES_HOST", "localhost"),
        db_port=int(env("POSTGRES_PORT", "5432")),
        db_name=env("POSTGRES_DB", "aurora"),
        db_user=env("POSTGRES_USER", "aurora"),
        db_password=env("POSTGRES_PASSWORD", ""),
        db_ro_user=env("DB_RO_USER", "aurora_ro"),
        db_ro_password=env("DB_RO_PASSWORD", ""),
        gemini_api_key=env("GEMINI_API_KEY", ""),
        gemini_model=env("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        confidence_threshold=float(env("CONFIDENCE_THRESHOLD", "0.6")),
        data_dir=Path(env("DATA_DIR", str(ROOT / "data"))),
        log_dir=Path(env("LOG_DIR", str(ROOT / "logs"))),
        frontend_dir=Path(env("FRONTEND_DIR", str(ROOT / "frontend"))),
    )
