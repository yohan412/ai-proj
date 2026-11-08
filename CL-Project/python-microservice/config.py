import os
from dataclasses import dataclass


def _as_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


@dataclass
class Settings:
    # Whisper
    WHISPER_MODEL: str
    WHISPER_FP16: bool

    # LLM provider: "ollama"
    LLM_PROVIDER: str

    # Ollama (gemma4:e4b)
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    OLLAMA_NUM_CTX: int
    OLLAMA_KEEP_ALIVE: str
    OLLAMA_TIMEOUT: int
    OLLAMA_THINK: bool
    OLLAMA_TEMPERATURE: float
    OLLAMA_EXPLAIN_TEMPERATURE: float

    # 프롬프트 압축 / overlap 청킹
    MAX_SEGMENTS_FOR_PROMPT: int
    CHUNK_SIZE_SEGMENTS: int
    CHUNK_OVERLAP_SEGMENTS: int
    CHUNK_MERGE_GAP_SEC: float

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            WHISPER_MODEL=os.getenv("WHISPER_MODEL", "small"),
            WHISPER_FP16=_as_bool("WHISPER_FP16", "false"),

            LLM_PROVIDER=os.getenv("LLM_PROVIDER", "ollama"),

            OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            OLLAMA_MODEL=os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
            OLLAMA_NUM_CTX=int(os.getenv("OLLAMA_NUM_CTX", "16384")),
            OLLAMA_KEEP_ALIVE=os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
            OLLAMA_TIMEOUT=int(os.getenv("OLLAMA_TIMEOUT", "300")),
            OLLAMA_THINK=_as_bool("OLLAMA_THINK", "false"),
            OLLAMA_TEMPERATURE=float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
            OLLAMA_EXPLAIN_TEMPERATURE=float(os.getenv("OLLAMA_EXPLAIN_TEMPERATURE", "0.3")),

            MAX_SEGMENTS_FOR_PROMPT=int(os.getenv("MAX_SEGMENTS_FOR_PROMPT", "1200")),
            CHUNK_SIZE_SEGMENTS=int(os.getenv("CHUNK_SIZE_SEGMENTS", "300")),
            CHUNK_OVERLAP_SEGMENTS=int(os.getenv("CHUNK_OVERLAP_SEGMENTS", "50")),
            CHUNK_MERGE_GAP_SEC=float(os.getenv("CHUNK_MERGE_GAP_SEC", "30")),
        )
