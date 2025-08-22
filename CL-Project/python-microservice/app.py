from flask import Flask, request, jsonify
import os
import pathlib
import tempfile

from config import Settings
from services.transcriber import transcribe_file
from services.chapterizer import make_chapters

app = Flask(__name__)
cfg = Settings.from_env()

@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "whisper_model": cfg.WHISPER_MODEL,
        "llm_base_url": cfg.LLM_BASE_URL,
        "llm_model": cfg.LLM_MODEL
    })

@app.post("/analyze")
def analyze():
    """
    멀티파트: file (video/*)
    쿼리: lang (ko|en|... 선택, 미지정 시 Whisper 자동 감지)
    응답(JSON):
    {
      "format": "json",
      "duration": <float sec>,
      "segments": [{"start":..,"end":..,"text":".."}, ...],
      "chapters": [{"start":..,"end":..,"title":"..","summary":".."}, ...]
    }
    """
    lang = request.args.get("lang")
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400

    with tempfile.TemporaryDirectory() as td:
        suffix = pathlib.Path(f.filename).suffix or ".mp4"
        in_path = os.path.join(td, "input" + suffix)
        f.save(in_path)

        # 1) Whisper 자막 추출 (서비스로 분리)
        duration, segments = transcribe_file(
            file_path=in_path,
            language=lang,
            whisper_model=cfg.WHISPER_MODEL,
            use_fp16=cfg.WHISPER_FP16
        )

        # 2) gpt-oss-20b 챕터 생성 (서비스로 분리)
        chapters = []
        if segments:
            try:
                chapters = make_chapters(
                    segments=segments,
                    duration=duration,
                    lang=lang,
                    llm_base_url=cfg.LLM_BASE_URL,
                    llm_model=cfg.LLM_MODEL,
                    llm_api_key=cfg.LLM_API_KEY,
                    max_segments_for_prompt=cfg.MAX_SEGMENTS_FOR_PROMPT
                )
            except Exception as e:
                # LLM 실패해도 Whisper 결과는 반환
                app.logger.exception("chapterization failed: %s", e)
                chapters = []

        return jsonify({
            "format": "json",
            "duration": duration,
            "segments": segments,
            "chapters": chapters
        })

if __name__ == "__main__":
    # 운영에서는 debug=False 권장
    app.run(host="0.0.0.0", port=5001, debug=False)
