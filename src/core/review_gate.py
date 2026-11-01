from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class SimilarityIndex:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"records": []}, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def normalize_text(value: str) -> str:
        text = (value or "").lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def fingerprint(value: str) -> str:
        normalized = SimilarityIndex.normalize_text(value)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def register(self, artifact_id: str, text: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        index = json.loads(self.path.read_text(encoding="utf-8"))
        record = {
            "artifact_id": artifact_id,
            "fingerprint": self.fingerprint(text),
            "metadata": metadata or {},
        }
        index.setdefault("records", []).append(record)
        self.path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    def find_similar(self, text: str, *, threshold: float = 0.8) -> list[dict[str, Any]]:
        target_hash = self.fingerprint(text)
        index = json.loads(self.path.read_text(encoding="utf-8"))
        matches: list[dict[str, Any]] = []
        for record in index.get("records", []):
            if record.get("fingerprint") == target_hash:
                matches.append(record)
            elif threshold < 1.0:
                target_tokens = set(self.normalize_text(text).split())
                other_tokens = set(self.normalize_text(str(record.get("metadata", {}).get("preview", ""))).split())
                overlap = len(target_tokens & other_tokens) / max(len(target_tokens | other_tokens), 1)
                if overlap >= threshold:
                    matches.append(record)
        return matches

