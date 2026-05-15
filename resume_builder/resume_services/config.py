"""
Resume builder configuration.
Reads from environment variables via python-decouple (same as rest of project).

Supports two AI providers:
- OpenAI (primary)   — set OPENAI_API_KEY
- Groq   (fallback)  — set GROQ_API_KEY
"""
from pathlib import Path
from decouple import config

OPENAI_API_KEY: str = config("OPENAI_API_KEY", default="")
OPENAI_MODEL: str   = config("OPENAI_MODEL",   default="gpt-4o-mini")

GROQ_API_KEY: str   = config("GROQ_API_KEY",   default="")
GROQ_MODEL: str     = config("GROQ_MODEL",     default="llama-3.3-70b-versatile")

TEMPLATES_DIR: Path = Path(__file__).resolve().parent.parent / "templates"
