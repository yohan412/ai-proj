# services/chapterizer.py
from typing import List, Dict, Any, Optional, Tuple
import re
import json

from services.ollama_client import OllamaError, chat
from utils.helpers import remove_duplicate_sentences, trim_incomplete_last_sentence

_BOUNDARY_CHAR_BUDGET = 24000
_BATCH_CHAR_BUDGET = 16000
_DEFAULT_CHUNK_SIZE = 300
_DEFAULT_CHUNK_OVERLAP = 50
_DEFAULT_MERGE_GAP_SEC = 30.0


def _lang_label_from_code(code: Optional[str]) -> str:
    code = (code or "").lower()
    table = {
        "ko": "Korean", "en": "English", "ja": "Japanese",
        "zh": "Chinese", "zh-cn": "Chinese", "zh-tw": "Chinese (Traditional)",
        "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
        "pt": "Portuguese", "ru": "Russian", "vi": "Vietnamese",
        "id": "Indonesian", "th": "Thai", "hi": "Hindi", "ar": "Arabic",
    }
    return table.get(code, "the same language as the transcript")


def _segment_line(seg: Dict[str, Any]) -> str:
    return f"{seg.get('start', 0):.1f}s: {(seg.get('text') or '').strip()}"


def _format_segments_for_prompt(segments: List[Dict[str, Any]], char_budget: int) -> str:
    """한 윈도우의 자막을 문자 한도 안에서 프롬프트 텍스트로 만든다."""
    lines = []
    total = 0
    for seg in segments:
        line = _segment_line(seg)
        extra = len(line) + (1 if lines else 0)
        if total + extra > char_budget:
            break
        lines.append(line)
        total += extra
    return "\n".join(lines)


def _iter_overlap_windows(
    segments: List[Dict[str, Any]],
    chunk_size: int,
    overlap: int,
) -> List[List[Dict[str, Any]]]:
    """세그먼트를 overlap 있는 슬라이딩 윈도우로 나눈다."""
    if not segments:
        return []
    size = max(1, int(chunk_size))
    ov = max(0, min(int(overlap), size - 1))
    step = max(1, size - ov)
    windows: List[List[Dict[str, Any]]] = []
    start = 0
    n = len(segments)
    while start < n:
        windows.append(segments[start:start + size])
        if start + size >= n:
            break
        start += step
    return windows


def _window_time_span(window: List[Dict[str, Any]], duration: float) -> Tuple[float, float]:
    if not window:
        return 0.0, duration
    w_start = float(window[0].get("start", 0.0))
    w_end = float(window[-1].get("end", window[-1].get("start", w_start)))
    return max(0.0, w_start), min(duration, max(w_end, w_start))


def _cuts_from_boundaries(boundaries: List[Dict[str, float]]) -> List[float]:
    cuts: List[float] = []
    for b in boundaries or []:
        try:
            cuts.append(float(b.get("start", 0.0)))
            cuts.append(float(b.get("end", 0.0)))
        except (TypeError, ValueError):
            continue
    return cuts


def _boundaries_from_cuts(
    cuts: List[float],
    duration: float,
    merge_gap: float,
) -> List[Dict[str, float]]:
    """여러 윈도우에서 모은 절단점을 합쳐 연속 구간으로 만든다."""
    gap = max(1.0, float(merge_gap))
    pts = sorted({round(float(c), 1) for c in cuts if 0.0 < float(c) < duration})
    merged = [0.0]
    for c in pts:
        if c - merged[-1] >= gap:
            merged.append(c)
    if duration - merged[-1] < gap and len(merged) > 1:
        # 마지막 조각이 너무 짧으면 직전 절단을 영상 끝으로 흡수
        merged[-1] = duration
    elif merged[-1] != duration:
        merged.append(duration)

    return [
        {"start": merged[i], "end": merged[i + 1]}
        for i in range(len(merged) - 1)
        if merged[i + 1] > merged[i]
    ]


def _max_chapter_count(duration: float) -> int:
    """긴 영상일수록 챕터 상한을 늘린다."""
    if duration <= 0:
        return 8
    # 대략 2~3분당 1챕터, 최소 8 / 최대 20
    return max(8, min(20, int(duration / 120.0) + 1))


def _chapter_transcript(segments: List[Dict[str, Any]], start: float, end: float, limit: int) -> str:
    chapter_segments = [
        s for s in segments
        if s.get("start", 0) >= start and s.get("end", 0) <= end
    ]
    transcript = " ".join((s.get("text") or "").strip() for s in chapter_segments).strip()
    return transcript[:limit]


def _extract_json_object(text: str) -> str:
    raw = (text or "").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return raw
    return raw[start:end + 1]


def _equal_boundaries(duration: float, num_chapters: int = 6) -> List[Dict[str, float]]:
    if duration <= 0:
        return []
    chunk = duration / num_chapters
    return [{"start": i * chunk, "end": (i + 1) * chunk} for i in range(num_chapters)]


def _boundary_system_prompt(*, whole_video: bool, max_chapters: int) -> str:
    if whole_video:
        count_rule = (
            f"- TOTAL segment count MUST be between 4 and {max_chapters} (inclusive). "
            f"If you detect more, MERGE adjacent segments until the count ≤ {max_chapters} while keeping ≥60.0s."
        )
        goal = f"return 4–{max_chapters} MAJOR topic segments (not subtitle-sized fragments)"
    else:
        count_rule = (
            "- Return only MAJOR topic segments that fall inside this transcript window. "
            "Prefer 1–5 segments for this window. Do not invent content outside the window timestamps."
        )
        goal = "return MAJOR topic segments inside the given transcript window only"

    return f"""You are a video topic segmenter. Output ONLY valid JSON.
Your goal is to {goal}.

Hard constraints:
- Use ONLY timestamps that appear in the transcript; do NOT invent times.
- Segments must be contiguous, non-overlapping, strictly increasing (start < end).
- Each segment length ≥ 60.0s. Also enforce a MINIMUM GAP of 45.0s between any two boundaries.
{count_rule}
- Prefer boundaries at MAJOR transitions (new section/theme, "now/next/first/in summary", theory↔demo, new dataset/model, Q&A, recap).

Anti-fragmentation rules:
- DO NOT place boundaries merely because a new subtitle line appears.
- Ignore candidate boundaries that are < 45.0s from the previous boundary.
- If a candidate boundary lacks a clear topical cue, discard it during merging.

Output format (exact key order, numbers with 1 decimal place):
{{"boundaries":[
  {{"start": 0.0, "end": 0.0}}
]}}

Do all reasoning internally. Return ONLY the JSON."""


def _request_boundaries_for_window(
    *,
    window: List[Dict[str, Any]],
    duration: float,
    temperature: float,
    whole_video: bool,
    max_chapters: int,
    window_index: int,
    window_count: int,
) -> List[Dict[str, float]]:
    transcript_text = _format_segments_for_prompt(window, _BOUNDARY_CHAR_BUDGET)
    if not transcript_text.strip():
        return []

    w_start, w_end = _window_time_span(window, duration)
    system = _boundary_system_prompt(whole_video=whole_video, max_chapters=max_chapters)
    scope = (
        f"Full video duration: {duration:.1f} seconds."
        if whole_video
        else (
            f"Full video duration: {duration:.1f} seconds.\n"
            f"This is overlapping chunk {window_index}/{window_count} "
            f"covering roughly {w_start:.1f}s ~ {w_end:.1f}s."
        )
    )
    user = f"""{scope}

Transcript with timestamps (each line starts with a timestamp in seconds):
{transcript_text}

Task:
1) Propose candidate major-topic boundaries from the transcript (based on topical cues, not subtitle lines).
2) Enforce: min segment length ≥60.0s AND min boundary gap ≥45.0s.
3) Snap boundaries to existing transcript timestamps.
4) Return ONLY the JSON {{"boundaries":[...]}} with seconds to 1 decimal place."""

    print(
        f"[1단계] 윈도우 {window_index}/{window_count}: "
        f"세그먼트 {len(window)}개, 대략 {w_start:.1f}s~{w_end:.1f}s",
        flush=True,
    )
    try:
        text = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            num_predict=800,
            json_mode=True,
        )
    except OllamaError as e:
        print(f"[1단계] 윈도우 {window_index} Ollama 호출 실패: {e}", flush=True)
        return []

    print(f"[1단계] 윈도우 {window_index} LLM 응답:", flush=True)
    print(text[:500], flush=True)
    boundaries = _parse_boundary_json(text)
    if not boundaries:
        print(f"[1단계] 윈도우 {window_index} JSON 파싱 실패 또는 빈 결과", flush=True)
        return []
    print(f"[1단계] 윈도우 {window_index} 추출 구간: {len(boundaries)}개", flush=True)
    return boundaries


def _extract_time_boundaries(
    segments: List[Dict[str, Any]],
    duration: float,
    temperature: float,
    max_segments: int,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
    merge_gap_sec: float = _DEFAULT_MERGE_GAP_SEC,
) -> List[Dict[str, float]]:
    """1단계: overlap 청킹으로 소주제 경계를 추출한 뒤 절단점을 합친다."""
    print("[1단계] 시간 구간 추출 시작 (overlap chunking)", flush=True)
    print(f"[1단계] 영상 길이: {duration:.1f}초", flush=True)
    print(f"[1단계] 자막 세그먼트: {len(segments)}개", flush=True)

    usable = segments[: max(1, int(max_segments))] if max_segments else segments
    size = max(1, int(chunk_size))
    overlap = max(0, min(int(chunk_overlap), size - 1))
    windows = _iter_overlap_windows(usable, size, overlap)
    max_chapters = _max_chapter_count(duration)

    print(
        f"[1단계] 청크 설정: size={size}, overlap={overlap}, "
        f"windows={len(windows)}, merge_gap={merge_gap_sec:.1f}s, max_chapters={max_chapters}",
        flush=True,
    )

    if not windows:
        print("[1단계] 자막 윈도우 없음, 기본 구간 사용", flush=True)
        return _equal_boundaries(duration)

    all_cuts: List[float] = [0.0, duration]
    whole_video = len(windows) == 1
    success_windows = 0

    for idx, window in enumerate(windows, start=1):
        bounds = _request_boundaries_for_window(
            window=window,
            duration=duration,
            temperature=temperature,
            whole_video=whole_video,
            max_chapters=max_chapters,
            window_index=idx,
            window_count=len(windows),
        )
        if bounds:
            success_windows += 1
            all_cuts.extend(_cuts_from_boundaries(bounds))

    if success_windows == 0:
        print("[1단계] 모든 윈도우 실패, 기본 구간 사용", flush=True)
        return _equal_boundaries(duration)

    boundaries = _boundaries_from_cuts(all_cuts, duration, merge_gap_sec)
    print(f"[1단계] 청크 병합 후 구간 수: {len(boundaries)}개", flush=True)
    for i, b in enumerate(boundaries):
        print(
            f"  {i+1}. {b.get('start', 0):.1f}s ~ {b.get('end', 0):.1f}s "
            f"(길이: {b.get('end', 0) - b.get('start', 0):.1f}초)",
            flush=True,
        )

    if not boundaries:
        print("[1단계] 병합 결과 비어 기본 구간 사용", flush=True)
        return _equal_boundaries(duration)
    return boundaries


def _parse_boundary_json(text: str) -> Optional[List[Dict[str, float]]]:
    """정상 JSON을 먼저 읽고, 잘린 응답만 기존 보정 규칙으로 살린다."""
    raw = (text or "").strip()
    direct = _load_boundaries(raw)
    if direct is not None:
        return direct
    extracted = _load_boundaries(_extract_json_object(raw))
    if extracted is not None:
        return extracted

    json_text = re.sub(r",\s*]", "]", raw)
    json_text = re.sub(r",\s*}", "}", json_text)

    if json_text.startswith("{") and json_text.endswith("]"):
        json_text = "[" + json_text

    if not json_text.startswith('{"boundaries"'):
        if json_text.startswith("["):
            json_text = '{"boundaries": ' + json_text + "}"
        elif not json_text.startswith("{"):
            json_text = '{"boundaries": [' + json_text

    if not json_text.endswith("}"):
        if json_text.endswith("]"):
            json_text = json_text + "}"
        else:
            json_text = json_text + "]}"

    if not json_text.endswith("]}"):
        last_complete = json_text.rfind("},")
        if last_complete != -1:
            print("[1단계] Incomplete JSON 감지, 마지막 완전한 객체까지만 사용", flush=True)
            json_text = json_text[:last_complete + 1] + "]}"
        else:
            print("[1단계] JSON 완전 실패, 빈 배열 사용", flush=True)
            json_text = '{"boundaries": []}'

    return _load_boundaries(json_text)


def _load_boundaries(json_text: str) -> Optional[List[Dict[str, float]]]:
    try:
        obj = json.loads(json_text)
    except Exception:
        return None
    if isinstance(obj, list):
        obj = {"boundaries": obj}
    if not isinstance(obj, dict):
        return None
    boundaries = obj.get("boundaries")
    if not isinstance(boundaries, list):
        return None
    return boundaries


def _validate_and_merge_boundaries(
    boundaries: List[Dict[str, float]],
    duration: float,
    min_duration: float = 60.0,
) -> List[Dict[str, float]]:
    """구간 검증 및 병합 - 너무 많거나 짧은 구간 처리"""
    if not boundaries:
        return boundaries

    max_count = _max_chapter_count(duration)
    print(f"\n[검증] 구간 검증 시작 - 입력: {len(boundaries)}개 (상한 {max_count})", flush=True)

    # 1. 너무 짧은 인접 구간 병합
    merged: List[Dict[str, float]] = []
    current = None
    for b in boundaries:
        if current is None:
            current = dict(b)
            continue
        current_duration = current["end"] - current["start"]
        if current_duration < min_duration:
            current["end"] = b.get("end", current["end"])
            print(f"[검증] 병합: {current['start']:.1f}s ~ {b.get('end', 0):.1f}s (너무 짧음)", flush=True)
        else:
            merged.append(current)
            current = dict(b)
    if current:
        merged.append(current)

    # 2. 상한을 넘으면 가장 짧은 인접 쌍부터 합쳐 연속성을 유지
    while len(merged) > max_count:
        shortest_idx = 0
        shortest_dur = float("inf")
        for i in range(len(merged) - 1):
            dur = merged[i]["end"] - merged[i]["start"]
            if dur < shortest_dur:
                shortest_dur = dur
                shortest_idx = i
        left = merged[shortest_idx]
        right = merged[shortest_idx + 1]
        print(
            f"[검증] 상한 초과 병합: {left['start']:.1f}s~{right['end']:.1f}s "
            f"(기존 {len(merged)}개 → {len(merged) - 1}개)",
            flush=True,
        )
        merged[shortest_idx] = {"start": left["start"], "end": right["end"]}
        del merged[shortest_idx + 1]

    for b in merged:
        if b["end"] > duration:
            print(f"[검증] 종료 시간 수정: {b['end']:.1f}s → {duration:.1f}s", flush=True)
            b["end"] = duration
        if b["start"] >= b["end"]:
            b["end"] = min(b["start"] + 60.0, duration)
            print(f"[검증] 시간 범위 수정: {b['start']:.1f}s ~ {b['end']:.1f}s", flush=True)

    print(f"[검증] 최종 결과: {len(merged)}개 구간", flush=True)
    for i, b in enumerate(merged):
        dur = b["end"] - b["start"]
        print(f"  {i+1}. {b['start']:.1f}s ~ {b['end']:.1f}s (길이: {dur:.1f}초)", flush=True)

    return merged


def _metadata_instructions(lang_name: str) -> str:
    if lang_name == "Korean":
        return """당신은 교육 콘텐츠 요약 전문가입니다. 주어진 자막을 읽고 반드시 JSON만 출력하세요.

출력 형식(JSON):
{"title": "제목", "summary": "요약 내용"}

제약 조건:
1. 제목
   - 3~5개의 단어
   - 7~30자 이내
   - 핵심 키워드 위주, 문장 형태 금지
   - 반드시 순수 한글만 사용
2. 요약
   - 반드시 1문장 또는 2문장만 작성
   - 1문장일 경우 전체 길이 30~120자
   - 2문장일 경우 각 문장은 40~60자, 두 문장의 합은 80~120자
   - 마침표(.)는 최대 두 번까지만 허용
   - 한 번 언급한 내용은 반복하지 말 것
   - 같은 어구나 같은 문장 구조를 두 번 쓰지 말 것
   - 반드시 순수 한글만 사용
3. 공통 규칙
   - 출력에는 영어, 숫자, 알파벳, 외래어, 기호 절대 포함 금지
   - 외래어·전문 용어도 한글로 풀어쓰기
   - JSON 값 안에도 한글만 포함되어야 함
   - JSON 이외의 다른 글자나 설명은 절대 출력하지 말 것"""

    return f"""You are an educational content summarization expert. Read the given transcript and generate JSON only, written in {lang_name}.

Output format (JSON):
{{"title": "Title", "summary": "Summary content"}}

Constraints:
1. Title
   - Must contain 3–5 words
   - Length must be between 7–30 characters
   - Focus on core keywords, not full sentences
   - Must be written in {lang_name} only
2. Summary
   - Must be exactly 1 or 2 sentences
   - If 1 sentence: total length must be 80–120 characters
   - If 2 sentences: each must be 40–60 characters, with a combined total of 80–120 characters
   - Periods (.) are allowed at most twice
   - Do not repeat the same information once mentioned
   - Do not reuse the same phrase or sentence structure
   - Must be written in {lang_name} only
3. Common rules
   - JSON values must contain {lang_name} text only
   - Technical terms should be expressed in plain words
   - Do not output anything other than the JSON"""


def _clean_summary(summary: str) -> str:
    summary = remove_duplicate_sentences(summary)
    return trim_incomplete_last_sentence(summary)


def _parse_title_summary(text: str, transcript: str, start: float) -> Dict[str, str]:
    try:
        if text.startswith('"') and not text.startswith("{"):
            cleaned = text.strip('"')
            print(f"[chapterizer] 따옴표 문자열 처리 - 제목: {cleaned[:50]}", flush=True)
            return {"title": cleaned, "summary": cleaned}

        json_text = text.strip()

        if '"title"' in json_text and '"summary"' not in json_text and json_text.startswith("{"):
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', json_text)
            if title_match:
                title = title_match.group(1)
                after_title = json_text[title_match.end():]
                content_match = re.search(r',\s*"([^"]+)', after_title)
                if content_match:
                    summary = _clean_summary(content_match.group(1))
                    print(f"[chapterizer] summary 키 누락 수정 - 제목: {title[:30]}", flush=True)
                    return {"title": title, "summary": summary}

        json_text = re.sub(r",\s*}", "}", json_text)

        if json_text.startswith("{") and not json_text.endswith("}"):
            if '"summary"' in json_text and json_text.count('"') % 2 == 1:
                json_text = json_text + '"}'
            else:
                json_text = json_text + "}"

        json_start = json_text.find("{")
        if json_start > 0:
            json_text = json_text[json_start:]

        json_end = json_text.rfind("}")
        if json_end != -1:
            json_text = json_text[:json_end + 1]

        if not json_text:
            raise ValueError("JSON 추출 실패")

        obj = json.loads(json_text)
        title = str(obj.get("title", "")).strip()
        summary = _clean_summary(str(obj.get("summary", "")).strip())
        if not title or not summary:
            raise ValueError("제목 또는 요약 비어있음")
        print(f"[chapterizer] JSON 파싱 성공 - 제목: {title[:50]}", flush=True)
        return {"title": title, "summary": summary}
    except Exception as e:
        print(f"[chapterizer] JSON 파싱 실패: {e}, Regex fallback 시도...", flush=True)
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
        summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', text)
        if title_match and summary_match:
            title = title_match.group(1).strip()
            summary = _clean_summary(summary_match.group(1).strip())
            print(f"[chapterizer] Regex 파싱 성공 - 제목: {title[:50]}", flush=True)
            return {"title": title, "summary": summary}

        print("[chapterizer] 파싱 완전 실패, 최종 fallback 사용", flush=True)
        sentences = transcript.split(". ")
        first_sentence = sentences[0][:200] if sentences else transcript[:200]
        return {
            "title": f"Part {int(start / 60) + 1}",
            "summary": first_sentence or "No content",
        }


def _generate_chapter_metadata(
    segments: List[Dict[str, Any]],
    start: float,
    end: float,
    lang: str,
    temperature: float,
) -> Dict[str, str]:
    """구간 하나의 제목/요약을 생성한다. 배치 호출이 실패했을 때의 폴백."""
    transcript = _chapter_transcript(segments, start, end, 1200)
    if not transcript:
        print(f"[chapterizer] 경고: 구간 {start:.1f}s-{end:.1f}s에 자막 없음")
        return {"title": "Untitled", "summary": "No content"}

    lang_name = _lang_label_from_code(lang)
    user_label = "자막 내용" if lang_name == "Korean" else "Subtitles"
    print(f"[2단계] 개별 구간 자막 길이: {len(transcript)}자", flush=True)

    try:
        text = chat(
            [
                {"role": "system", "content": _metadata_instructions(lang_name)},
                {"role": "user", "content": f"{user_label}:\n{transcript}"},
            ],
            temperature=temperature,
            num_predict=200,
            json_mode=True,
        )
    except OllamaError as e:
        print(f"[2단계] Ollama 호출 실패: {e}", flush=True)
        return {
            "title": f"Part {int(start / 60) + 1}",
            "summary": transcript[:200],
        }

    print(f"[2단계] LLM 응답 (첫 200자): {text[:200]}", flush=True)
    return _parse_title_summary(text, transcript, start)


def _generate_chapters_metadata_batch(
    segments: List[Dict[str, Any]],
    boundaries: List[Dict[str, float]],
    lang: Optional[str],
    temperature: float,
) -> Optional[List[Dict[str, str]]]:
    """구간별 제목/요약을 한 번의 JSON 응답으로 받는다. 실패하면 None."""
    if not boundaries:
        return []

    lang_name = _lang_label_from_code(lang)
    per_limit = max(400, _BATCH_CHAR_BUDGET // len(boundaries))
    blocks = []
    for i, boundary in enumerate(boundaries, start=1):
        start = float(boundary.get("start", 0))
        end = float(boundary.get("end", 0))
        transcript = _chapter_transcript(segments, start, end, per_limit) or "(no subtitles)"
        blocks.append(f"[{i}] {start:.1f}s-{end:.1f}s\n{transcript}")

    system = _metadata_instructions(lang_name) + f"""

여러 구간을 한 번에 요약한다. 출력은 아래 JSON 하나만 허용한다.
{{"chapters":[{{"title":"...","summary":"..."}}, ...]}}
chapters 배열 길이는 반드시 {len(boundaries)}개이고, 입력 구간 순서를 유지한다."""

    user = "구간별 자막:\n\n" + "\n\n".join(blocks)
    print(f"[2단계] 배치 제목/요약 요청 - {len(boundaries)}개 구간", flush=True)

    try:
        text = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            num_predict=min(1600, 250 * len(boundaries)),
            json_mode=True,
        )
    except OllamaError as e:
        print(f"[2단계] 배치 호출 실패: {e}", flush=True)
        return None

    print(f"[2단계] 배치 응답 (첫 300자): {text[:300]}", flush=True)
    try:
        obj = json.loads(_extract_json_object(text))
        items = obj.get("chapters")
        if not isinstance(items, list) or len(items) != len(boundaries):
            print(
                f"[2단계] 배치 길이 불일치: 기대 {len(boundaries)}, 실제 {len(items) if isinstance(items, list) else '없음'}",
                flush=True,
            )
            return None
        parsed = []
        for item in items:
            if not isinstance(item, dict):
                return None
            title = str(item.get("title", "")).strip()
            summary = _clean_summary(str(item.get("summary", "")).strip())
            if not title or not summary:
                return None
            parsed.append({"title": title, "summary": summary})
        print(f"[2단계] 배치 파싱 성공 - {len(parsed)}개", flush=True)
        return parsed
    except Exception as e:
        print(f"[2단계] 배치 JSON 파싱 실패: {e}", flush=True)
        return None


def make_chapters(
    *,
    segments: List[Dict[str, Any]],
    duration: float,
    lang: Optional[str],
    temperature: float = 0.2,
    max_segments_for_prompt: int = 1200,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
    merge_gap_sec: float = _DEFAULT_MERGE_GAP_SEC,
) -> List[Dict[str, Any]]:
    """Ollama로 구간을 나눈 뒤 제목/요약을 붙인다. 긴 자막은 overlap 청킹으로 처리한다."""
    print(f"[chapterizer] 2단계 분석 시작 - 세그먼트: {len(segments)}개, 언어: {lang}", flush=True)

    try:
        boundaries = _extract_time_boundaries(
            segments,
            duration,
            temperature,
            max_segments_for_prompt,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            merge_gap_sec=merge_gap_sec,
        )
        if not boundaries:
            print("[chapterizer] 경고: 구간 추출 실패, 빈 리스트 반환", flush=True)
            return []

        boundaries = _validate_and_merge_boundaries(boundaries, duration, min_duration=60.0)

        normalized = []
        for boundary in boundaries:
            start = float(boundary.get("start", 0))
            end = float(boundary.get("end", duration))
            start = max(0.0, min(start, duration))
            end = max(start + 10.0, min(end, duration))
            normalized.append({"start": start, "end": end})

        print(f"\n[chapterizer] 2단계: 제목/요약 생성 시작 ({len(normalized)}개 구간)", flush=True)
        print("=" * 80, flush=True)

        metadatas = _generate_chapters_metadata_batch(segments, normalized, lang, temperature)
        if metadatas is None:
            print("[chapterizer] 배치 생성 실패, 구간별 요청으로 전환", flush=True)
            metadatas = [
                _generate_chapter_metadata(segments, b["start"], b["end"], lang or "", temperature)
                for b in normalized
            ]

        chapters = []
        success_count = 0
        fallback_count = 0
        for i, (boundary, metadata) in enumerate(zip(normalized, metadatas)):
            title = metadata.get("title", "Untitled")
            summary = metadata.get("summary", "")
            chapters.append({
                "start": boundary["start"],
                "end": boundary["end"],
                "title": title,
                "summary": summary,
            })
            if title.startswith("Part ") or title.startswith("Chapter "):
                fallback_count += 1
                print(f"  [{i+1}] Fallback - {title}", flush=True)
            else:
                success_count += 1
                print(f"  [{i+1}] {boundary['start']:.1f}s~{boundary['end']:.1f}s {title}", flush=True)

        print("=" * 80, flush=True)
        print("[챕터 2단계 분석 완료]", flush=True)
        print(f"[생성된 챕터 수] {len(chapters)}개", flush=True)
        print(f"[성공] {success_count}개 / [Fallback] {fallback_count}개", flush=True)
        return chapters
    except Exception as e:
        print(f"[chapterizer] 2단계 분석 중 오류: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return []
