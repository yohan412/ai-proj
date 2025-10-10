# services/translator.py
from typing import Optional, List
import re

# Windows 한글 인코딩은 app.py에서 처리됨

def _lang_name_from_code(code: Optional[str]) -> str:
    """언어 코드를 전체 이름으로 변환"""
    code = (code or "").lower()
    table = {
        "ko": "Korean", "en": "English", "ja": "Japanese",
        "zh": "Chinese", "zh-cn": "Chinese", "zh-tw": "Chinese (Traditional)",
        "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
        "pt": "Portuguese", "ru": "Russian", "vi": "Vietnamese",
        "id": "Indonesian", "th": "Thai", "hi": "Hindi", "ar": "Arabic",
    }
    return table.get(code, code or "Korean")

def translate_text(
    *,
    text: str,
    target_lang: str,
    model_id: str,
    load_in_4bit: bool = True,
    hf_token: Optional[str] = None,
    max_gpu_mem: str = "18GiB",
    max_cpu_mem: str = "32GiB",
    offload_dir: str = "./offload",
    low_cpu_mem: bool = True,
    torch_dtype_name: str = "auto",
) -> str:
    """
    영어 텍스트를 타겟 언어로 번역합니다.
    chapterizer의 파이프라인을 재사용하여 메모리 효율성 향상.
    
    Args:
        text: 번역할 영어 텍스트
        target_lang: 타겟 언어 코드 (예: 'ko', 'ja', 'en')
        model_id: 사용할 모델 ID
        기타: chapterizer와 동일한 설정들
    
    Returns:
        번역된 텍스트 (실패 시 원본 반환)
    """
    # 영어인 경우 번역 불필요
    if target_lang and target_lang.lower() in ['en', 'english']:
        return text
    
    target_lang_name = _lang_name_from_code(target_lang)
    
    print(f"[translator] 번역 시작 - 타겟 언어: {target_lang_name}")
    print(f"[translator] 원본 텍스트 길이: {len(text)}자")
    
    # ★ NEW: chapterizer의 파이프라인 재사용
    try:
        from services.chapterizer import _get_pipe, _extract_text
        
        # ★ CHANGED: 프롬프트 개선 - 더 명확하고 간결한 지시
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a professional translator. Translate English to {target_lang_name}.

CRITICAL RULES:
- Translate ONLY the given text
- Do NOT add any explanations or comments
- Use natural {target_lang_name} expressions
- Output ONLY the translated text

<|eot_id|><|start_header_id|>user<|end_header_id|>

{text}

<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        
        # ★ CHANGED: temperature=0.1로 거의 결정적 번역
        pipe = _get_pipe(
            model_id, load_in_4bit, 0.1, 256, hf_token,
            max_gpu_mem=max_gpu_mem,
            max_cpu_mem=max_cpu_mem,
            offload_dir=offload_dir,
            low_cpu_mem=low_cpu_mem,
            torch_dtype_name=torch_dtype_name
        )
        
        if pipe is None:
            print(f"[translator] 오류: 파이프 객체가 None입니다!")
            return text
        
        print(f"[translator] 번역 추론 시작 (temperature=0.1)...")
        outputs = pipe(prompt)
        
        translated = _extract_text(outputs)
        print(f"[translator] 번역 완료 - 결과 길이: {len(translated)}자")
        
        # 번역이 비어있거나 너무 짧으면 원본 반환
        if not translated or len(translated.strip()) < 2:
            print(f"[translator] 경고: 번역 결과가 비어있음, 원본 반환")
            return text
        
        return translated.strip()
        
    except Exception as e:
        print(f"[translator] 번역 실패: {e}")
        import traceback
        traceback.print_exc()
        return text  # 실패 시 원본 반환

def translate_batch(
    *,
    texts: List[str],
    target_lang: str,
    model_id: str,
    load_in_4bit: bool = True,
    hf_token: Optional[str] = None,
    max_gpu_mem: str = "18GiB",
    max_cpu_mem: str = "32GiB",
    offload_dir: str = "./offload",
    low_cpu_mem: bool = True,
    torch_dtype_name: str = "auto",
) -> List[str]:
    """
    여러 텍스트를 한 번에 번역합니다 (성능 최적화).
    
    Args:
        texts: 번역할 영어 텍스트 리스트
        target_lang: 타겟 언어 코드
        기타: 동일한 설정
    
    Returns:
        번역된 텍스트 리스트
    """
    # 영어인 경우 번역 불필요
    if target_lang and target_lang.lower() in ['en', 'english']:
        return texts
    
    if not texts:
        return []
    
    target_lang_name = _lang_name_from_code(target_lang)
    
    print(f"[translator] 배치 번역 시작 - 타겟 언어: {target_lang_name}, 항목 수: {len(texts)}개")
    
    # ★ 배치 번역: 모든 텍스트를 구분자로 연결
    combined_text = "\n###SEPARATOR###\n".join(texts)
    print(f"[translator] 결합된 텍스트 길이: {len(combined_text)}자")
    
    try:
        from services.chapterizer import _get_pipe, _extract_text
        
        # ★ 배치 번역용 프롬프트
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a professional translator. Translate the following texts from English to {target_lang_name}.

CRITICAL RULES:
- Translate each text separated by ###SEPARATOR###
- Keep the ###SEPARATOR### between translations
- Do NOT add explanations or comments
- Use natural {target_lang_name} expressions
- Output ONLY the translations with ###SEPARATOR### between them

<|eot_id|><|start_header_id|>user<|end_header_id|>

{combined_text}

<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        
        # ★ temperature=0.1로 거의 결정적 번역
        pipe = _get_pipe(
            model_id, load_in_4bit, 0.1, 1024, hf_token,
            max_gpu_mem=max_gpu_mem,
            max_cpu_mem=max_cpu_mem,
            offload_dir=offload_dir,
            low_cpu_mem=low_cpu_mem,
            torch_dtype_name=torch_dtype_name
        )
        
        if pipe is None:
            print(f"[translator] 오류: 파이프 객체가 None입니다!")
            return texts
        
        print(f"[translator] 배치 번역 추론 시작 (temperature=0.1)...")
        outputs = pipe(prompt)
        
        translated_combined = _extract_text(outputs)
        print(f"[translator] 배치 번역 완료 - 결과 길이: {len(translated_combined)}자")
        
        # 구분자로 분리
        translated_list = translated_combined.split("###SEPARATOR###")
        translated_list = [t.strip() for t in translated_list]
        
        # 결과 개수가 맞지 않으면 원본 반환
        if len(translated_list) != len(texts):
            print(f"[translator] 경고: 번역 개수 불일치 ({len(translated_list)} != {len(texts)}), 원본 반환")
            return texts
        
        print(f"[translator] 배치 번역 성공: {len(translated_list)}개 항목")
        return translated_list
        
    except Exception as e:
        print(f"[translator] 배치 번역 실패: {e}")
        import traceback
        traceback.print_exc()
        return texts  # 실패 시 원본 반환
