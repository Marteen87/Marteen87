from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ArtifactStore:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def save_json(self, artifact_name: str, payload: dict[str, Any], *, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
        artifact_dir = self.root_dir / artifact_name
        artifact_dir.mkdir(parents=True, exist_ok=True)
        metadata = self._normalize_payload(payload)
        metadata["provenance"] = provenance or {}
        metadata["hash_sha256"] = hashlib.sha256(json.dumps(metadata, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        target = artifact_dir / "artifact.json"
        target.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata

    def save_markdown(self, artifact_name: str, content: str, *, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
        artifact_dir = self.root_dir / artifact_name
        artifact_dir.mkdir(parents=True, exist_ok=True)
        target = artifact_dir / "artifact.md"
        target.write_text(content, encoding="utf-8")
        return {
            "artifact_name": artifact_name,
            "path": str(target),
            "provenance": provenance or {},
            "hash_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }

