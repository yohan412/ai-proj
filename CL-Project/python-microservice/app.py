# app.py
import io, base64, time
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS

from l2cs_model import GazeEngine   # 모든 로직은 이쪽으로 위임

app = Flask(__name__)
CORS(app)

# 엔진 초기화 (가중치/디바이스/입력 크기/검출 크기는 l2cs_model.py의 환경변수로 제어)
ENGINE = GazeEngine()

@app.get("/health")
def health():
    return jsonify(ENGINE.health())

@app.post("/infer")
def infer():
    """
    입력(JSON):
      { "imageBase64": "<base64 jpeg/png payload (data-url prefix 없이)>" }

    출력(JSON):
      - 성공: { "yaw": <float>, "pitch": <float>, "latency_ms": <int> }
      - 얼굴 X: { "message": "no_face", "latency_ms": <int> }
      - 오류:  { "error": "...", "detail": "..." }
    """
    t0 = time.time()
    data = request.get_json(silent=True) or {}
    b64 = data.get("imageBase64")
    if not b64:
        return jsonify({"error": "imageBase64 required"}), 400

    try:
        img_bytes = base64.b64decode(b64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        return jsonify({"error": "decode_failed", "detail": str(e)}), 400

    try:
        out = ENGINE.infer_from_pil(img)
        latency = int((time.time() - t0) * 1000)
        if out is None:
            return jsonify({"message": "no_face", "latency_ms": latency})
        out["latency_ms"] = latency
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": "inference_failed", "detail": str(e)}), 500

if __name__ == "__main__":
    # 환경변수 예시:
    #  export L2CS_WEIGHTS=models/L2CSNet_gaze360.pkl
    #  export L2CS_INPUT_SIZE=224
    #  export L2CS_DEVICE=cuda
    #  export L2CS_DET_W=320; export L2CS_DET_H=320
    app.run(host="0.0.0.0", port=8001)
