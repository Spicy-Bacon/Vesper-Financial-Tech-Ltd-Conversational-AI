"""Server-only settings; environment variables override the ignored root .env."""
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    OMLX_API_KEY: SecretStr | None = None
    OMLX_BASE_URL: str = "http://127.0.0.1:8000/v1"
    OMLX_MODEL: str = Field(default="", max_length=256)
    VESPER_MODEL_BACKEND: Literal["unconfigured", "omlx"] = "unconfigured"
    VESPER_DEMO: bool = False
    VESPER_DEMO_CATALOG: bool = False
    VESPER_SERVE_FRONTEND: bool = True

    @field_validator("OMLX_BASE_URL")
    @classmethod
    def valid_base_url(cls, value):
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("Use an HTTP(S) base URL without credentials, query or fragment.")
        if parsed.path.rstrip("/") != "/v1":
            raise ValueError("The oMLX base URL must end in /v1.")
        return value.rstrip("/")

    @classmethod
    def load(cls, env_file: Path | None = None, environ: dict | None = None):
        env_file = env_file or Path(__file__).resolve().parents[2] / ".env"
        values = dict(dotenv_values(env_file, interpolate=False)) if env_file.is_file() else {}
        environment = os.environ if environ is None else environ
        values.update({key: value for key, value in environment.items() if key in cls.model_fields})
        return cls.model_validate(values)
