import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class UserStore:
    """
    Lightweight JSON-backed user and session store.
    Roles: admin, user
    """

    _PBKDF2_ALGO = "pbkdf2_sha256"
    _PBKDF2_ITERATIONS = 310_000
    _SALT_BYTES = 16
    _SESSION_TTL_SECONDS = 8 * 60 * 60

    def __init__(self, path: str = "app/data/users.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        if not self._path.exists():
            self._seed_defaults()

    @property
    def session_ttl_seconds(self) -> int:
        return self._SESSION_TTL_SECONDS

    def _hash_password(self, password: str, salt_hex: str | None = None) -> str:
        salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(self._SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self._PBKDF2_ITERATIONS,
        )
        return f"{self._PBKDF2_ALGO}${self._PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"

    @staticmethod
    def _legacy_hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _verify_password(self, stored_hash: str, password: str) -> bool:
        if stored_hash.startswith(f"{self._PBKDF2_ALGO}$"):
            parts = stored_hash.split("$")
            if len(parts) != 4:
                return False
            _, iterations_s, salt_hex, expected_hex = parts
            try:
                iterations = int(iterations_s)
                computed = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    bytes.fromhex(salt_hex),
                    iterations,
                ).hex()
            except Exception:
                return False
            return secrets.compare_digest(computed, expected_hex)
        return secrets.compare_digest(self._legacy_hash_password(password), stored_hash)

    def _is_legacy_hash(self, stored_hash: str) -> bool:
        return not stored_hash.startswith(f"{self._PBKDF2_ALGO}$")

    def _upgrade_user_hash(self, username: str, plain_password: str) -> None:
        rows = self._load()
        updated = False
        for user in rows:
            if user.get("username") != username:
                continue
            user["password_hash"] = self._hash_password(plain_password)
            updated = True
            break
        if updated:
            self._save(rows)

    def _prune_expired_sessions(self) -> None:
        now = datetime.utcnow()
        expired = []
        for token, payload in self._sessions.items():
            expires_at = payload.get("expires_at")
            try:
                exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                exp_utc = exp.replace(tzinfo=None) if exp.tzinfo is None else exp.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                expired.append(token)
                continue
            if exp_utc <= now:
                expired.append(token)
        for token in expired:
            self._sessions.pop(token, None)

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
        self._prune_expired_sessions()
        for user in self._load():
            if user.get("username") != username:
                continue
            stored_hash = str(user.get("password_hash") or "")
            if not self._verify_password(stored_hash, password):
                continue
            if self._is_legacy_hash(stored_hash):
                self._upgrade_user_hash(username, password)
            issued_at = datetime.utcnow()
            expires_at = issued_at + timedelta(seconds=self._SESSION_TTL_SECONDS)
            token = secrets.token_urlsafe(32)
            self._sessions[token] = {
                "username": user.get("username"),
                "role": user.get("role"),
                "issued_at": issued_at.isoformat() + "Z",
                "expires_at": expires_at.isoformat() + "Z",
            }
            return token
        return None

    def get_session_user(self, token: str | None) -> Optional[Dict[str, Any]]:
        self._prune_expired_sessions()
        if not token:
            return None
        return self._sessions.get(token)

    def logout(self, token: str | None) -> None:
        if token and token in self._sessions:
            del self._sessions[token]

