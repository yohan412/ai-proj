"""Ollama /api/chat 클라이언트. 채팅 템플릿은 서버가 붙인다."""
import re
from typing import Any, Dict, List

import requests

from config import Settings


class OllamaError(RuntimeError):
    """Ollama 연결 실패, 타임아웃, HTTP 오류."""


_FINAL_MARKERS = (
    "<|channel|>final<|message|>",
    "<|channel|>final<|message>",
)


def _settings() -> Settings:
    return Settings.from_env()


def _final_text(content: str) -> str:
    """채널 표식이 남아 있으면 final 본문만 남긴다."""
    text = content or ""
    for marker in _FINAL_MARKERS:
        if marker in text:
            text = text.split(marker)[-1]
    text = re.sub(r"<\|[^|>]+?\|>", "", text)
    return text.strip()


def chat(
    messages: List[Dict[str, str]],
    *,
    temperature: float,
    num_predict: int,
    json_mode: bool = False,
) -> str:
    """system/user 메시지를 보내고 최종 텍스트를 반환한다."""
    cfg = _settings()
    url = f"{cfg.OLLAMA_BASE_URL}/api/chat"
    payload: Dict[str, Any] = {
        "model": cfg.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "think": cfg.OLLAMA_THINK,
        "keep_alive": cfg.OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": cfg.OLLAMA_NUM_CTX,
        },
    }
    if json_mode:
        payload["format"] = "json"

    try:
        resp = requests.post(url, json=payload, timeout=cfg.OLLAMA_TIMEOUT)
        resp.raise_for_status()
    except requests.Timeout as e:
        msg = f"Ollama 응답 시간 초과 ({cfg.OLLAMA_TIMEOUT}초): {url}"
        print(f"[ollama] {msg}", flush=True)
        raise OllamaError(msg) from e
    except requests.ConnectionError as e:
        msg = f"Ollama 서버에 연결할 수 없습니다: {url} ({e})"
        print(f"[ollama] {msg}", flush=True)
        raise OllamaError(msg) from e
    except requests.HTTPError as e:
        body = ""
        if e.response is not None:
            body = (e.response.text or "")[:500]
        msg = f"Ollama 요청 실패: {e} {body}".strip()
        print(f"[ollama] {msg}", flush=True)
        raise OllamaError(msg) from e

    data = resp.json()
    message = data.get("message") or {}
    return _final_text(str(message.get("content") or ""))


def ollama_status() -> Dict[str, Any]:
    """GET /api/tags 로 서버 도달과 모델 존재 여부를 확인한다."""
    cfg = _settings()
    url = f"{cfg.OLLAMA_BASE_URL}/api/tags"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        names = [
            str(m.get("name"))
            for m in (resp.json().get("models") or [])
            if isinstance(m, dict) and m.get("name")
        ]
        wanted = cfg.OLLAMA_MODEL
        present = any(name == wanted or name.startswith(wanted + ":") or name.startswith(wanted) for name in names)
        return {
            "reachable": True,
            "model_present": present,
            "models": names,
        }
    except Exception as e:
        print(f"[ollama] 상태 확인 실패: {url} ({e})", flush=True)
        return {
            "reachable": False,
            "model_present": False,
            "models": [],
            "error": str(e),
        }
