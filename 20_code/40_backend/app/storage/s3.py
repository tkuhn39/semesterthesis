"""
@module: app.storage.s3
@context: Storage abstraction layer.
@role: S3-compatible StorageBackend (AWS S3, Cloudflare R2, Ceph radosgw,
       MinIO). All connection details come from .env via app.config. This is
       the HA-friendly backend: shared across nodes, no local state.
"""

from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import Settings
from app.storage.base import StorageBackend, normalize_key

_NOT_FOUND_CODES = {"404", "NoSuchKey", "NoSuchBucket"}


class S3StorageBackend(StorageBackend):
    """Stores objects in an S3-compatible bucket."""

    def __init__(self, settings: Settings) -> None:
        if not settings.s3_bucket:
            raise ValueError("STORAGE_BACKEND=s3 requires S3_BUCKET to be set")
        self._bucket = settings.s3_bucket
        secret = settings.s3_secret_access_key
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=secret.get_secret_value() if secret else None,
            config=Config(
                s3={"addressing_style": "path" if settings.s3_use_path_style else "virtual"}
            ),
        )

    def save_bytes(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=normalize_key(key), Body=data)

    def load_bytes(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=normalize_key(key))
        except ClientError as error:
            if _is_not_found(error):
                raise KeyError(key) from error
            raise
        data: bytes = response["Body"].read()
        return data

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=normalize_key(key))
        except ClientError as error:
            if _is_not_found(error):
                return False
            raise
        return True

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=normalize_key(key))

    def list_keys(self, prefix: str = "") -> list[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            # "Contents" is absent on an empty listing; () is a non-mutable default.
            keys.extend(item["Key"] for item in page.get("Contents", ()))
        return sorted(keys)


def _is_not_found(error: ClientError) -> bool:
    # botocore always populates Error/Code on a ClientError.
    code = str(error.response["Error"]["Code"])
    return code in _NOT_FOUND_CODES
