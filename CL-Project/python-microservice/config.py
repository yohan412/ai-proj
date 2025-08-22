import os
from dataclasses import dataclass

@dataclass
class Settings:
    WHISPER_MODEL: str
    WHISPER_FP16: bool
    LLM_BASE_URL: str
    LLM_MODEL: str
    LLM_API_KEY: str
    MAX_SEGMENTS_FOR_PROMPT: int

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            WHISPER_MODEL=os.getenv("WHISPER_MODEL", "small"),
            WHISPER_FP16=os.getenv("WHISPER_FP16", "false").lower() in ("1","true","yes"),
            LLM_BASE_URL=os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1"),
            LLM_MODEL=os.getenv("LLM_MODEL", "gpt-oss-20b"),
            LLM_API_KEY=os.getenv("LLM_API_KEY", ""),
            MAX_SEGMENTS_FOR_PROMPT=int(os.getenv("MAX_SEGMENTS_FOR_PROMPT", "1200")),
        )
