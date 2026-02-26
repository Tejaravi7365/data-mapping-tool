import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class AuditLogStore:
    """
    JSON-backed audit event store.
    """

    def __init__(self, path: str = "app/data/audit_logs.json") -> None:
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

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None

    def create(
        self,
        actor: str,
        action: str,
        details: str,
        status: str = "Success",
        target: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        rows = self._load()
        now = datetime.utcnow().isoformat() + "Z"
        item = {
            "id": str(uuid4()),
            "created_at": now,
            "actor": actor,
            "action": action,
            "details": details,
            "status": status,
            "target": target or "",
            "metadata": metadata or {},
        }
        rows.append(item)
        self._save(rows)
        return item

    def list_filtered(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        rows = self._load()
        if actor:
            actor_norm = actor.strip().lower()
            rows = [r for r in rows if str(r.get("actor", "")).strip().lower() == actor_norm]
        if action:
            action_norm = action.strip().lower()
            rows = [r for r in rows if str(r.get("action", "")).strip().lower() == action_norm]
        if status:
            status_norm = status.strip().lower()
            rows = [r for r in rows if str(r.get("status", "")).strip().lower() == status_norm]
        from_dt = self._parse_iso(from_ts)
        to_dt = self._parse_iso(to_ts)
        if from_dt:
            rows = [
                r
                for r in rows
                if (self._parse_iso(str(r.get("created_at", ""))) or datetime.min.replace(tzinfo=timezone.utc)) >= from_dt
            ]
        if to_dt:
            rows = [
                r
                for r in rows
                if (self._parse_iso(str(r.get("created_at", ""))) or datetime.min.replace(tzinfo=timezone.utc)) <= to_dt
            ]
        rows = sorted(rows, key=lambda r: str(r.get("created_at", "")), reverse=True)
        return rows[: max(1, min(int(limit), 1000))]

