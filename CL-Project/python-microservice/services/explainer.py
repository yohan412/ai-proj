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
    
    # ★ 타겟 언어에 따라 프롬프트 언어 선택
    if lang_name == "Korean":
        # 한글 프롬프트
        explanation_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

당신은 교육 컨텐츠 분석 전문가입니다. 주어진 내용을 분석하고 명확한 설명을 한글로 제공하세요.

중요 규칙:
- 핵심 개념을 요약하고 설명하세요
- 자연스러운 한글을 사용하세요
- 교육적 인사이트를 포함한 3-5문장으로 작성하세요
- 영어 단어를 절대 사용하지 마세요
- 전문 용어도 한글로 풀어 쓰세요

<|eot_id|><|start_header_id|>user<|end_header_id|>

다음 내용을 분석하고 주요 아이디어를 한글로 설명하세요:

{transcript_text[:1500]}

<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    else:
        # 영어 프롬프트
        explanation_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an educational content analyzer. Provide explanation in {lang_name}.

CRITICAL RULES:
- Write ONLY in {lang_name}
- Summarize and explain key concepts
- Provide 3-5 sentences with educational insights
- Rephrase ideas in your own words

<|eot_id|><|start_header_id|>user<|end_header_id|>

Analyze and explain in {lang_name}:

{transcript_text[:1500]}

<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    
    # LLM으로 설명 생성 (최적 파라미터: temperature=0.27)
    outputs = pipe(
        explanation_prompt,
        max_new_tokens=400,
        temperature=0.25
    )
    explanation = _extract_text(outputs).strip()
    
    print(f"[LLM 생성 완료]")
    print(f"  - 설명 ({lang_name}, {len(explanation)}자): {explanation[:100]}...")
    
    return explanation

