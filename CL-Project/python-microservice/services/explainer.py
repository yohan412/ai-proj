# services/explainer.py
from typing import List, Dict, Any, Optional
from services.chapterizer import _lang_label_from_code  # ★ chapterizer에서 import

def generate_explanation(
    *,
    segments: List[Dict[str, Any]],
    start_time: float,
    end_time: float,
    lang: str,
    pipe,  # LLM pipeline
    _extract_text  # text extraction function
) -> str:
    """
    챕터 구간에 대한 상세 설명 생성
    
    Args:
        segments: 전체 자막 세그먼트 리스트
        start_time: 챕터 시작 시간
        end_time: 챕터 종료 시간
        lang: 언어 코드
        pipe: LLM 파이프라인
        _extract_text: LLM 출력 텍스트 추출 함수
    
    Returns:
        생성된 설명 텍스트
    """
    # 해당 구간의 세그먼트만 필터링
    chapter_segments = []
    for seg in segments:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        if seg_start < end_time and seg_end > start_time:
            chapter_segments.append(seg)
    
    print(f"  - 필터링된 세그먼트 수: {len(chapter_segments)}")
    
    if not chapter_segments:
        return "이 구간에 대한 자막이 없습니다."
    
    # 세그먼트 텍스트 결합
    transcript_text = " ".join([seg.get("text", "").strip() for seg in chapter_segments])
    print(f"  - 자막 텍스트 길이: {len(transcript_text)}자")
    print(f"  - 자막 텍스트 미리보기: {transcript_text[:100]}...")
    
    # 언어 라벨
    lang_name = _lang_label_from_code(lang)
    print(f"  - 타겟 언어: {lang_name}")
    
    # 프롬프트 생성
    explanation_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an educational content analyzer. Analyze the given content and provide a clear explanation in {lang_name}.

IMPORTANT:
- SUMMARIZE and EXPLAIN the key concepts (do NOT copy the original text)
- Use natural {lang_name} language
- Provide 3-5 sentences with educational insights
- Rephrase the ideas in your own words

<|eot_id|><|start_header_id|>user<|end_header_id|>

Analyze this content and explain the main ideas in {lang_name}:

{transcript_text[:1500]}

<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    
    # LLM으로 설명 생성
    outputs = pipe(explanation_prompt)
    explanation = _extract_text(outputs).strip()
    
    print(f"[LLM 생성 완료]")
    print(f"  - 설명 ({lang_name}, {len(explanation)}자): {explanation[:100]}...")
    
    return explanation

