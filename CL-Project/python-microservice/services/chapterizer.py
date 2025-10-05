# services/chapterizer.py
from typing import List, Dict, Any, Optional, Tuple
import os
import threading
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from transformers import BitsAndBytesConfig        # ★ NEW: BnB 4bit 설정 사용
from transformers import AutoConfig                # ★ NEW: 레포 config 로드 후 mxfp4 설정 제거

from utils.helpers import round_time, ensure_json

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
    return torch.bfloat16 if torch.cuda.is_available() else torch.float32

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
            max_memory = {"cuda:0": str(max_gpu_mem), "cpu": str(max_cpu_mem)}  # ★ CHANGED: 키 표준화
            device_map = "auto"
        else:
            max_memory = {"cpu": str(max_cpu_mem)}
            device_map = "cpu"                                # ★ NEW: CUDA 없으면 CPU 고정

        common_kw = dict(
            device_map=device_map,
            max_memory=max_memory,
            low_cpu_mem_usage=bool(low_cpu_mem),
            trust_remote_code=True,
            token=(hf_token or None),
            offload_folder=offload_dir,
            config=hf_cfg,                                    # ★ NEW: 우리가 정리한 config를 강제 사용
        )

<<<<<<< HEAD
        # Llama-3.1-8B-Instruct 모델용 토크나이저 설정
=======
        # 토크나이저
>>>>>>> f11bdd0b5e19b09685c2872dc58019d9888e5b01
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
        mdl = None
        if torch.cuda.is_available() and load_in_4bit:
            try:
                bnb_cfg = _make_bnb_config()
                mdl = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    torch_dtype=torch.bfloat16,
                    quantization_config=bnb_cfg,              # ★ CHANGED: 유일한 양자화 진입점
                    **common_kw                               # ★ CHANGED: config=hf_cfg 포함
                )
<<<<<<< HEAD
                _pipe = pipeline(
                    "text-generation",
                    model=mdl, tokenizer=tok,
                    temperature=temperature, max_new_tokens=max_new_tokens,
                    do_sample=True, return_full_text=False,
                    pad_token_id=tok.eos_token_id
                )
                _loaded_key = want
                return _pipe
            except Exception:
                # 실패 시 FP 경로로 폴백
                pass
=======
            except Exception as e:
                print(f"[chapterizer] 4bit load failed -> fallback FP. reason={e}")
>>>>>>> f11bdd0b5e19b09685c2872dc58019d9888e5b01

        if mdl is None:
            mdl = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=dtype,
                **common_kw                                   # ★ CHANGED: FP 경로도 config=hf_cfg 사용
            )

        # 일부 모델 경고 방지: pad 토큰 없으면 eos로 대체
        if tok.pad_token_id is None and tok.eos_token_id is not None:
            tok.pad_token_id = tok.eos_token_id

        _pipe = pipeline(
            "text-generation",
            model=mdl, tokenizer=tok,
            temperature=temperature, max_new_tokens=max_new_tokens,
            do_sample=True, return_full_text=False,
            pad_token_id=tok.eos_token_id
        )
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
    sys_lang = _lang_label_from_code(lang)
    transcript_block = _pack_segments_for_prompt(segments, duration, max_segments_for_prompt)

    # Llama-3.1-8B-Instruct 모델용 프롬프트 형식
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a professional video chapterizer. Your task is to analyze a video transcript and create 3-12 topic-based chapters.

Rules:
- No overlapping time segments
- Chronological order
- Concise chapter titles
- 1-2 sentence summaries
- Times in seconds (float format)
- Use language: {sys_lang}
- Return STRICT JSON ONLY with this exact schema:
{{"chapters": [{{"start": <float>, "end": <float>, "title": "<string>", "summary": "<string>"}}]}}

<|eot_id|><|start_header_id|>user<|end_header_id|>

Video duration (seconds): {round_time(duration)}
Transcript lines (start|end|text):
{transcript_block}

Please analyze this transcript and create chapters as requested.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    pipe = _get_pipe(
        model_id, load_in_4bit, temperature, max_new_tokens, hf_token,
        max_gpu_mem=max_gpu_mem,
        max_cpu_mem=max_cpu_mem,
        offload_dir=offload_dir,
        low_cpu_mem=low_cpu_mem,
        torch_dtype_name=torch_dtype_name
    )
    # Llama 모델용 단일 프롬프트 처리
    outputs = pipe(prompt)
    text = _extract_text(outputs)

    obj = ensure_json(text) or {}
    chapters = obj.get("chapters") or []

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
    return cleaned
