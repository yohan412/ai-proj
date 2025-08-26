# utils/helpers.py
import json
import re   # ★ NEW
from typing import Optional

def round_time(x: float) -> float:
    return round(float(x), 3)

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def ensure_json(text: str) -> Optional[dict]:
    """LLM 응답에서 JSON 객체 추출(코드블록/주석 섞임 방어)"""
    t = (text or "").strip()

    # ★ NEW: 코드펜스 제거(예: ```json ... ```)
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*|\s*```$", "", t, flags=re.MULTILINE).strip()

    # 1차: 전체 파싱 시도
    try:
        return json.loads(t)
    except Exception:
        pass

    # 2차: 텍스트 중 첫 JSON 객체 추출
    m = re.search(r"\{[\s\S]*\}", t)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None
