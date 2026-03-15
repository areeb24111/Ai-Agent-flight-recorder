from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def run_sqlite_migrations() -> None:
    """Apply SQLite schema migrations (add missing columns). Call from API startup and workers."""
    if "sqlite" not in str(engine.url):
        return
    with engine.connect() as conn:
        try:
            r = conn.execute(text("PRAGMA table_info(runs)"))
            cols = [row[1] for row in r]
            if "simulation_id" not in cols:
                conn.execute(text("ALTER TABLE runs ADD COLUMN simulation_id VARCHAR(36)"))
                conn.commit()
        except Exception:
            pass
        try:
            r = conn.execute(text("PRAGMA table_info(simulations)"))
            cols = [row[1] for row in r]
            if "dataset_id" not in cols:
                conn.execute(text("ALTER TABLE simulations ADD COLUMN dataset_id VARCHAR(36)"))
                conn.commit()
            if "template_config" not in cols:
                conn.execute(text("ALTER TABLE simulations ADD COLUMN template_config TEXT"))
                conn.commit()
        except Exception:
            pass


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

