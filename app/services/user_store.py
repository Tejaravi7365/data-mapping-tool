import hashlib
import json
import os
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
    _DEFAULT_DEV_ENVIRONMENTS = {"dev", "local"}

    def __init__(self, path: str = "app/data/users.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._seed_defaults_enabled = self._resolve_seed_defaults_enabled()
        if not self._path.exists():
            if self._seed_defaults_enabled:
                self._seed_defaults()
            else:
                self._save([])

    @property
    def session_ttl_seconds(self) -> int:
        return self._SESSION_TTL_SECONDS

    @property
    def seed_defaults_enabled(self) -> bool:
        return self._seed_defaults_enabled

    @staticmethod
    def _is_truthy(value: str) -> bool:
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    def _resolve_seed_defaults_enabled(self) -> bool:
        explicit = os.getenv("SEED_DEFAULT_USERS")
        if explicit is not None and explicit.strip() != "":
            return self._is_truthy(explicit)
        app_env = os.getenv("APP_ENV", "dev").strip().lower()
        return app_env in self._DEFAULT_DEV_ENVIRONMENTS

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

    def _revoke_sessions_for_username(self, username: str) -> None:
        normalized = (username or "").strip().lower()
        tokens = [
            token
            for token, payload in self._sessions.items()
            if str(payload.get("username", "")).strip().lower() == normalized
        ]
        for token in tokens:
            self._sessions.pop(token, None)

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
            {
                "username": u.get("username"),
                "role": u.get("role"),
                "active": bool(u.get("active", True)),
                "created_at": u.get("created_at"),
                "updated_at": u.get("updated_at"),
                "last_login_at": u.get("last_login_at"),
            }
            for u in self._load()
        ]

    def has_users(self) -> bool:
        return bool(self._load())

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        normalized = (username or "").strip().lower()
        for user in self._load():
            if str(user.get("username", "")).strip().lower() == normalized:
                return {
                    "username": user.get("username"),
                    "role": user.get("role"),
                    "active": bool(user.get("active", True)),
                    "created_at": user.get("created_at"),
                    "updated_at": user.get("updated_at"),
                    "last_login_at": user.get("last_login_at"),
                }
        return None

    def admin_count(self, active_only: bool = True) -> int:
        total = 0
        for user in self._load():
            if str(user.get("role", "")).strip().lower() != "admin":
                continue
            if active_only and not bool(user.get("active", True)):
                continue
            total += 1
        return total

    def create_user(self, username: str, password: str, role: str) -> Dict[str, Any]:
        rows = self._load()
        if any((u.get("username") or "").lower() == username.lower() for u in rows):
            raise ValueError("Username already exists")
        now = datetime.utcnow().isoformat() + "Z"
        user = {
            "username": username,
            "password_hash": self._hash_password(password),
            "role": role,
            "active": True,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
        }
        rows.append(user)
        self._save(rows)
        return {
            "username": username,
            "role": role,
            "active": True,
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
            "last_login_at": user["last_login_at"],
        }

    def update_user(
        self,
        username: str,
        role: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        rows = self._load()
        normalized = (username or "").strip().lower()
        target: Optional[Dict[str, Any]] = None
        now = datetime.utcnow().isoformat() + "Z"
        role_changed = False
        for user in rows:
            if str(user.get("username", "")).strip().lower() != normalized:
                continue
            old_role = str(user.get("role", "")).strip().lower()
            if role is not None:
                user["role"] = role
                role_changed = old_role != str(role).strip().lower()
            if active is not None:
                user["active"] = bool(active)
            user["updated_at"] = now
            target = user
            break
        if not target:
            raise ValueError("User not found")
        self._save(rows)
        if active is False or role_changed:
            self._revoke_sessions_for_username(str(target.get("username", "")))
        return {
            "username": target.get("username"),
            "role": target.get("role"),
            "active": bool(target.get("active", True)),
            "created_at": target.get("created_at"),
            "updated_at": target.get("updated_at"),
            "last_login_at": target.get("last_login_at"),
        }

    def reset_password(self, username: str, new_password: str) -> Dict[str, Any]:
        rows = self._load()
        normalized = (username or "").strip().lower()
        target: Optional[Dict[str, Any]] = None
        now = datetime.utcnow().isoformat() + "Z"
        for user in rows:
            if str(user.get("username", "")).strip().lower() != normalized:
                continue
            user["password_hash"] = self._hash_password(new_password)
            user["updated_at"] = now
            target = user
            break
        if not target:
            raise ValueError("User not found")
        self._save(rows)
        self._revoke_sessions_for_username(str(target.get("username", "")))
        return {
            "username": target.get("username"),
            "role": target.get("role"),
            "active": bool(target.get("active", True)),
            "created_at": target.get("created_at"),
            "updated_at": target.get("updated_at"),
            "last_login_at": target.get("last_login_at"),
        }

    def delete_user(self, username: str) -> bool:
        rows = self._load()
        normalized = (username or "").strip().lower()
        filtered = [u for u in rows if str(u.get("username", "")).strip().lower() != normalized]
        if len(filtered) == len(rows):
            return False
        self._save(filtered)
        self._revoke_sessions_for_username(username)
        return True

    def authenticate(self, username: str, password: str) -> Optional[str]:
        self._prune_expired_sessions()
        for user in self._load():
            if user.get("username") != username:
                continue
            if not bool(user.get("active", True)):
                return None
            stored_hash = str(user.get("password_hash") or "")
            if not self._verify_password(stored_hash, password):
                continue
            if self._is_legacy_hash(stored_hash):
                self._upgrade_user_hash(username, password)
            now = datetime.utcnow().isoformat() + "Z"
            user["last_login_at"] = now
            user["updated_at"] = now
            rows = self._load()
            for row in rows:
                if row.get("username") == username:
                    row["last_login_at"] = now
                    row["updated_at"] = now
                    if "active" not in row:
                        row["active"] = True
                    break
            self._save(rows)
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
        payload = self._sessions.get(token)
        if not payload:
            return None
        username = str(payload.get("username", ""))
        current_user = self.get_user(username)
        if not current_user or not bool(current_user.get("active", True)):
            self._sessions.pop(token, None)
            return None
        return payload

    def logout(self, token: str | None) -> None:
        if token and token in self._sessions:
            del self._sessions[token]

