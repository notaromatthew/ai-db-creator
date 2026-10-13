"""Impostazioni a runtime (tabella app_settings) con valori predefiniti da config."""
from app.config import settings
from app.models.database import AppSetting, get_session, init_db

# chiave -> (valore predefinito, tipo)
DEFAULTS = {
    "default_daily_ai_quota": lambda: settings.default_daily_ai_quota,
    "daily_ai_budget_total": lambda: settings.daily_ai_budget_total,
    "max_upload_mb": lambda: settings.max_upload_mb,
    "max_projects_per_user": lambda: settings.max_projects_per_user,
    "registration_open": lambda: True,
    "maintenance_message": lambda: "",
}
INT_KEYS = {"default_daily_ai_quota", "daily_ai_budget_total", "max_upload_mb", "max_projects_per_user"}


def get_setting(key: str):
    session = get_session(init_db())
    try:
        row = session.get(AppSetting, key)
        if row is not None and row.value is not None:
            return row.value
    finally:
        session.close()
    return DEFAULTS[key]()


def all_settings() -> dict:
    return {k: get_setting(k) for k in DEFAULTS}


def set_setting(key: str, value, actor: str):
    if key not in DEFAULTS:
        raise KeyError(key)
    if key in INT_KEYS:
        value = int(value)
        if value < 0:
            raise ValueError("valore negativo")
    elif key == "registration_open":
        value = bool(value)
    else:
        value = str(value)[:300]
    session = get_session(init_db())
    try:
        row = session.get(AppSetting, key)
        if row is None:
            session.add(AppSetting(key=key, value=value, updated_by=actor))
        else:
            row.value, row.updated_by = value, actor
        session.commit()
    finally:
        session.close()
    return value
