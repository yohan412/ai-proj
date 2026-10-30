# services/explainer.py
from typing import List, Dict, Any

from services.chapterizer import _lang_label_from_code
from services.ollama_client import OllamaError, chat
from utils.helpers import remove_duplicate_sentences, trim_incomplete_last_sentence


def generate_explanation(
    *,
    segments: List[Dict[str, Any]],
    start_time: float,
    end_time: float,
    lang: str,
    temperature: float = 0.3,
) -> str:
    """챕터 구간에 대한 상세 설명을 Ollama로 생성한다."""
    chapter_segments = []
    for seg in segments:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        if seg_start < end_time and seg_end > start_time:
            chapter_segments.append(seg)

    print(f"  - 필터링된 세그먼트 수: {len(chapter_segments)}")

    if not chapter_segments:
        return "이 구간에 대한 자막이 없습니다."

    transcript_text = " ".join(seg.get("text", "").strip() for seg in chapter_segments)
    print(f"  - 자막 텍스트 길이: {len(transcript_text)}자")
    print(f"  - 자막 텍스트 미리보기: {transcript_text[:100]}...")

    lang_name = _lang_label_from_code(lang)
    print(f"  - 타겟 언어: {lang_name}")
    excerpt = transcript_text[:1500]

    if lang_name == "Korean":
        system = """당신은 교육 컨텐츠 분석 전문가입니다. 주어진 내용을 분석하고 명확한 설명을 한글로 제공하세요.

중요 규칙:
- 핵심 개념을 요약하고 설명하세요
- 자연스러운 한글을 사용하세요
- 교육적 인사이트를 포함한 3-5문장으로 작성하세요
- 영어 단어를 절대 사용하지 마세요
- 전문 용어도 한글로 풀어 쓰세요"""
        user = f"다음 내용을 분석하고 주요 아이디어를 한글로 설명하세요:\n\n{excerpt}"
    else:
        system = f"""You are an educational content analyzer. Provide explanation in {lang_name}.

CRITICAL RULES:
- Write ONLY in {lang_name}
- Summarize and explain key concepts
- Provide 3-5 sentences with educational insights
- Rephrase ideas in your own words"""
        user = f"Analyze and explain in {lang_name}:\n\n{excerpt}"

    try:
        explanation = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            num_predict=400,
            json_mode=False,
        )
    except OllamaError as e:
        return f"설명을 생성하지 못했습니다. Ollama 서버를 확인해 주세요. ({e})"

    explanation = remove_duplicate_sentences(explanation)
    explanation = trim_incomplete_last_sentence(explanation)

    print("[LLM 생성 완료]")
    print(f"  - 설명 ({lang_name}, {len(explanation)}자): {explanation[:100]}...")
    return explanation
