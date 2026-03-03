from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load(name: str, **kwargs) -> str:
    template = (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template
