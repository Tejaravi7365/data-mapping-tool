import json
from pathlib import Path
from typing import Any, Dict


class SsoSettingsStore:
    """
    JSON-backed SSO settings store (admin-managed).
    """

    def __init__(self, path: str = "app/data/sso_settings.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._save(
                {
                    "enabled": False,
                    "provider": "okta",
                    "issuer_url": "",
                    "client_id": "",
                    "client_secret": "",
                    "redirect_uri": "",
                    "scopes": "openid profile email",
                }
            )

    def _load(self) -> Dict[str, Any]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
            return {}
        except Exception:
            return {}

    def _save(self, payload: Dict[str, Any]) -> None:
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get(self) -> Dict[str, Any]:
        return self._load()

    def update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self._load()
        merged = dict(current)
        merged.update(payload or {})
        self._save(merged)
        return merged

    @staticmethod
    def sanitize(payload: Dict[str, Any]) -> Dict[str, Any]:
        redacted = dict(payload or {})
        if redacted.get("client_secret"):
            redacted["client_secret"] = "***"
        return redacted
