from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

class ArtifactStore:
    def __init__(self, root_dir: str | Path):
        self.root = Path(root_dir); self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def canonical_hash(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save_json(self, name: str, payload: dict[str, Any], provenance: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {"payload": payload, "provenance": provenance or {}}
        result = {**body, "hash_sha256": self.canonical_hash(body)}
        folder = self.root / name; folder.mkdir(parents=True, exist_ok=True)
        (folder / "artifact.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
        return result

    def save_markdown(self, name: str, content: str, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
        folder = self.root / name; folder.mkdir(parents=True, exist_ok=True)
        (folder / "artifact.md").write_text(content, encoding="utf-8")
        return {"name": name, "provenance": provenance or {}, "hash_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}
