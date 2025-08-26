# services/transcriber.py
from typing import List, Dict, Tuple, Any, Optional
from faster_whisper import WhisperModel
import torch
import os  # ★ NEW

def _device_and_compute(use_fp16: bool) -> Tuple[str, str]:
    if torch.cuda.is_available():
        # GPU 사용 시 fp16 또는 fp32
        return "cuda", ("float16" if use_fp16 else "float32")
    # CPU에서는 int8이 메모리/속도 유리
    return "cpu", "int8"

_model_cache: Dict[str, WhisperModel] = {}

def _get_model(name: str, use_fp16: bool) -> WhisperModel:
    key = f"{name}:{'fp16' if use_fp16 else 'fp32'}"
    if key not in _model_cache:
        device, compute_type = _device_and_compute(use_fp16)
        # ★ NEW: HF_HOME(볼륨) 재사용하여 모델 캐시 일관화
        download_root = os.getenv("HF_HOME") or None  # ★ NEW
        _model_cache[key] = WhisperModel(
            name,
            device=device,
            compute_type=compute_type,
            download_root=download_root,  # ★ NEW
        )
    return _model_cache[key]

def _round(x: float, n: int = 3) -> float:
    return round(float(x), n)

def transcribe_file(
    file_path: str,
    language: Optional[str],
    whisper_model: str,
    use_fp16: bool
) -> Tuple[float, List[Dict[str, Any]], str]:
    """
    faster-whisper로 자막 추출
    return: (duration, segments[{start,end,text}], lang_code)
    """
    model = _get_model(whisper_model, use_fp16)
    segments_iter, info = model.transcribe(
        file_path,
        language=language,          # None이면 자동감지
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    out: List[Dict[str, Any]] = []
    for seg in segments_iter:
        out.append({
            "start": _round(seg.start),
            "end":   _round(seg.end),
            "text":  (seg.text or "").strip()
        })
    duration = _round(getattr(info, "duration", 0.0))
    lang_code = getattr(info, "language", None) or (language or "")
    return duration, out, lang_code
