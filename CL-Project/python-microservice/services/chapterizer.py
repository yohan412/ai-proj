# services/chapterizer.py
from typing import List, Dict, Any, Optional, Tuple
import os
import threading
import torch
import sys
import io
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from transformers import BitsAndBytesConfig        # ★ NEW: BnB 4bit 설정 사용
from transformers import AutoConfig                # ★ NEW: 레포 config 로드 후 mxfp4 설정 제거

from utils.helpers import round_time, ensure_json

# Windows 한글 인코딩은 app.py에서 처리됨

# 전역 파이프 캐시
_pipe = None
_loaded_key: Tuple[str, bool, bool, str, str, str, bool, str] = ("", False, False, "", "", "", False, "")
_lock = threading.Lock()

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

def _str2dtype(name: str):
    name = (name or "auto").lower()
    if name == "float16": return torch.float16
    if name == "bfloat16": return torch.bfloat16
    if name == "float32": return torch.float32
    # ★ CHANGED: auto → CUDA면 bfloat16, 아니면 float32
    if torch.cuda.is_available():
        print(f"[chapterizer] GPU detected: {torch.cuda.get_device_name(0)}")
        print(f"[chapterizer] GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        return torch.bfloat16
    else:
        print("[chapterizer] No GPU detected, using CPU with float32")
        return torch.float32

def _make_bnb_config() -> BitsAndBytesConfig:
    """BitsAndBytes 4bit(NF4) 설정 (CUDA 전용)."""
    return BitsAndBytesConfig(               # ★ NEW
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

def _get_pipe(
    model_id: str,
    load_in_4bit: bool,           # ★ CHANGED: 시그니처는 유지(환경변수 연동용), 실제 전달은 quantization_config로만
    temperature: float,
    max_new_tokens: int,
    hf_token: Optional[str],
    max_gpu_mem: str,
    max_cpu_mem: str,
    offload_dir: str,
    low_cpu_mem: bool,
    torch_dtype_name: str
):
    """텍스트 생성 파이프라인 준비(캐시됨)."""
    global _pipe, _loaded_key

    want = (
        model_id, load_in_4bit, torch.cuda.is_available(),
        max_gpu_mem, max_cpu_mem, offload_dir, low_cpu_mem, torch_dtype_name
    )
    if _pipe is not None and _loaded_key == want:
        return _pipe

    try:
        with _lock:
            if _pipe is not None and _loaded_key == want:
                return _pipe

        dtype = _str2dtype(torch_dtype_name)

        # 디바이스/메모리 매핑
        if torch.cuda.is_available():
            # GPU 사용 시 최적화된 설정
            max_memory = {0: str(max_gpu_mem), "cpu": str(max_cpu_mem)}
            device_map = "auto"
            print(f"[chapterizer] Using GPU with {max_gpu_mem} GPU memory, {max_cpu_mem} CPU memory")
        else:
            # CPU 사용 시 설정
            max_memory = {"cpu": str(max_cpu_mem)}
            device_map = "cpu"
            print(f"[chapterizer] Using CPU with {max_cpu_mem} CPU memory")

        common_kw = dict(
            device_map=device_map,
            max_memory=max_memory,
            low_cpu_mem_usage=bool(low_cpu_mem),
            trust_remote_code=True,
            token=(hf_token or None),
            offload_folder=offload_dir,
        )

        # Llama-3.1-8B-Instruct 모델용 토크나이저 설정
        tok = AutoTokenizer.from_pretrained(
            model_id, 
            use_fast=True, 
            trust_remote_code=True, 
            token=(hf_token or None)
        )
        
        # Llama 모델용 패딩 토큰 설정
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token

        # 모델 로드: 4bit(BnB) 우선 시도 → 실패 시 FP 폴백
        print(f"[chapterizer] 모델 로딩 시작 - 4bit: {load_in_4bit}, CUDA: {torch.cuda.is_available()}")
        mdl = None
        if torch.cuda.is_available() and load_in_4bit:
            try:
                print(f"[chapterizer] 4bit 모델 로딩 시도...")
                bnb_cfg = _make_bnb_config()
                print(f"[chapterizer] BnB 설정 완료, 모델 다운로드 시작...")
                print(f"[chapterizer] AutoModelForCausalLM.from_pretrained 호출 시작...")
                print(f"[chapterizer] model_id: {model_id}")
                print(f"[chapterizer] torch_dtype: torch.bfloat16")
                print(f"[chapterizer] common_kw keys: {list(common_kw.keys())}")
                
                try:
                    mdl = AutoModelForCausalLM.from_pretrained(
                        model_id,
                        torch_dtype=torch.bfloat16,
                        quantization_config=bnb_cfg,
                        **common_kw
                    )
                    print(f"[chapterizer] AutoModelForCausalLM.from_pretrained 호출 완료!")
                except Exception as load_error:
                    print(f"[chapterizer] from_pretrained 내부 오류: {load_error}")
                    import traceback
                    traceback.print_exc()
                    raise load_error
                
                print(f"[chapterizer] 4bit 모델 로딩 성공, 파이프라인 생성 중...")
                print(f"[chapterizer] 4bit 파이프라인 생성 시작...")
                
                # 파이프라인 생성 전 토크나이저 검증
                print(f"[chapterizer] 토크나이저 검증 - pad_token_id: {tok.pad_token_id}, eos_token_id: {tok.eos_token_id}")
                
                _pipe = pipeline(
                    "text-generation",
                    model=mdl, tokenizer=tok,
                    temperature=temperature, max_new_tokens=max_new_tokens,
                    do_sample=True, return_full_text=False,
                    pad_token_id=tok.eos_token_id
                )
                print(f"[chapterizer] 4bit 파이프라인 생성 완료")
                print(f"[chapterizer] 파이프라인 객체 타입: {type(_pipe)}")
                _loaded_key = want
                print(f"[chapterizer] 파이프라인 반환 준비 완료")
                return _pipe
            except Exception as e:
                print(f"[chapterizer] 4bit load failed -> fallback FP. reason={e}")
                import traceback
                traceback.print_exc()
                mdl = None

        if mdl is None:
            print(f"[chapterizer] FP 모델 로딩 시도...")
            mdl = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=dtype,
                **common_kw
            )
            print(f"[chapterizer] FP 모델 로딩 성공, 파이프라인 생성 중...")

        # 일부 모델 경고 방지: pad 토큰 없으면 eos로 대체
        if tok.pad_token_id is None and tok.eos_token_id is not None:
            tok.pad_token_id = tok.eos_token_id

        print(f"[chapterizer] FP 파이프라인 생성 시작...")
        _pipe = pipeline(
            "text-generation",
            model=mdl, tokenizer=tok,
            temperature=temperature, max_new_tokens=max_new_tokens,
            do_sample=True, return_full_text=False,
            pad_token_id=tok.eos_token_id
        )
        print(f"[chapterizer] FP 파이프라인 생성 완료")
        print(f"[chapterizer] 파이프라인 객체 타입: {type(_pipe)}")
        _loaded_key = want
        print(f"[chapterizer] FP 파이프라인 반환 준비 완료")
        return _pipe
    except Exception as global_error:
        print(f"[chapterizer] _get_pipe 전체 오류 발생: {global_error}")
        import traceback
        traceback.print_exc()
        return None

def _pack_segments_for_prompt(segments: List[Dict[str, Any]], duration: float, max_segments: int) -> str:
    """세그먼트를 프롬프트로 압축."""
    segs = segments
    if len(segs) > max_segments:
        step = len(segs) / max_segments
        idxs = [int(i * step) for i in range(max_segments)]
        segs = [segments[i] for i in idxs]
    lines = []
    for s in segs:
        st = round_time(s.get("start", 0.0))
        en = round_time(s.get("end", 0.0))
        tx = (s.get("text") or "").strip()
        lines.append(f"{st:.3f}|{en:.3f}|{tx}")
    return "\n".join(lines)

def _extract_text(outputs: List[Dict[str, Any]]) -> str:
    """pipeline 출력에서 텍스트만 추출."""
    if not outputs:
        return ""
    o = outputs[0]
    if "generated_text" in o:
        gt = o["generated_text"]
        if isinstance(gt, list) and gt:
            last = gt[-1]
            if isinstance(last, dict):
                content = last.get("content", "")
                if isinstance(content, list):
                    return "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
                return str(content)
            return str(last)
        if isinstance(gt, str):
            return gt
    if "text" in o:
        return str(o["text"])
    return ""

def _extract_time_boundaries(segments: List[Dict[str, Any]], duration: float, pipe) -> List[Dict[str, float]]:
    """1단계: 소주제 경계만 추출 (시간 구간만) - MAJOR topics only"""
    import re
    import json
    
    print(f"[1단계] 시간 구간 추출 시작")
    print(f"[1단계] 영상 길이: {duration:.1f}초")
    print(f"[1단계] 자막 세그먼트: {len(segments)}개")
    
    # 전체 자막을 압축하여 프롬프트에 포함
    transcript_lines = []
    for s in segments[:200]:  # 최대 200개만
        transcript_lines.append(f"{s.get('start', 0):.1f}s: {s.get('text', '').strip()}")
    transcript_text = "\n".join(transcript_lines)
    
    # ★ 대폭 개선된 프롬프트
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a video content analyzer. Your task is to identify 4-8 MAJOR subtopics in this educational video.

IMPORTANT RULES:
1. Find only MAJOR topic transitions (e.g., "Introduction" → "Main Concept" → "Examples" → "Applications")
2. Each segment should be at least 60 seconds long
3. DO NOT split every sentence - group related content together
4. Return EXACTLY 4-8 segments, no more

Return this JSON format:
{{"boundaries": [
  {{"start": 0.0, "end": 120.5}},
  {{"start": 120.5, "end": 250.0}}
]}}

<|eot_id|><|start_header_id|>user<|end_header_id|>

Video duration: {duration:.1f} seconds

Full transcript with timestamps:
{transcript_text}

Analyze the complete transcript and identify 4-8 MAJOR subtopics.
Return ONLY the JSON with time boundaries.

<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{{"boundaries": [
"""
    
    # ★ max_new_tokens=500, temperature=0.2
    outputs = pipe(prompt, max_new_tokens=500, temperature=0.2)
    text = _extract_text(outputs)
    
    # ★ 전체 응답 출력
    print(f"[1단계] LLM 응답 (전체):")
    print("=" * 80)
    print(text)
    print("=" * 80)
    
    # JSON 파싱
    json_text = text
    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)  # 마지막 쉼표 제거
    
    try:
        json_start = text.find('{')
        if json_start == -1:
            # { 없으면 시작 부분 추가
            json_text = '{"boundaries": [' + text
        else:
            json_end = text.rfind('}') + 1
            if json_end > json_start:
                json_text = text[json_start:json_end]
        
        obj = json.loads(json_text)
        boundaries = obj.get("boundaries", [])
        
        print(f"[1단계] 추출된 구간 수: {len(boundaries)}개")
        for i, b in enumerate(boundaries):
            duration_sec = b.get('end', 0) - b.get('start', 0)
            print(f"  {i+1}. {b.get('start', 0):.1f}s ~ {b.get('end', 0):.1f}s (길이: {duration_sec:.1f}초)")
        
        return boundaries
    except Exception as e:
        print(f"[1단계] JSON 파싱 실패: {e}, 기본 구간 사용")
        # 실패 시 균등 분할
        num_chapters = 6
        chunk_duration = duration / num_chapters
        return [{"start": i * chunk_duration, "end": (i + 1) * chunk_duration} for i in range(num_chapters)]

def _validate_and_merge_boundaries(boundaries: List[Dict[str, float]], duration: float, min_duration: float = 60.0) -> List[Dict[str, float]]:
    """구간 검증 및 병합 - 너무 많거나 짧은 구간 처리"""
    if not boundaries:
        return boundaries
    
    print(f"\n[검증] 구간 검증 시작 - 입력: {len(boundaries)}개")
    
    # 1. 너무 많은 구간 필터링 (> 10개)
    if len(boundaries) > 10:
        print(f"[경고] 구간이 너무 많음 ({len(boundaries)}개) - 상위 8개만 사용")
        # 긴 구간 우선 선택
        boundaries_with_duration = []
        for b in boundaries:
            dur = b.get('end', 0) - b.get('start', 0)
            boundaries_with_duration.append((b, dur))
        
        boundaries_with_duration.sort(key=lambda x: x[1], reverse=True)
        boundaries = [b[0] for b in boundaries_with_duration[:8]]
        boundaries.sort(key=lambda x: x.get('start', 0))
        print(f"[검증] 필터링 후: {len(boundaries)}개 구간")
    
    # 2. 너무 짧은 구간 병합 (< min_duration)
    merged = []
    current = None
    
    for b in boundaries:
        if current is None:
            current = dict(b)  # 복사
        else:
            current_duration = current['end'] - current['start']
            if current_duration < min_duration:
                # 현재 구간이 너무 짧으면 다음 구간과 병합
                current['end'] = b.get('end', current['end'])
                print(f"[검증] 병합: {current['start']:.1f}s ~ {b.get('end', 0):.1f}s (너무 짧음)")
            else:
                # 현재 구간이 충분히 길면 추가하고 새로 시작
                merged.append(current)
                current = dict(b)
    
    # 마지막 구간 추가
    if current:
        merged.append(current)
    
    # 3. 최종 검증 - duration 초과 수정
    for b in merged:
        if b['end'] > duration:
            print(f"[검증] 종료 시간 수정: {b['end']:.1f}s → {duration:.1f}s")
            b['end'] = duration
        if b['start'] >= b['end']:
            b['end'] = min(b['start'] + 60.0, duration)
            print(f"[검증] 시간 범위 수정: {b['start']:.1f}s ~ {b['end']:.1f}s")
    
    print(f"[검증] 최종 결과: {len(merged)}개 구간")
    for i, b in enumerate(merged):
        dur = b['end'] - b['start']
        print(f"  {i+1}. {b['start']:.1f}s ~ {b['end']:.1f}s (길이: {dur:.1f}초)")
    
    return merged

def _generate_chapter_metadata(segments: List[Dict[str, Any]], start: float, end: float, lang: str, pipe) -> Dict[str, str]:
    """2단계: 해당 구간의 자막으로 제목/요약 생성 (원본 언어)"""
    import re
    import json
    
    # 해당 구간의 자막만 필터링
    chapter_segments = [s for s in segments if s.get('start', 0) >= start and s.get('end', 0) <= end]
    
    if not chapter_segments:
        print(f"[chapterizer] 경고: 구간 {start:.1f}s-{end:.1f}s에 자막 없음")
        return {"title": "Untitled", "summary": "No content"}
    
    # 자막 텍스트 결합
    transcript = " ".join([s.get('text', '').strip() for s in chapter_segments])
    
    if not transcript.strip():
        print(f"[chapterizer] 경고: 구간 {start:.1f}s-{end:.1f}s의 자막이 비어있음")
        return {"title": "Untitled", "summary": "No content"}
    
    # 언어에 따른 프롬프트
    lang_name = _lang_label_from_code(lang)
    
    # ★ 개선된 프롬프트 - {"title": " 제거
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a content summarizer. Read the subtitles and create:
1. A short title (3-5 words) in {lang_name}
2. A brief summary (1-2 sentences) in {lang_name}

Return ONLY this JSON:
{{"title": "Title Here", "summary": "Summary here."}}

<|eot_id|><|start_header_id|>user<|end_header_id|>

Subtitles:
{transcript[:800]}

<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    
    print(f"[2단계] 자막 길이: {len(transcript)}자, 프롬프트 길이: {len(prompt)}자")
    
    # ★ max_new_tokens=200 (챕터 제목/요약용)
    outputs = pipe(prompt, max_new_tokens=200, temperature=0.3)
    text = _extract_text(outputs)
    
    print(f"[2단계] LLM 응답 (첫 200자): {text[:200]}")
    
    # JSON 파싱
    json_text = text
    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)  # 마지막 쉼표 제거
    
    try:
        # JSON 추출
        json_start = text.find('{')
        if json_start == -1:
            # { 없으면 시작부터 JSON이라고 가정
            json_text = '{"title": "' + text
        else:
            json_end = text.rfind('}') + 1
            if json_end > json_start:
                json_text = text[json_start:json_end]
        
        obj = json.loads(json_text)
        title = obj.get("title", "").strip()
        summary = obj.get("summary", "").strip()
        
        if title and summary:
            print(f"[chapterizer] ✅ JSON 파싱 성공 - 제목: {title[:50]}")
            return {"title": title, "summary": summary}
        else:
            raise ValueError("제목 또는 요약 비어있음")
            
    except Exception as e:
        print(f"[chapterizer] ⚠️ JSON 파싱 실패: {e}, Regex fallback 시도...")
        
        # ★ Regex fallback
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
        summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', text)
        
        if title_match and summary_match:
            title = title_match.group(1).strip()
            summary = summary_match.group(1).strip()
            print(f"[chapterizer] ✅ Regex 파싱 성공 - 제목: {title[:50]}")
            return {"title": title, "summary": summary}
        
        # ★ 최종 fallback - 의미있는 요약
        print(f"[chapterizer] ❌ 파싱 완전 실패, 최종 fallback 사용")
        sentences = transcript.split('. ')
        first_sentence = sentences[0][:200] if sentences else transcript[:200]
        
        return {
            "title": f"Part {int(start/60)+1}",
            "summary": first_sentence
        }

def make_chapters_hf(
    *,
    segments: List[Dict[str, Any]],
    duration: float,
    lang: Optional[str],                 # Whisper 감지 언어코드
    model_id: str,
    load_in_4bit: bool,
    temperature: float,
    max_new_tokens: int,
    max_segments_for_prompt: int,
    hf_token: Optional[str] = None,
    # 메모리/오프로딩 인자
    max_gpu_mem: str = "18GiB",
    max_cpu_mem: str = "32GiB",
    offload_dir: str = "./offload",
    low_cpu_mem: bool = True,
    torch_dtype_name: str = "auto",
) -> List[Dict[str, Any]]:
    """★ NEW: 2단계 챕터 생성 방식 - 구간 추출 후 제목/요약 생성"""
    print(f"[chapterizer] 2단계 분석 시작 - 세그먼트: {len(segments)}개, 언어: {lang}")
    print(f"[chapterizer] 모델 ID: {model_id}")
    
    try:
        # 파이프라인 로드
        print(f"[chapterizer] 모델 로딩 중...")
        pipe = _get_pipe(
            model_id, load_in_4bit, 0.3, max_new_tokens, hf_token,
            max_gpu_mem=max_gpu_mem,
            max_cpu_mem=max_cpu_mem,
            offload_dir=offload_dir,
            low_cpu_mem=low_cpu_mem,
            torch_dtype_name=torch_dtype_name
        )
        
        if pipe is None:
            print(f"[chapterizer] 오류: 파이프 로드 실패!")
            return []
        
        print(f"[chapterizer] 모델 로딩 완료")
        
        # ★ 1단계: 시간 구간 추출
        boundaries = _extract_time_boundaries(segments, duration, pipe)
        
        if not boundaries:
            print(f"[chapterizer] 경고: 구간 추출 실패, 빈 리스트 반환")
            return []
        
        # ★ 구간 검증 및 병합
        boundaries = _validate_and_merge_boundaries(boundaries, duration, min_duration=60.0)
        
        # ★ 2단계: 각 구간의 제목/요약 생성
        print(f"\n[chapterizer] 2단계: 각 구간의 제목/요약 생성 시작 ({len(boundaries)}개 구간)")
        print("=" * 80)
        chapters = []
        success_count = 0
        fallback_count = 0
        
        for i, boundary in enumerate(boundaries):
            start = float(boundary.get('start', 0))
            end = float(boundary.get('end', duration))
            
            # 시간 범위 검증
            start = max(0.0, min(start, duration))
            end = max(start + 10.0, min(end, duration))  # 최소 10초 보장
            
            print(f"\n  [{i+1}/{len(boundaries)}] 구간 분석: {start:.1f}s ~ {end:.1f}s (길이: {end-start:.1f}초)")
            
            # 해당 구간의 제목/요약 생성
            metadata = _generate_chapter_metadata(segments, start, end, lang, pipe)
            
            title = metadata.get("title", "Untitled")
            summary = metadata.get("summary", "")
            
            chapters.append({
                "start": start,
                "end": end,
                "title": title,
                "summary": summary
            })
            
            # 성공/실패 카운트
            if title.startswith("Part ") or title.startswith("Chapter "):
                fallback_count += 1
                print(f"     ⚠️ Fallback 사용됨")
            else:
                success_count += 1
                print(f"     ✅ 성공")
            
            print(f"     제목: {title}")
            print(f"     요약: {summary[:100]}{'...' if len(summary) > 100 else ''}")
        
        print(f"\n{'=' * 80}")
        print(f"[챕터 2단계 분석 완료]")
        print(f"[생성된 챕터 수] {len(chapters)}개")
        print(f"[성공] {success_count}개 / [Fallback] {fallback_count}개")
        
        if chapters:
            print(f"\n[챕터 목록]")
            for i, chapter in enumerate(chapters):
                print(f"  {i+1}. [{chapter['start']:.2f}s - {chapter['end']:.2f}s] {chapter['title']}")
        
        print()
        return chapters
        
    except Exception as e:
        print(f"[chapterizer] 2단계 분석 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return []
