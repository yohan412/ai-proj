import json
import math
from typing import Optional

def round_time(x: float) -> float:
    return round(float(x), 3)

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def ensure_json(text: str) -> Optional[dict]:
    """LLM 응답에서 JSON 객체 추출(코드블록 방지 등 최소 방어)"""
    t = (text or "").strip()
    try:
        return json.loads(t)
    except Exception:
        pass

    # 코드블록/잡다한 텍스트에서 첫 JSON 객체를 추출
    import re
    m = re.search(r"\{[\s\S]*\}", t)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None
