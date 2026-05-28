"""Resume builder AI configuration."""

from pathlib import Path

from decouple import config

GROQ_API_KEY: str = config("GROQ_API_KEY", default="")
GROQ_MODEL: str = config("GROQ_MODEL", default="openai/gpt-oss-120b")

TEMPLATES_DIR: Path = Path(__file__).resolve().parent.parent / "templates"
