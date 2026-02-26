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
        item = {
            "id": str(uuid4()),
            "name": name,
            "connection_type": connection_type,
            "credentials": credentials,
            "owner_role": owner_role,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
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

