from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class LangfuseConfig:
    host: str
    public_key: str
    secret_key: str
    enabled: bool = True


@dataclass(slots=True)
class AgentConfig:
    gemini_api_key: str
    max_retries: int
    sandbox_timeout_s: int
    chroma_dir: str
    sqlite_path: str
    session_dir: str
    verbose: bool
    langfuse: LangfuseConfig

    @classmethod
    def from_env(cls, dotenv_path: str | None = None, no_trace: bool = False, verbose: bool = False) -> "AgentConfig":
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path, override=False)
        else:
            load_dotenv(override=False)

        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        max_retries = int(os.getenv("MAX_RETRIES", "5"))
        sandbox_timeout_s = int(os.getenv("SANDBOX_TIMEOUT_S", "30"))
        chroma_dir = os.getenv("CHROMA_DIR", "./chroma_db")
        sqlite_path = os.getenv("SQLITE_PATH", "./debugagent.db")
        session_dir = os.getenv("SESSION_DIR", "./sessions")

        langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

        langfuse_enabled = (not no_trace) and bool(langfuse_public_key and langfuse_secret_key)

        Path(chroma_dir).mkdir(parents=True, exist_ok=True)
        Path(session_dir).mkdir(parents=True, exist_ok=True)
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        return cls(
            gemini_api_key=gemini_api_key,
            max_retries=max_retries,
            sandbox_timeout_s=sandbox_timeout_s,
            chroma_dir=chroma_dir,
            sqlite_path=sqlite_path,
            session_dir=session_dir,
            verbose=verbose,
            langfuse=LangfuseConfig(
                host=langfuse_host,
                public_key=langfuse_public_key,
                secret_key=langfuse_secret_key,
                enabled=langfuse_enabled,
            ),
        )
