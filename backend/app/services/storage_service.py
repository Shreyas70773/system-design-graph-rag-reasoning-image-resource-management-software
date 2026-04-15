"""
Storage service for user-uploaded assets.

Supports:
- Cloudflare R2 (if configured and boto3 is available)
- Local uploads fallback under backend/uploads
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import uuid

from app.config import get_settings


@dataclass
class StoredFile:
    url: str
    key: str
    storage_backend: str


class StorageService:
    def __init__(self):
        self.settings = get_settings()
        self.upload_root = Path(__file__).resolve().parents[2] / "uploads"
        self.upload_root.mkdir(parents=True, exist_ok=True)

    def _r2_configured(self) -> bool:
        return bool(
            self.settings.cloudflare_account_id
            and self.settings.cloudflare_r2_access_key
            and self.settings.cloudflare_r2_secret_key
            and self.settings.cloudflare_r2_bucket
        )

    @staticmethod
    def _extension_from_content_type(content_type: str) -> str:
        mapping = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/svg+xml": "svg",
        }
        return mapping.get(content_type.lower(), "bin")

    async def save_logo(self, brand_id: str, filename: str, content_type: str, data: bytes) -> StoredFile:
        ext = self._extension_from_content_type(content_type)
        object_key = f"brands/{brand_id}/logos/{uuid.uuid4().hex}.{ext}"

        if self._r2_configured():
            stored = await self._save_to_r2(object_key, content_type, data)
            if stored is not None:
                return stored

        return await self._save_local(object_key, data)

    async def _save_to_r2(self, object_key: str, content_type: str, data: bytes) -> Optional[StoredFile]:
        try:
            import boto3  # type: ignore
        except Exception:
            return None

        endpoint_url = f"https://{self.settings.cloudflare_account_id}.r2.cloudflarestorage.com"

        try:
            s3_client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.settings.cloudflare_r2_access_key,
                aws_secret_access_key=self.settings.cloudflare_r2_secret_key,
                region_name="auto",
            )
            s3_client.put_object(
                Bucket=self.settings.cloudflare_r2_bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type,
            )

            public_base = (self.settings.cloudflare_r2_public_base_url or "").strip()
            if public_base:
                url = f"{public_base.rstrip('/')}/{object_key}"
            else:
                # Fallback opaque URL format when a public endpoint is not configured.
                url = f"r2://{self.settings.cloudflare_r2_bucket}/{object_key}"

            return StoredFile(url=url, key=object_key, storage_backend="cloudflare_r2")
        except Exception:
            return None

    async def _save_local(self, object_key: str, data: bytes) -> StoredFile:
        relative_path = Path(object_key)
        local_path = self.upload_root / relative_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)

        public_url = f"/uploads/{relative_path.as_posix()}"
        return StoredFile(
            url=public_url,
            key=relative_path.as_posix(),
            storage_backend="local",
        )


_storage_singleton: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = StorageService()
    return _storage_singleton
