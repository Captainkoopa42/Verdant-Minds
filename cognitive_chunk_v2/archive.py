from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .models import CognitiveChunkV2


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class ResourceStore:
    resources: dict[str, bytes] = field(default_factory=dict)

    def put_bytes(self, path: str, data: bytes) -> str:
        normalized = path.replace("\\", "/").lstrip("/")
        if not normalized:
            raise ValueError("Resource path cannot be empty.")
        self.resources[normalized] = bytes(data)
        return normalized

    def get_bytes(self, path: str) -> bytes:
        return self.resources[path]

    def put_array(self, path: str, array: np.ndarray) -> str:
        buffer = io.BytesIO()
        np.save(buffer, np.asarray(array))
        return self.put_bytes(path, buffer.getvalue())

    def get_array(self, path: str) -> np.ndarray:
        return np.load(io.BytesIO(self.get_bytes(path)))

    def manifest(self) -> dict[str, dict[str, int | str]]:
        return {
            path: {
                "sha256": sha256_bytes(data),
                "byte_length": len(data),
            }
            for path, data in sorted(self.resources.items())
        }


class CognitiveChunkArchive:
    CHUNK_PATH = "chunk.json"
    RESOURCE_MANIFEST_PATH = "resource_manifest.json"

    @classmethod
    def save(
        cls,
        path: Path,
        chunk: CognitiveChunkV2,
        store: ResourceStore,
    ) -> None:
        manifest = store.manifest()
        with zipfile.ZipFile(
            path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                cls.CHUNK_PATH,
                chunk.model_dump_json(indent=2),
            )
            archive.writestr(
                cls.RESOURCE_MANIFEST_PATH,
                json.dumps(manifest, indent=2, sort_keys=True),
            )
            for resource_path, data in sorted(store.resources.items()):
                archive.writestr(
                    f"resources/{resource_path}",
                    data,
                )

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        verify: bool = True,
    ) -> tuple[CognitiveChunkV2, ResourceStore]:
        with zipfile.ZipFile(path, "r") as archive:
            chunk = CognitiveChunkV2.model_validate_json(
                archive.read(cls.CHUNK_PATH)
            )
            manifest = json.loads(
                archive.read(cls.RESOURCE_MANIFEST_PATH).decode("utf-8")
            )
            store = ResourceStore()
            for resource_path in manifest:
                data = archive.read(f"resources/{resource_path}")
                store.put_bytes(resource_path, data)

        if verify:
            cls.verify_resources(store, manifest)
        return chunk, store

    @staticmethod
    def verify_resources(
        store: ResourceStore,
        expected_manifest: dict[str, dict[str, int | str]],
    ) -> None:
        actual = store.manifest()
        if actual != expected_manifest:
            raise ValueError("Archive resource integrity verification failed.")
