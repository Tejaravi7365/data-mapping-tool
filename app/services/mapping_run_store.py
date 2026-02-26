import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class MappingRunStore:
    """
    JSON-backed store for mapping execution history and dashboard metrics.
    """

    def __init__(self, path: str = "app/data/mapping_runs.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._save([])

    def _load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, rows: List[Dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def _next_run_id(self, rows: List[Dict[str, Any]]) -> str:
        max_num = 2450
        for row in rows:
            run_id = str(row.get("run_id", ""))
            if run_id.startswith("MAP-"):
                try:
                    max_num = max(max_num, int(run_id.split("-", 1)[1]))
                except Exception:
                    continue
        return f"MAP-{max_num + 1}"

    def list(self) -> List[Dict[str, Any]]:
        return self._load()

    def list_for_user(self, username: str, role: str) -> List[Dict[str, Any]]:
        rows = self._load()
        if role == "admin":
            return rows
        normalized = (username or "").strip().lower()
        return [r for r in rows if str(r.get("created_by", "")).strip().lower() == normalized]

    def create(
        self,
        created_by: str,
        source_type: str,
        target_type: str,
        source_datasource_id: str | None,
        target_datasource_id: str | None,
        source_datasource_name: str,
        target_datasource_name: str,
        source_database: str | None,
        target_database: str | None,
        source_object: str,
        target_table: str,
        total_fields: int,
        matched_fields: int,
        status: str,
    ) -> Dict[str, Any]:
        rows = self._load()
        now = datetime.utcnow().isoformat() + "Z"
        item = {
            "run_id": self._next_run_id(rows),
            "created_at": now,
            "created_by": created_by,
            "source_type": source_type,
            "target_type": target_type,
            "source_datasource_id": source_datasource_id,
            "target_datasource_id": target_datasource_id,
            "source_datasource_name": source_datasource_name,
            "target_datasource_name": target_datasource_name,
            "source_database": source_database,
            "target_database": target_database,
            "source_object": source_object,
            "target_table": target_table,
            "total_fields": int(total_fields),
            "matched_fields": int(matched_fields),
            "status": status,
            "updated_at": now,
        }
        rows.append(item)
        self._save(rows)
        return item
