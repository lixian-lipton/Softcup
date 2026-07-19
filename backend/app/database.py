from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import APP_DB

engine = create_engine(
    f"sqlite:///{APP_DB}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _table_columns(table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _ensure_column(table: str, column: str, ddl: str) -> None:
    cols = _table_columns(table)
    if not cols:
        return
    if column in cols:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def migrate_db() -> None:
    """兼容旧库：补充用户关联与标注审核字段。"""
    try:
        _ensure_column("case_studies", "user_id", "user_id INTEGER")
        _ensure_column("annotations", "user_id", "user_id INTEGER")
        _ensure_column("annotations", "status", "status VARCHAR(32) DEFAULT 'pending'")
        _ensure_column("annotations", "reviewed_at", "reviewed_at DATETIME")
    except Exception:
        # 新库无表时由 create_all 创建
        pass


def seed_admin() -> None:
    """首次启动创建默认管理员 admin / 123456。"""
    import os

    from app.models import User, UserRole
    from app.services.security import hash_password

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        password = (os.environ.get("ADMIN_PASSWORD") or "123456").strip() or "123456"

        if admin:
            # 运维重置：SOFTCUP_RESET_ADMIN_PASSWORD=1 时将 admin 口令恢复为默认/环境变量
            if os.environ.get("SOFTCUP_RESET_ADMIN_PASSWORD", "").strip() in ("1", "true", "yes"):
                admin.password_hash = hash_password(password)
                admin.is_active = True
                db.commit()
                print("[softcup] 已重置管理员密码")
            return

        db.add(
            User(
                username="admin",
                password_hash=hash_password(password),
                role=UserRole.admin,
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_db()
    seed_admin()
