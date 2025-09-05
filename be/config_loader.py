import os
from typing import Any, Dict, List

def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError("PyYAML is required. Add 'pyyaml' to backend/requirements.txt") from e
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_config_to_env() -> Dict[str, Any]:
    """Loads config from YAML and sets env vars used by the app.

    Priority: CONFIG_PATH env var -> backend/config.yaml -> ./config.yaml
    Sets:
      - GOOGLE_API_KEY
      - PANDAS_AGI_API_KEY
      - GMAIL_USER1/GMAIL_PASS1, GMAIL_USER2/GMAIL_PASS2
      - CORS_ORIGINS (comma-separated) if provided
    Returns the parsed config dict for optional direct use.
    """
    cfg_path = os.environ.get("CONFIG_PATH")
    if not cfg_path:
        # default search
        p1 = os.path.join(os.path.dirname(__file__), "config.yaml")
        p2 = os.path.join(os.getcwd(), "config.yaml")
        cfg_path = p1 if os.path.exists(p1) else p2

    cfg = _load_yaml(cfg_path) if cfg_path else {}

    # Gemini
    gemini_key = (
        cfg.get("gemini", {}).get("api_key")
        if isinstance(cfg.get("gemini"), dict)
        else None
    )
    if gemini_key:
        os.environ["GOOGLE_API_KEY"] = str(gemini_key)

    # PandaAGI
    pandaagi_key = (
        cfg.get("pandas-agi", {}).get("api_key")
        if isinstance(cfg.get("pandas-agi"), dict)
        else None
    )
    if pandaagi_key:
        os.environ["PANDAS_AGI_API_KEY"] = str(pandaagi_key)

    # Gmail users
    gmail = cfg.get("gmail", {}) if isinstance(cfg.get("gmail"), dict) else {}
    users: List[Dict[str, Any]] = gmail.get("users", []) if isinstance(gmail.get("users"), list) else []
    for idx, u in enumerate(users[:2], start=1):
        email_val = u.get("email")
        pass_val = u.get("app_password") or u.get("password")
        if email_val:
            os.environ[f"GMAIL_USER{idx}"] = str(email_val)
        if pass_val:
            os.environ[f"GMAIL_PASS{idx}"] = str(pass_val)

    # CORS
    server = cfg.get("server", {}) if isinstance(cfg.get("server"), dict) else {}
    cors = server.get("cors_origins")
    if isinstance(cors, list) and cors:
        os.environ["CORS_ORIGINS"] = ",".join(str(x) for x in cors)

    return cfg

