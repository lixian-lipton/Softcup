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
    """首次启动创建管理员；口令写入 data/INITIAL_ADMIN.txt，不在界面展示。"""
    import os
    import secrets
    from pathlib import Path

    from app.config import DATA_DIR
    from app.models import User, UserRole
    from app.services.security import hash_password

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            return

        password = (os.environ.get("ADMIN_PASSWORD") or "").strip()
        if len(password) < 8:
            password = secrets.token_urlsafe(12)

        db.add(
            User(
                username="admin",
                password_hash=hash_password(password),
                role=UserRole.admin,
                is_active=True,
            )
        )
        db.commit()

        cred_path = Path(DATA_DIR) / "INITIAL_ADMIN.txt"
        cred_path.write_text(
            "设备检修系统 — 初始管理员凭据（请妥善保管，登录后建议尽快修改）\n"
            f"username: admin\n"
            f"password: {password}\n"
            "登录页请选择「管理员」身份。\n",
            encoding="utf-8",
        )
        try:
            cred_path.chmod(0o600)
        except OSError:
            pass
        print(f"[softcup] 已创建管理员账号，初始口令见: {cred_path}")
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_db()
    seed_admin()
