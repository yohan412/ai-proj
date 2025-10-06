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

# Windows 한글 인코딩 문제 해결
if sys.platform == "win32":
    # 콘솔 출력을 UTF-8로 설정
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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

    with _lock:
        if _pipe is not None and _loaded_key == want:
            return _pipe

        dtype = _str2dtype(torch_dtype_name)

        # ★ NEW: 레포의 mxfp4 설정(quantization_config 등)을 강제로 무시하도록 config 정리
        hf_cfg = AutoConfig.from_pretrained(                 # ★ NEW
            model_id, token=(hf_token or None), trust_remote_code=True
        )
        for attr in ("quantization_config", "quantization_method", "quantization", "quant_method"):  # ★ NEW
            if hasattr(hf_cfg, attr):
                try:
                    delattr(hf_cfg, attr)                    # ★ NEW
                except Exception:
                    try:
                        setattr(hf_cfg, attr, None)          # ★ NEW
                    except Exception:
                        pass

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
            config=hf_cfg,                                    # ★ NEW: 우리가 정리한 config를 강제 사용
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
                mdl = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    torch_dtype=torch.bfloat16,
                    quantization_config=bnb_cfg,              # ★ CHANGED: 유일한 양자화 진입점
                    **common_kw                               # ★ CHANGED: config=hf_cfg 포함
                )
                print(f"[chapterizer] 4bit 모델 로딩 성공, 파이프라인 생성 중...")
                print(f"[chapterizer] 4bit 파이프라인 생성 시작...")
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
                return _pipe
            except Exception as e:
                print(f"[chapterizer] 4bit load failed -> fallback FP. reason={e}")
                import traceback
                traceback.print_exc()

        if mdl is None:
            print(f"[chapterizer] FP 모델 로딩 시도...")
            mdl = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=dtype,
                **common_kw                                   # ★ CHANGED: FP 경로도 config=hf_cfg 사용
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
        return _pipe

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
    """세그먼트로부터 챕터 생성."""
    print(f"[chapterizer] 함수 호출됨 - 세그먼트: {len(segments)}개, 언어: {lang}")
    print(f"[chapterizer] 모델 ID: {model_id}")
    print(f"[chapterizer] 4bit 로딩: {load_in_4bit}")
    
    try:
        print(f"[chapterizer] 시작 - 세그먼트: {len(segments)}개, 언어: {lang}")
        
        sys_lang = _lang_label_from_code(lang)
        transcript_block = _pack_segments_for_prompt(segments, duration, max_segments_for_prompt)
        print(f"[chapterizer] 프롬프트 준비 완료 - 길이: {len(transcript_block)}자")
    except Exception as e:
        print(f"[chapterizer] 프롬프트 준비 실패: {e}")
        return []

    # Llama-3.2-3B-Instruct 모델용 프롬프트 형식 (전체 자막 기반 소주제 분석)
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an expert video content analyzer. Your task is to analyze the ENTIRE video transcript and identify major subtopics, then create chapters that group related content by these subtopics.

ANALYSIS PROCESS:
1. Read through the ENTIRE transcript to understand the overall content structure
2. Identify 4-8 major subtopics or themes that span multiple segments
3. Group consecutive segments that belong to the same subtopic
4. Create chapter boundaries where subtopics change
5. Each chapter should cover a coherent subtopic with multiple related segments

IMPORTANT RULES:
- Analyze the WHOLE transcript, not individual segments
- Create 4-8 chapters maximum (not one per segment)
- Each chapter should span multiple consecutive segments
- Chapters must represent distinct subtopics or themes
- Use chronological order
- Concise, descriptive chapter titles (2-6 words)
- 1-2 sentence summaries explaining the subtopic
- Times in seconds (float format)
- Use language: {sys_lang}
- Use ONLY ASCII characters in title and summary fields
- NO Unicode characters, NO special symbols

Return STRICT JSON ONLY with this exact schema:
{{"chapters": [{{"start": <float>, "end": <float>, "title": "<string>", "summary": "<string>"}}]}}

DO NOT:
- Create one chapter per segment
- Include explanatory text before or after JSON
- Use markdown code blocks
- Use special Unicode characters or symbols
- Use any non-ASCII characters

<|eot_id|><|start_header_id|>user<|end_header_id|>

Video duration: {round_time(duration)} seconds
Complete transcript:
{transcript_block}

Analyze the ENTIRE transcript and identify major subtopics. Create 4-8 chapters that group related segments by subtopic.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    try:
        print(f"[chapterizer] 모델 로딩 중...")
        pipe = _get_pipe(
            model_id, load_in_4bit, temperature, max_new_tokens, hf_token,
            max_gpu_mem=max_gpu_mem,
            max_cpu_mem=max_cpu_mem,
            offload_dir=offload_dir,
            low_cpu_mem=low_cpu_mem,
            torch_dtype_name=torch_dtype_name
        )
        print(f"[chapterizer] 모델 로딩 완료, 소주제 분석 시작...")
        
        # Llama 모델용 단일 프롬프트 처리
        print(f"[chapterizer] 파이프 실행 시작...")
        print(f"[chapterizer] 프롬프트 길이: {len(prompt)}자")
        print(f"[chapterizer] 프롬프트 미리보기: {prompt[:200]}...")
        print(f"[chapterizer] 파이프 객체 타입: {type(pipe)}")
        print(f"[chapterizer] 파이프 실행 전 상태 확인...")
        
        # 파이프 실행 전 추가 검증
        if pipe is None:
            print(f"[chapterizer] 오류: 파이프 객체가 None입니다!")
            return []
        
        print(f"[chapterizer] 파이프 객체 검증 완료, 추론 시작...")
        
        try:
            print(f"[chapterizer] pipe(prompt) 호출 시작...")
            outputs = pipe(prompt)
            print(f"[chapterizer] pipe(prompt) 호출 완료!")
            print(f"[chapterizer] 파이프 실행 완료, outputs 타입: {type(outputs)}")
            print(f"[chapterizer] outputs 내용: {outputs}")
        except Exception as pipe_error:
            print(f"[chapterizer] pipe(prompt) 실행 중 오류: {pipe_error}")
            import traceback
            traceback.print_exc()
            return []
        
    except Exception as e:
        print(f"[chapterizer] 파이프 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    text = _extract_text(outputs)
    print(f"[chapterizer] 추론 완료, 응답 길이: {len(text)}자")
    print(f"[chapterizer] 응답 내용: {text[:200]}...")
    
    # 전체 응답 내용 확인
    print(f"[chapterizer] 전체 응답: {text}")

    # JSON 파싱 개선 - Unicode 이스케이프 시퀀스 문제 해결
    print(f"[chapterizer] JSON 추출 시작...")
    
    # re 모듈을 함수 시작 부분에서 import
    import re
    import json
    
    # 1차: { } 사이의 JSON 추출
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start != -1 and json_end > json_start:
        json_text = text[json_start:json_end]
        print(f"[chapterizer] 추출된 JSON (1차): {json_text[:200]}...")
        
        # Unicode 이스케이프 시퀀스 정리
        # 잘못된 유니코드 이스케이프 시퀀스 제거 (예: \u0326, \u0328 등)
        json_text = re.sub(r'\\u[0-9a-fA-F]{4}', '', json_text)
        print(f"[chapterizer] 유니코드 정리 후: {json_text[:200]}...")
        
        # JSON 파싱 시도
        try:
            obj = json.loads(json_text)
            print(f"[chapterizer] JSON 파싱 성공 (1차)")
        except Exception as e:
            print(f"[chapterizer] JSON 파싱 실패 (1차): {e}")
            
            # 2차: 정규식으로 재시도
            json_pattern = r'\{[^{}]*"chapters"[^{}]*\[[^\]]*\][^{}]*\}'
            json_matches = re.findall(json_pattern, text, re.DOTALL)
            if json_matches:
                json_text = json_matches[0]
                # 유니코드 정리
                json_text = re.sub(r'\\u[0-9a-fA-F]{4}', '', json_text)
                print(f"[chapterizer] 정규식으로 추출된 JSON: {json_text[:200]}...")
                try:
                    obj = json.loads(json_text)
                    print(f"[chapterizer] JSON 파싱 성공 (2차)")
                except Exception as e2:
                    print(f"[chapterizer] JSON 파싱 실패 (2차): {e2}")
                    obj = {}
            else:
                print(f"[chapterizer] 정규식으로도 JSON을 찾을 수 없음")
                obj = {}
    else:
        print(f"[chapterizer] JSON을 찾을 수 없음, 전체 텍스트에서 파싱 시도")
        # 유니코드 정리
        text = re.sub(r'\\u[0-9a-fA-F]{4}', '', text)
        try:
            obj = json.loads(text)
            print(f"[chapterizer] 전체 텍스트 JSON 파싱 성공")
        except Exception as e:
            print(f"[chapterizer] 전체 텍스트 JSON 파싱 실패: {e}")
            obj = {}
    
    # 최종 검증
    if not obj or not obj.get("chapters"):
        print(f"[chapterizer] 최종 JSON 파싱 실패")
        obj = {}
    
    chapters = obj.get("chapters") or []
    print(f"[chapterizer] 파싱된 챕터 수: {len(chapters)}개")

    cleaned: List[Dict[str, Any]] = []
    for ch in chapters:
        try:
            st = round_time(float(ch.get("start", 0.0)))
            en = round_time(float(ch.get("end", st)))
        except Exception:
            st, en = 0.0, 0.0
        st = max(0.0, min(st, duration))
        en = max(st, min(en, duration))
        title = (ch.get("title") or "").strip()
        summary = (ch.get("summary") or "").strip()
        cleaned.append({"start": st, "end": en, "title": title, "summary": summary})

    cleaned.sort(key=lambda x: x["start"])
    # 겹침 제거
    for i in range(1, len(cleaned)):
        if cleaned[i]["start"] < cleaned[i-1]["end"]:
            cleaned[i]["start"] = cleaned[i-1]["end"]
            cleaned[i]["end"] = max(cleaned[i]["end"], cleaned[i]["start"])
    
    print(f"[chapterizer] 최종 챕터 수: {len(cleaned)}개")
    
    # 챕터 분석 완료 로그
    print(f"\n[챕터 분석 완료]")
    print(f"[생성된 챕터 수] {len(cleaned)}개")
    if cleaned:
        print(f"\n[챕터 목록]")
        for i, chapter in enumerate(cleaned):
            print(f"  {i+1}. [{chapter.get('start', 0):.2f}s - {chapter.get('end', 0):.2f}s] {chapter.get('title', '제목 없음')}")
    else:
        print(f"[경고] 챕터가 생성되지 않았습니다.")
    print()
    
    return cleaned
