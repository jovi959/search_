import os
from datetime import date
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent
_FALSE_ENV_VALUES = {"", "0", "false", "no", "off", "disabled"}
_ENGLISH_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def load(name: str, **kwargs) -> str:
    template = (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    values = {"current_date": year_month_context(), **kwargs}
    for key, value in values.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template


def year_month_context() -> str:
    """English 'Month YYYY' (no hyphens — avoids Google `-` query semantics). No day or clock time."""
    if not env_flag("INJECT_DATE_CONTEXT", default=True):
        return ""
    d = date.today()
    return f"{_ENGLISH_MONTHS[d.month - 1]} {d.year}"


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSE_ENV_VALUES
