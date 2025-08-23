# CUDA + PyTorch가 포함된 공식 런타임 이미지
FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

# 시스템 패키지: ffmpeg(영상→오디오), git, build-essential 등
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git build-essential gcc g++ \
 && rm -rf /var/lib/apt/lists/*

# 워킹 디렉터리
WORKDIR /app

# 파이썬 의존성
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 앱 코드
COPY . /app

# HF/Transformers 캐시와 오프로딩/모델 폴더
ENV HF_HOME=/cache/hf \
    TRANSFORMERS_CACHE=/cache/hf \
    HF_DATASETS_CACHE=/cache/hf \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:64

# 업로드/오프로딩/캐시/모델 볼륨 경로
VOLUME ["/cache", "/offload", "/models"]

# 포트
EXPOSE 5001

# Gunicorn: 1 worker(중요: LLM VRAM 중복 방지), gthread로 긴 작업 대응, 타임아웃 여유
# --threads 4 정도만, 필요하면 조정하되 worker=1 권장
CMD ["bash", "-lc", "gunicorn -w 1 --threads 4 -k gthread -t 900 -b 0.0.0.0:5001 app:app"]
