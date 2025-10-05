# services/chapterizer.py
from typing import List, Dict, Any, Optional, Tuple
import os
import threading
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from utils.helpers import round_time, clamp, ensure_json

_pipe = None
_loaded_key: Tuple[str, bool, bool, str, str, str, bool, str] = ("", False, False, "", "", "", False, "")
_lock = threading.Lock()

def _lang_label_from_code(code: Optional[str]) -> str:
    code = (code or "").lower()
    table = {
        "ko":"Korean","en":"English","ja":"Japanese",
        "zh":"Chinese","zh-cn":"Chinese","zh-tw":"Chinese (Traditional)",
        "es":"Spanish","fr":"French","de":"German","it":"Italian",
        "pt":"Portuguese","ru":"Russian","vi":"Vietnamese",
        "id":"Indonesian","th":"Thai","hi":"Hindi","ar":"Arabic",
    }
    return table.get(code, "the same language as the transcript")

def _str2dtype(name: str):
    name = (name or "auto").lower()
    if name == "float16": return torch.float16
    if name == "bfloat16": return torch.bfloat16
    if name == "float32": return torch.float32
    return torch.float16 if torch.cuda.is_available() else torch.float32  # auto

def _get_pipe(
    model_id: str,
    load_in_4bit: bool,
    temperature: float,
    max_new_tokens: int,
    hf_token: Optional[str],
    max_gpu_mem: str,
    max_cpu_mem: str,
    offload_dir: str,
    low_cpu_mem: bool,
    torch_dtype_name: str
):
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
        device_map = "auto"
        if torch.cuda.is_available():
            max_memory = {0: str(max_gpu_mem), "cpu": str(max_cpu_mem)}
        else:
            max_memory = {"cpu": str(max_cpu_mem)}

        common_kw = dict(
            device_map=device_map,
            max_memory=max_memory,
            low_cpu_mem_usage=bool(low_cpu_mem),
            trust_remote_code=True,
            token=(hf_token or None),
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

        # 4bit (GPU 권장) 우선 시도
        if load_in_4bit and torch.cuda.is_available():
            try:
                mdl = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16,
                    offload_folder=offload_dir,
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                    **common_kw
                )
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

        # FP16/FP32 경로 (+ 디스크 오프로딩 허용)
        try:
            mdl = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=dtype,
                offload_folder=offload_dir,
                **common_kw
            )
        except ValueError as ve:
            msg = str(ve).lower()
            if "disk_offload" in msg or "offload the whole model" in msg:
                raise RuntimeError(
                    "가용 GPU/CPU 메모리가 부족합니다. "
                    "HF_MAX_GPU_MEMORY/HF_MAX_CPU_MEMORY 값을 늘리거나, "
                    "GPU + HF_LOAD_IN_4BIT=true로 4bit 로딩을 사용하세요. "
                    f"(GPU={torch.cuda.is_available()}, max_gpu_mem={max_gpu_mem}, max_cpu_mem={max_cpu_mem})"
                ) from ve
            raise

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
                    return "".join([c.get("text","") if isinstance(c, dict) else str(c) for c in content])
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
    # ↓ 메모리/오프로딩 인자 추가
    max_gpu_mem: str = "12GiB",
    max_cpu_mem: str = "64GiB",
    offload_dir: str = "./offload",
    low_cpu_mem: bool = True,
    torch_dtype_name: str = "auto",
) -> List[Dict[str, Any]]:

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
        st = round_time(float(ch.get("start", 0.0)))
        en = round_time(float(ch.get("end", st)))
        st = max(0.0, min(st, duration))
        en = max(st, min(en, duration))
        title = (ch.get("title") or "").strip()
        summary = (ch.get("summary") or "").strip()
        cleaned.append({"start": st, "end": en, "title": title, "summary": summary})

    cleaned.sort(key=lambda x: x["start"])
    for i in range(1, len(cleaned)):
        if cleaned[i]["start"] < cleaned[i-1]["end"]:
            cleaned[i]["start"] = cleaned[i-1]["end"]
            cleaned[i]["end"]   = max(cleaned[i]["end"], cleaned[i]["start"])
    return cleaned
