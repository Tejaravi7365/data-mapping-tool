import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ProfileStore:
    """
    Lightweight JSON-backed connection profile store.
    Intended as a stepping stone before moving to DB + secrets manager + RBAC.
    """

    def __init__(self, path: str = "app/data/connection_profiles.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._save([])

    def _load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, profiles: List[Dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(profiles, indent=2), encoding="utf-8")

    def list_profiles(self) -> List[Dict[str, Any]]:
        return self._load()

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        for p in self._load():
            if p.get("id") == profile_id:
                return p
        return None

    def create_profile(
        self,
        name: str,
        connection_type: str,
        credentials: Dict[str, Any],
        owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        profiles = self._load()
        profile = {
            "id": str(uuid4()),
            "name": name,
            "connection_type": connection_type,
            "credentials": credentials,
            "owner": owner or "default",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        profiles.append(profile)
        self._save(profiles)
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        profiles = self._load()
        filtered = [p for p in profiles if p.get("id") != profile_id]
        if len(filtered) == len(profiles):
            return False
        self._save(filtered)
        return True

