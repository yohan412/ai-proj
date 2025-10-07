import os
from dataclasses import dataclass

@dataclass
class Settings:
    # Whisper
    WHISPER_MODEL: str
    WHISPER_FP16: bool

    # LLM provider: "hf_local" | "remote"
    LLM_PROVIDER: str

    # Remote(OpenAI-compatible) 옵션(선택)
    LLM_BASE_URL: str
    LLM_MODEL: str
    LLM_API_KEY: str

    # HF 로컬 (openai/gpt-oss-20b)
    HF_MODEL_ID: str
    HF_LOAD_IN_4BIT: bool
    HF_MAX_NEW_TOKENS: int
    HF_TEMPERATURE: float
    HF_TOKEN: str  # 프라이빗/레이트리밋 우회 시

    # 메모리/오프로딩 설정
    HF_MAX_GPU_MEMORY: str   # 예: "12GiB"
    HF_MAX_CPU_MEMORY: str   # 예: "64GiB"
    HF_OFFLOAD_DIR: str      # 예: "./offload"
    HF_LOW_CPU_MEM: bool     # True 권장
    HF_TORCH_DTYPE: str      # "auto"|"float16"|"bfloat16"|"float32"

    # 프롬프트 압축
    MAX_SEGMENTS_FOR_PROMPT: int

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            WHISPER_MODEL=os.getenv("WHISPER_MODEL", "small"),
            WHISPER_FP16=os.getenv("WHISPER_FP16", "false").lower() in ("1","true","yes"),

                    LLM_PROVIDER=os.getenv("LLM_PROVIDER", "hf_local"),

            LLM_BASE_URL=os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1"),
            LLM_MODEL=os.getenv("LLM_MODEL", "gpt-oss-20b"),
            LLM_API_KEY=os.getenv("LLM_API_KEY", ""),

                    HF_MODEL_ID=os.getenv("HF_MODEL_ID", "meta-llama/Llama-3.2-3B-Instruct"),
            HF_LOAD_IN_4BIT=os.getenv("HF_LOAD_IN_4BIT", "true").lower() in ("1","true","yes"), # HF_LOAD_IN_4BIT false -> cpu
            HF_MAX_NEW_TOKENS=int(os.getenv("HF_MAX_NEW_TOKENS", "2048")),
            HF_TEMPERATURE=float(os.getenv("HF_TEMPERATURE", "0.2")),
                    HF_TOKEN=os.getenv("HF_TOKEN", "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"),

            HF_MAX_GPU_MEMORY=os.getenv("HF_MAX_GPU_MEMORY", "16GiB"),  # GPU 메모리 증가
            HF_MAX_CPU_MEMORY=os.getenv("HF_MAX_CPU_MEMORY", "32GiB"),  # CPU 메모리 감소
            HF_OFFLOAD_DIR=os.getenv("HF_OFFLOAD_DIR", "./offload"),
            HF_LOW_CPU_MEM=os.getenv("HF_LOW_CPU_MEM", "false").lower() in ("1","true","yes"),  # GPU 사용 시 false
            HF_TORCH_DTYPE=os.getenv("HF_TORCH_DTYPE", "bfloat16"),  # GPU 최적화 dtype

            MAX_SEGMENTS_FOR_PROMPT=int(os.getenv("MAX_SEGMENTS_FOR_PROMPT", "1200")),
        )
