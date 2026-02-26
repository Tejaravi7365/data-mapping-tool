import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class DatasourceStore:
    """
    JSON-backed datasource store for admin-managed connection definitions.
    """

    def __init__(self, path: str = "app/data/datasources.json") -> None:
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

    def list(self) -> List[Dict[str, Any]]:
        return self._load()

    def get(self, datasource_id: str) -> Optional[Dict[str, Any]]:
        for row in self._load():
            if row.get("id") == datasource_id:
                return row
        return None

    def create(
        self,
        name: str,
        connection_type: str,
        credentials: Dict[str, Any],
        owner_role: str = "all",
        created_by: str = "admin",
    ) -> Dict[str, Any]:
        rows = self._load()
        now = datetime.utcnow().isoformat() + "Z"
        item = {
            "id": str(uuid4()),
            "name": name,
            "connection_type": connection_type,
            "credentials": credentials,
            "owner_role": owner_role,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
            "diagnostics": {
                "last_tested_at": None,
                "last_test_status": "Not Tested",
                "last_test_stage": "",
                "last_test_detail": "",
                "last_test_hint": "",
            },
        }
        rows.append(item)
        self._save(rows)
        return item

    def delete(self, datasource_id: str) -> bool:
        rows = self._load()
        filtered = [r for r in rows if r.get("id") != datasource_id]
        if len(filtered) == len(rows):
            return False
        self._save(filtered)
        return True

    def update(
        self,
        datasource_id: str,
        name: str,
        connection_type: str,
        credentials: Dict[str, Any],
        owner_role: str = "all",
    ) -> Optional[Dict[str, Any]]:
        rows = self._load()
        updated_item: Optional[Dict[str, Any]] = None
        now = datetime.utcnow().isoformat() + "Z"
        for row in rows:
            if row.get("id") != datasource_id:
                continue
            row["name"] = name
            row["connection_type"] = connection_type
            row["credentials"] = credentials
            row["owner_role"] = owner_role
            row["updated_at"] = now
            updated_item = row
            break
        if not updated_item:
            return None
        self._save(rows)
        return updated_item

    def update_diagnostics(
        self,
        datasource_id: str,
        status: str,
        stage: str,
        detail: str,
        hint: str,
    ) -> Optional[Dict[str, Any]]:
        rows = self._load()
        updated_item: Optional[Dict[str, Any]] = None
        now = datetime.utcnow().isoformat() + "Z"
        for row in rows:
            if row.get("id") != datasource_id:
                continue
            diagnostics = row.get("diagnostics") or {}
            diagnostics.update(
                {
                    "last_tested_at": now,
                    "last_test_status": status,
                    "last_test_stage": stage,
                    "last_test_detail": detail,
                    "last_test_hint": hint,
                }
            )
            row["diagnostics"] = diagnostics
            row["updated_at"] = now
            updated_item = row
            break
        if not updated_item:
            return None
        self._save(rows)
        return updated_item

