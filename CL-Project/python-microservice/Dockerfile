FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
SHELL ["/bin/bash","-lc"]

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/hf \
    PIP_CACHE_DIR=/pipcache

# OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv \
      ca-certificates curl git ffmpeg \
      build-essential python3-dev ninja-build jq \
    && rm -rf /var/lib/apt/lists/*
ENV CC=gcc CXX=g++

# paths
RUN mkdir -p /app /models/hf /offload /pipcache && chmod -R 777 /models/hf /offload /pipcache
WORKDIR /app

# requirements (app deps만 먼저)
COPY requirements.txt .
RUN awk 'BEGIN{IGNORECASE=1} \
  !/^(torch|torchvision|torchaudio|transformers|accelerate|bitsandbytes|triton|nvidia-cudnn-cu12)\b/' \
  requirements.txt > requirements.app.txt \
 && python3 -m pip install --upgrade pip \
 && python3 -m pip install --no-cache-dir -r requirements.app.txt

# 혹시 섞여 깔린 torch류 제거
RUN python3 -m pip uninstall -y torch torchvision torchaudio || true

# PyTorch stack (CUDA 12.4 빌드, 버전 고정)
RUN python3 -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu124 \
      torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1

# HF stack 고정 + cuDNN 파이썬 패키지
RUN python3 -m pip install --no-cache-dir --no-deps \
      transformers==4.44.2 accelerate==0.33.0 \
      bitsandbytes==0.44.1 triton==2.3.1 \
 && python3 -m pip install --no-cache-dir 'nvidia-cudnn-cu12>=9.1,<9.2' \
 && CUDNN_LIB_DIR=$(python3 -c "import os, nvidia.cudnn as c; print(os.path.join(os.path.dirname(c.__file__),'lib'))") \
 && echo "export LD_LIBRARY_PATH=${CUDNN_LIB_DIR}:\$LD_LIBRARY_PATH" >/etc/profile.d/cudnn.sh

# 빌드 타임 검증
RUN python3 - <<'PY'
import importlib, torch, torchvision, torchaudio, transformers, bitsandbytes, triton, sys
print("torch:", torch.__version__, "cuda:", torch.version.cuda)
print("torchvision:", torchvision.__version__)
print("torchaudio:", torchaudio.__version__)
print("transformers:", transformers.__version__)
print("bitsandbytes:", bitsandbytes.__version__)
print("triton:", triton.__version__)
ok = True
if torch.__version__.split('+')[0] != "2.4.1": ok=False
if not torch.version.cuda or not torch.version.cuda.startswith("12.4"): ok=False
if not importlib.util.find_spec('torch._custom_ops'): ok=False
sys.exit(0 if ok else 2)
PY

# app
COPY . .

EXPOSE 5001
CMD ["bash","-lc","source /etc/profile.d/cudnn.sh 2>/dev/null || true; gunicorn -w 1 -k gthread --threads 1 --timeout 600 --graceful-timeout 30 --keep-alive 120 -b 0.0.0.0:5001 app:app"]
