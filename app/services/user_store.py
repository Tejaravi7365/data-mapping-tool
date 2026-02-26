import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class UserStore:
    """
    Lightweight JSON-backed user and session store.
    Roles: admin, user
    """

    def __init__(self, path: str = "app/data/users.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        if not self._path.exists():
            self._seed_defaults()

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _seed_defaults(self) -> None:
        rows = [
            {
                "username": "admin",
                "password_hash": self._hash_password("admin123"),
                "role": "admin",
                "created_at": datetime.utcnow().isoformat() + "Z",
            },
            {
                "username": "user",
                "password_hash": self._hash_password("user123"),
                "role": "user",
                "created_at": datetime.utcnow().isoformat() + "Z",
            },
        ]
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, rows: List[Dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def list_users(self) -> List[Dict[str, Any]]:
        return [
            {"username": u.get("username"), "role": u.get("role"), "created_at": u.get("created_at")}
            for u in self._load()
        ]

    def create_user(self, username: str, password: str, role: str) -> Dict[str, Any]:
        rows = self._load()
        if any((u.get("username") or "").lower() == username.lower() for u in rows):
            raise ValueError("Username already exists")
        user = {
            "username": username,
            "password_hash": self._hash_password(password),
            "role": role,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        rows.append(user)
        self._save(rows)
        return {"username": username, "role": role, "created_at": user["created_at"]}

    def authenticate(self, username: str, password: str) -> Optional[str]:
        pwd_hash = self._hash_password(password)
        for user in self._load():
            if user.get("username") == username and user.get("password_hash") == pwd_hash:
                token = secrets.token_urlsafe(32)
                self._sessions[token] = {
                    "username": user.get("username"),
                    "role": user.get("role"),
                    "issued_at": datetime.utcnow().isoformat() + "Z",
                }
                return token
        return None

    def get_session_user(self, token: str | None) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        return self._sessions.get(token)

    def logout(self, token: str | None) -> None:
        if token and token in self._sessions:
            del self._sessions[token]

