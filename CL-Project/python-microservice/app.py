from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import pathlib
import tempfile
import sys
import io
import subprocess
import hashlib

# ★ NEW: .env 파일 로드
from dotenv import load_dotenv
load_dotenv()

# Windows 한글 인코딩 문제 해결
if sys.platform == "win32":
    # 콘솔 출력을 UTF-8로 설정
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    # 환경변수 설정 - transformers 라이브러리 파일 읽기 오류 해결
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'  # Python 3.7+ UTF-8 모드 활성화

# CUDA 라이브러리 경로 설정
import nvidia.cublas
cublas_bin_path = os.path.join(os.path.dirname(nvidia.cublas.__file__), 'bin')
os.environ['PATH'] = cublas_bin_path + os.pathsep + os.environ['PATH']

from config import Settings
from services.transcriber import transcribe_file
from services.chapterizer import make_chapters_hf, _get_pipe, _extract_text

# (옵션) 원격(OpenAI 호환) 쓰는 경우 유지
# try:
#     from services.chapterizer_remote import make_chapters as make_chapters_remote
# except Exception:
#     make_chapters_remote = None

app = Flask(__name__)
CORS(app, origins=["http://localhost:8181", "http://127.0.0.1:8181", "http://localhost:8080", "http://127.0.0.1:8080"])  # CORS 활성화 (Spring Boot에서의 요청 허용)
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

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    app.logger.info(
        "POST /analyze from=%s lang=%s content_length=%s has_file=%s",
        client_ip, lang_query, request.content_length, bool(f)
    )
    
    # 디버깅을 위한 추가 로그
    print(f"\n=== 분석 요청 시작 ===")
    print(f"클라이언트 IP: {client_ip}")
    print(f"언어: {lang_query}")
    print(f"파일 존재: {bool(f)}")
    print(f"파일명: {f.filename if f else 'None'}")
    print(f"콘텐츠 길이: {request.content_length}")
    print(f"========================\n")

    if not f:
        app.logger.warning("no file field in request")
        return jsonify({"error": "no file"}), 400

    with tempfile.TemporaryDirectory() as td:
        suffix = pathlib.Path(f.filename).suffix or ".mp4"
        in_path = os.path.join(td, "input" + suffix)
        f.save(in_path)
        
        # 파일 저장 후 즉시 닫기
        f.close()

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
            
            # 터미널에 자막 추출 결과 출력
            print(f"\n[자막 추출 완료]")
            print(f"[영상 길이] {duration:.2f}초")
            print(f"[자막 구간 수] {len(segments)}개")
            print(f"[감지된 언어] {detected_lang}")
            print(f"\n[자막 내용 - 처음 5개 구간]")
            for i, seg in enumerate(segments[:5]):
                print(f"  {i+1}. [{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}")
            if len(segments) > 5:
                print(f"  ... 외 {len(segments)-5}개 구간")
            print()
            
        except Exception as e:
            app.logger.exception("transcription failed: %s", e)
            return jsonify({"error": "transcription failed", "detail": str(e)}), 500

        lang_for_chapter = (lang_query or detected_lang or "").lower()

        # print(segments)  # ★ CHANGED: 과도한 출력은 주석 처리(로그 폭주/성능 저하 방지)

        # 2) Chapters
        chapters = []
        if segments:
            try:
                app.logger.info(f"Starting chapterization with {len(segments)} segments")
                print(f"\n[챕터 분석 시작] (Llama-3.2-3B-Instruct 사용)")
                provider = (cfg.LLM_PROVIDER or "hf_local").lower()
                if provider == "hf_local":
                    chapters = make_chapters_hf(
                        segments=segments,
                        duration=duration,
                        lang=lang_for_chapter,
                        model_id=cfg.HF_MODEL_ID,
                        load_in_4bit=cfg.HF_LOAD_IN_4BIT,     # BitsAndBytesConfig 내부로만 반영됨 (경고 제거됨) ★ CHANGED
                        temperature=cfg.HF_TEMPERATURE,
                        max_new_tokens=cfg.HF_MAX_NEW_TOKENS,
                        max_segments_for_prompt=cfg.MAX_SEGMENTS_FOR_PROMPT,
                        hf_token=(cfg.HF_TOKEN or None),
                        # 메모리/오프로딩 전달
                        max_gpu_mem=cfg.HF_MAX_GPU_MEMORY,
                        max_cpu_mem=cfg.HF_MAX_CPU_MEMORY,
                        offload_dir=cfg.HF_OFFLOAD_DIR,
                        low_cpu_mem=cfg.HF_LOW_CPU_MEM,
                        torch_dtype_name=(cfg.HF_TORCH_DTYPE or "auto"),  # ★ CHANGED: 빈값 보호
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
                    print(f"[경고] 알 수 없는 LLM_PROVIDER: {provider}")
                    chapters = []
            except Exception as e:
                app.logger.exception("chapterization failed: %s", e)
                print(f"[오류] 챕터 분석 실패: {str(e)}")
                chapters = []

        # 3) 10초 미만의 짧은 챕터 필터링
        if chapters:
            original_count = len(chapters)
            MIN_CHAPTER_DURATION = 10.0  # 최소 챕터 길이 (초)
            
            filtered_chapters = []
            for ch in chapters:
                chapter_duration = ch.get('end', 0) - ch.get('start', 0)
                if chapter_duration >= MIN_CHAPTER_DURATION:
                    filtered_chapters.append(ch)
                else:
                    print(f"[필터링] 짧은 챕터 제거: '{ch.get('title', 'Unknown')}' ({chapter_duration:.1f}초)")
            
            chapters = filtered_chapters
            filtered_count = original_count - len(chapters)
            
            if filtered_count > 0:
                print(f"\n[챕터 필터링 완료]")
                print(f"  - 원본 챕터 수: {original_count}개")
                print(f"  - 제거된 챕터: {filtered_count}개 (10초 미만)")
                print(f"  - 최종 챕터 수: {len(chapters)}개\n")
                app.logger.info(f"Filtered out {filtered_count} chapters shorter than {MIN_CHAPTER_DURATION}s")

        return jsonify({
            "format": "json",
            "duration": duration,
            "segments": segments,
            "chapters": chapters,
            "detected_lang": detected_lang
        })

@app.post("/clip")
def clip_video():
    """영상 구간 자르기 API"""
    try:
        video_file = request.files.get("file")
        start_time = float(request.form.get("start", 0))
        end_time = float(request.form.get("end", 10))
        
        if not video_file:
            return jsonify({"error": "no file"}), 400
        
        # FFmpeg 경로 확인 (프로젝트 루트의 AudioModel 폴더)
        # 현재 파일: CL-Project/python-microservice/app.py
        # AudioModel: ai-proj/AudioModel
        current_dir = os.path.dirname(os.path.abspath(__file__))  # python-microservice
        project_root = os.path.dirname(os.path.dirname(current_dir))  # ai-proj
        ffmpeg_path = os.path.join(project_root, "AudioModel", "ffmpeg.exe")
        
        print(f"[영상 자르기] FFmpeg 경로: {ffmpeg_path}")
        print(f"[영상 자르기] FFmpeg 존재 여부: {os.path.exists(ffmpeg_path)}")
        
        if not os.path.exists(ffmpeg_path):
            return jsonify({"error": f"ffmpeg not found at {ffmpeg_path}"}), 500
        
        with tempfile.TemporaryDirectory() as td:
            # 입력 파일 저장
            suffix = pathlib.Path(video_file.filename).suffix or ".mp4"
            input_path = os.path.join(td, "input" + suffix)
            output_path = os.path.join(td, "output.mp4")
            
            video_file.save(input_path)
            video_file.close()
            
            # FFmpeg로 구간 자르기
            duration = end_time - start_time
            cmd = [
                ffmpeg_path,
                "-ss", str(start_time),
                "-i", input_path,
                "-t", str(duration),
                "-c", "copy",  # 재인코딩 없이 빠른 복사
                "-avoid_negative_ts", "make_zero",
                "-y",  # 덮어쓰기
                output_path
            ]
            
            print(f"\n[영상 자르기] {start_time}s ~ {end_time}s")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[오류] FFmpeg 실행 실패: {result.stderr}")
                return jsonify({"error": "ffmpeg failed", "detail": result.stderr}), 500
            
            print(f"[완료] 구간 영상 생성: {output_path}")
            
            # 파일을 메모리로 읽어서 전송 (파일 핸들 문제 해결)
            try:
                with open(output_path, 'rb') as f:
                    video_data = f.read()
                
                from flask import Response
                return Response(
                    video_data,
                    mimetype='video/mp4',
                    headers={
                        'Content-Disposition': f'inline; filename="clip_{start_time}_{end_time}.mp4"',
                        'Content-Length': str(len(video_data))
                    }
                )
            except Exception as read_error:
                print(f"[오류] 파일 읽기 실패: {read_error}")
                return jsonify({"error": "file read failed", "detail": str(read_error)}), 500
            
    except Exception as e:
        print(f"[오류] 영상 자르기 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.post("/explain")
def explain_chapter():
    """챕터 구간에 대한 상세 설명 생성 API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "no JSON data"}), 400
        
        segments = data.get("segments", [])
        start_time = float(data.get("start", 0))
        end_time = float(data.get("end", 0))
        lang = data.get("lang", "ko")
        
        print(f"\n[상세 설명 요청]")
        print(f"  - 구간: {start_time}s ~ {end_time}s")
        print(f"  - 언어: {lang}")
        print(f"  - 전체 세그먼트 수: {len(segments)}")
        
        if not segments:
            return jsonify({"error": "no segments provided"}), 400
        
        # LLM 파이프라인 로드
        pipe = _get_pipe(
            model_id=cfg.HF_MODEL_ID,
            load_in_4bit=cfg.HF_LOAD_IN_4BIT,
            temperature=0.35,
            max_new_tokens=400,
            hf_token=cfg.HF_TOKEN,
            max_gpu_mem=cfg.HF_MAX_GPU_MEMORY,
            max_cpu_mem=cfg.HF_MAX_CPU_MEMORY,
            offload_dir=cfg.HF_OFFLOAD_DIR,
            low_cpu_mem=cfg.HF_LOW_CPU_MEM,
            torch_dtype_name=cfg.HF_TORCH_DTYPE or "auto"
        )
        
        if pipe is None:
            return jsonify({"error": "LLM pipeline initialization failed"}), 500
        
        # ★ explainer 모듈 사용
        from services.explainer import generate_explanation
        
        print(f"\n[LLM 상세 설명 생성 시작]")
        explanation = generate_explanation(
            segments=segments,
            start_time=start_time,
            end_time=end_time,
            lang=lang,
            pipe=pipe,
            _extract_text=_extract_text
        )
        
        print(f"\n[상세 설명 생성 완료]\n")
        
        return jsonify({
            "explanation": explanation,
            "segment_count": len(segments)
        })
        
    except Exception as e:
        print(f"[오류] 상세 설명 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.post("/chat")
def chat():
    """AI Agent 챗봇 - RAG 기반 질의응답"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "no JSON data"}), 400
        
        stored_name = data.get("stored_name")
        segments = data.get("segments", [])
        question = data.get("question")
        lang = data.get("lang", "ko")
        
        print(f"\n[챗봇 질문]")
        print(f"  - stored_name: {stored_name}")
        print(f"  - question: {question}")
        print(f"  - lang: {lang}")
        print(f"  - segments: {len(segments)}개")
        
        if not stored_name:
            return jsonify({"error": "stored_name is required"}), 400
        
        if not question:
            return jsonify({"error": "question is required"}), 400
        
        if not segments:
            return jsonify({"error": "segments is required"}), 400
        
        # LLM 파이프라인 로드
        pipe = _get_pipe(
            model_id=cfg.HF_MODEL_ID,
            load_in_4bit=cfg.HF_LOAD_IN_4BIT,
            temperature=0.5,
            max_new_tokens=300,
            hf_token=cfg.HF_TOKEN,
            max_gpu_mem=cfg.HF_MAX_GPU_MEMORY,
            max_cpu_mem=cfg.HF_MAX_CPU_MEMORY,
            offload_dir=cfg.HF_OFFLOAD_DIR,
            low_cpu_mem=cfg.HF_LOW_CPU_MEM,
            torch_dtype_name=cfg.HF_TORCH_DTYPE or "auto"
        )
        
        if pipe is None:
            return jsonify({"error": "LLM pipeline initialization failed"}), 500
        
        # Simple QA
        from services.agent_service import create_simple_qa
        result = create_simple_qa(pipe, stored_name, segments, question, lang)
        
        print(f"\n[챗봇 응답 완료]")
        print(f"  - answer: {result['answer'][:100]}...")
        
        return jsonify(result)
    
    except Exception as e:
        print(f"[오류] 챗봇 응답 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "answer": f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}",
            "sources": [],
            "thinking_steps": [],
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
