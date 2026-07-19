from pathlib import Path

from pydantic import Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _PYDANTIC_SETTINGS_V2 = True
except ImportError:  # pydantic v1（LoongArch 离线包）
    from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = None  # type: ignore
    _PYDANTIC_SETTINGS_V2 = False

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
SEARCH_DB = DATA_DIR / "search.db"
APP_DB = DATA_DIR / "app.db"
UPLOAD_DIR = DATA_DIR / "uploads"

for _d in (DATA_DIR, UPLOAD_DIR):
    _d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    if _PYDANTIC_SETTINGS_V2:
        model_config = SettingsConfigDict(
            env_file=str(ROOT_DIR / ".env"),
            env_file_encoding="utf-8",
            extra="ignore",
        )
    else:

        class Config:
            env_file = str(ROOT_DIR / ".env")
            env_file_encoding = "utf-8"
            extra = "ignore"
            case_sensitive = False

    app_name: str = "设备检修知识检索与作业系统"
    app_debug: bool = Field(default=True)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM: mock | local | api
    llm_mode: str = "mock"
    local_model_path: str = ""
    llm_max_tokens: int = 512
    llm_context_chars: int = 5000
    llm_api_timeout: float = 120.0

    # DeepSeek / OpenAI 兼容 API（api 模式）
    llm_api_base: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_api_model: str = "deepseek-chat"

    max_upload_mb: int = 8
    allowed_image_types: str = "image/jpeg,image/png,image/webp"
    auth_secret: str = "softcup-change-me-in-production"
    auth_token_hours: int = 168

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def local_model_exists(self) -> bool:
        return Path(self.local_model_path).is_dir()

    @property
    def allowed_image_type_set(self) -> set[str]:
        return {t.strip().lower() for t in self.allowed_image_types.split(",") if t.strip()}


settings = Settings()
