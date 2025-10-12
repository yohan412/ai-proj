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

def remove_duplicate_sentences(text: str) -> str:
    """반복되는 문장 제거"""
    if not text:
        return text
    
    # 마침표 기준으로 문장 분리
    sentences = text.split('.')
    
    # 중복 제거 (순서 유지)
    seen = []
    unique = []
    
    for sent in sentences:
        cleaned = sent.strip()
        if not cleaned:
            continue
        
        # 정규화 (공백, 쉼표 제거)
        normalized = cleaned.replace(' ', '').replace(',', '')
        
        # 이미 본 문장과 유사도 체크 (70% 이상 일치하면 중복)
        is_duplicate = False
        for seen_normalized in seen:
            if len(normalized) > 0 and len(seen_normalized) > 0:
                # 간단한 유사도: 짧은 문장이 긴 문장에 포함되는지
                shorter = min(normalized, seen_normalized, key=len)
                longer = max(normalized, seen_normalized, key=len)
                if shorter in longer:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            seen.append(normalized)
            unique.append(cleaned)
    
    return '. '.join(unique) + ('.' if unique else '')

def trim_incomplete_last_sentence(text: str) -> str:
    """마지막 마침표(.)나 느낌표(!)로 끝나지 않은 문장 제거"""
    if not text:
        return text
    
    # 유효한 문장 종결 부호: . 또는 !만 허용 (? 제외)
    last_period = text.rfind('.')
    last_exclamation = text.rfind('!')
    
    # 가장 마지막 유효한 문장 종결 부호의 위치
    last_sentence_end = max(last_period, last_exclamation)
    
    # 유효한 문장 종결 부호가 없으면 빈 문자열 반환
    if last_sentence_end == -1:
        return ""
    
    # 마지막 유효한 문장 종결 부호 뒤의 텍스트 확인
    after_last = text[last_sentence_end + 1:].strip()
    
    # 뒤에 텍스트가 있으면 (미완성 문장) 잘라냄
    if after_last:
        return text[:last_sentence_end + 1].strip()
    
    return text