# -*- coding: utf-8 -*-
"""
Gemini 1.5 Flash (google‑generative‑ai) 로 각 구간의 text 를 자연스럽게 다듬는다.
---------------------------------------------------------------------
pip install --upgrade google-generativeai
---------------------------------------------------------------------
환경 변수 GOOGLE_API_KEY 에 **키**가 있으면 자동 사용.
(개별 키를 함수에 넘겨도 됨)
"""

from __future__ import annotations
from typing import List, Dict, Optional
import google.generativeai as genai
import os
import time

# ------------------------------------------------------------------ #
# ①  Gemini 초기화
# ------------------------------------------------------------------ #

from .model_loader import get_gemini_model
from config import rephrase_system_prompt, rephrase_user_prompt_template

# ------------------------------------------------------------------ #
# ②  한 구간(text)을 정제하는 헬퍼
# ------------------------------------------------------------------ #
_SYSTEM_PROMPT_CLEAN = """You are a helpful Korean/English proof‑reader.
입력은 OCR로부터 추출된 매우 난해한 문장일 수 있기 때문에 단어의 철자가 잘못되어있거나 맞춤법이 틀려있을수 있습니다.
가능한 한 **자연스러운** 한국어(또는 영어) 문장/단어로 정제해 주세요.
의미를 잃지 않는 범위에서 띄어쓰기를 교정하고, 불필요한 반복·노이즈를 제거합니다.
불필요하게 반복되는 띄어쓰기도 한번으로 줄입니다.
대답은 **수정된 한 줄**만 반환하세요."""

def _clean_text(model: genai.GenerativeModel, raw: str,
                *, max_retry: int = 3, delay: float = 1.2) -> str:
    """Gemini API 3‑회 재시도 래퍼"""
    for attempt in range(1, max_retry + 1):
        try:
            # The model is already configured with a system prompt, so we only send the user content.
            rsp = model.generate_content(raw.strip(), safety_settings={"harassment": "block_none"})
            cleaned = rsp.text.strip()
            return cleaned or raw      # 빈 응답이면 원본 보존
        except Exception as e:
            print(f"API call failed during cleaning on attempt {attempt}. Error: {e}")
            if attempt == max_retry:
                return raw             # 포기하고 원본 반환
            time.sleep(delay)          # 백오프 후 재시도


# ------------------------------------------------------------------ #
# ③  (start, end, text) 리스트 → 정제된 동일 포맷 반환
# ------------------------------------------------------------------ #
def refine_segments(
    segments: List[Dict[str, str | float | None]],
    api_key: Optional[str] = None
) -> List[Dict[str, str | float | None]]:
    """
    입력: [{'start': 0.0, 'end': 2.3, 'text': ' ... '}, …]

    출력: 같은 리스트이되 text 가 Gemini 로 다듬어진 형태.
    순서는 그대로 유지.
    """
    model = get_gemini_model(_SYSTEM_PROMPT_CLEAN)
    if model is None:
        print("Warning: Could not create a Gemini model for cleaning. Returning original segments.")
        return segments

    cleaned: List[Dict[str, str | float | None]] = []
    for seg in segments:
        new_text = _clean_text(model, str(seg["text"]))
        cleaned.append({**seg, "text": new_text})

    return cleaned

# ------------------------------------------------------------------ #
# ④  (start, end, text) 리스트 → 문단으로 재구성된 동일 포맷 반환
# ------------------------------------------------------------------ #

def _rephrase_text(model: genai.GenerativeModel, raw: str,
                   *, max_retry: int = 3, delay: float = 1.2) -> str:
    """Gemini API 3‑회 재시도 래퍼 (문단 재구성용)"""
    user_prompt = rephrase_user_prompt_template.format(text_chunk=raw.strip())
    for attempt in range(1, max_retry + 1):
        try:
            # The model is already configured with a system prompt, so we only send the user content.
            rsp = model.generate_content(user_prompt, safety_settings={"harassment": "block_none"})
            rephrased = rsp.text.strip()
            return rephrased or raw      # 빈 응답이면 원본 보존
        except Exception as e:
            print(f"API call failed during rephrasing on attempt {attempt}. Error: {e}")
            if attempt == max_retry:
                return raw             # 포기하고 원본 반환
            time.sleep(delay)          # 백오프 후 재시도

def rephrase_segments_as_paragraphs(
    segments: List[Dict[str, str | float | None]],
    api_key: Optional[str] = None
) -> List[Dict[str, str | float | None]]:
    """
    입력: [{'start': 0.0, 'end': 2.3, 'text': ' ... '}, …]

    출력: 같은 리스트이되 text 가 Gemini 로 재구성된 문단인 형태.
    순서는 그대로 유지.
    """
    model = get_gemini_model(rephrase_system_prompt)
    if model is None:
        print("Warning: Could not create a Gemini model for rephrasing. Returning original segments.")
        return segments

    rephrased_list: List[Dict[str, str | float | None]] = []
    for seg in segments:
        new_text = _rephrase_text(model, str(seg["text"]))
        rephrased_list.append({**seg, "text": new_text})

    return rephrased_list
