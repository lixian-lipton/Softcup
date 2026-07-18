from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import UPLOAD_DIR, settings

IMAGE_SUFFIX_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def save_image_upload(upload: UploadFile, prefix: str = "upload") -> Path:
    """Validate and save an uploaded image inside the project data directory."""
    content_type = (upload.content_type or "").lower()
    if content_type not in settings.allowed_image_type_set:
        raise HTTPException(status_code=415, detail="仅支持 JPG、PNG、WebP 图片")

    suffix = IMAGE_SUFFIX_BY_TYPE.get(content_type)
    if not suffix:
        suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=415, detail="图片扩展名不受支持")
    if suffix == ".jpeg":
        suffix = ".jpg"

    max_bytes = settings.max_upload_mb * 1024 * 1024
    dest = UPLOAD_DIR / f"{prefix}_{uuid.uuid4().hex}{suffix}"
    written = 0

    try:
        with dest.open("wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"图片不能超过 {settings.max_upload_mb}MB",
                    )
                f.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if written == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="上传图片为空")
    return dest
