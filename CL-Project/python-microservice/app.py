from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pathlib
import tempfile

from config import Settings
from services.transcriber import transcribe_file
from services.chapterizer import make_chapters_hf  # ← 이 파일로 통일

# (옵션) 원격(OpenAI 호환) 쓰는 경우 유지
# try:
#     from services.chapterizer_remote import make_chapters as make_chapters_remote
# except Exception:
#     make_chapters_remote = None

app = Flask(__name__)
CORS(app, origins=["http://localhost:8181", "http://127.0.0.1:8181"])  # CORS 활성화 (Spring Boot에서의 요청 허용)
cfg = Settings.from_env()

@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "whisper_model": cfg.WHISPER_MODEL,
        "llm_provider": cfg.LLM_PROVIDER,
        "hf_model_id": cfg.HF_MODEL_ID if cfg.LLM_PROVIDER == "hf_local" else None,
        "remote_base_url": cfg.LLM_BASE_URL if cfg.LLM_PROVIDER == "remote" else None
    })

@app.post("/analyze")
def analyze():
    lang_query = request.args.get("lang")
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400

    with tempfile.TemporaryDirectory() as td:
        suffix = pathlib.Path(f.filename).suffix or ".mp4"
        in_path = os.path.join(td, "input" + suffix)
        f.save(in_path)

        # 1) Whisper
        try:
            app.logger.info(f"Starting transcription for file: {in_path}")
            duration, segments, detected_lang = transcribe_file(
                file_path=in_path,
                language=lang_query,  # None이면 자동감지
                whisper_model=cfg.WHISPER_MODEL,
                use_fp16=cfg.WHISPER_FP16
            )
            app.logger.info(f"Transcription completed. Duration: {duration}, Segments: {len(segments)}")
        except Exception as e:
            app.logger.exception("transcription failed: %s", e)
            return jsonify({"error": "transcription failed", "detail": str(e)}), 500

        lang_for_chapter = (lang_query or detected_lang or "").lower()

        print(segments)

        # 2) Chapters
        chapters = []
        if segments:
            try:
                app.logger.info(f"Starting chapterization with {len(segments)} segments")
                provider = (cfg.LLM_PROVIDER or "hf_local").lower()
                if provider == "hf_local":
                    chapters = make_chapters_hf(
                        segments=segments,
                        duration=duration,
                        lang=lang_for_chapter,
                        model_id=cfg.HF_MODEL_ID,
                        load_in_4bit=cfg.HF_LOAD_IN_4BIT,
                        temperature=cfg.HF_TEMPERATURE,
                        max_new_tokens=cfg.HF_MAX_NEW_TOKENS,
                        max_segments_for_prompt=cfg.MAX_SEGMENTS_FOR_PROMPT,
                        hf_token=(cfg.HF_TOKEN or None),
                        # 메모리/오프로딩 전달
                        max_gpu_mem=cfg.HF_MAX_GPU_MEMORY,
                        max_cpu_mem=cfg.HF_MAX_CPU_MEMORY,
                        offload_dir=cfg.HF_OFFLOAD_DIR,
                        low_cpu_mem=cfg.HF_LOW_CPU_MEM,
                        torch_dtype_name=cfg.HF_TORCH_DTYPE
                    )
                    app.logger.info(f"Chapterization completed. Chapters: {len(chapters)}")
                elif provider == "remote" and make_chapters_remote is not None:
                    chapters = make_chapters_remote(
                        segments=segments,
                        duration=duration,
                        lang=lang_for_chapter,
                        llm_base_url=cfg.LLM_BASE_URL,
                        llm_model=cfg.LLM_MODEL,
                        llm_api_key=cfg.LLM_API_KEY,
                        max_segments_for_prompt=cfg.MAX_SEGMENTS_FOR_PROMPT
                    )
                else:
                    app.logger.warning("Unknown LLM_PROVIDER=%s; skip chapterization.", provider)
                    chapters = []
            except Exception as e:
                app.logger.exception("chapterization failed: %s", e)
                chapters = []

        return jsonify({
            "format": "json",
            "duration": duration,
            "segments": segments,
            "chapters": chapters,
            "detected_lang": detected_lang
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
