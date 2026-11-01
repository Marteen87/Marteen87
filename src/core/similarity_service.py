from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any

class SimilarityIndex:
    """Artifact deduplication/retrieval only; never used as professional evidence."""
    def __init__(self, path: str | Path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists(): self.path.write_text('{"records": []}', encoding="utf-8")

    @staticmethod
    def fingerprint(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def register(self, artifact_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        row = {"artifact_id": artifact_id, "fingerprint": self.fingerprint(text), "metadata": metadata or {}}
        data.setdefault("records", []).append(row)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return row

    def find_exact(self, text: str) -> list[dict[str, Any]]:
        fp = self.fingerprint(text)
        return [r for r in json.loads(self.path.read_text(encoding="utf-8")).get("records", []) if r.get("fingerprint") == fp]
