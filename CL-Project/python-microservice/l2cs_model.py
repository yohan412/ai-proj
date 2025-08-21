# l2cs_model.py
import os
from typing import Optional, Dict, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms
import numpy as np
from PIL import Image

# -------------------
# 설정(환경변수로 오버라이드 가능)
# -------------------
L2CS_WEIGHTS = os.environ.get("L2CS_WEIGHTS", "models/L2CSNet_gaze360.pkl")
L2CS_DEVICE  = os.environ.get("L2CS_DEVICE",  "cuda" if torch.cuda.is_available() else "cpu")
# 일부 체크포인트는 224, 일부는 448 입력을 기대합니다.
L2CS_INPUT_SIZE = int(os.environ.get("L2CS_INPUT_SIZE", "224"))
# InsightFace RetinaFace 입력 크기
L2CS_DET_W = int(os.environ.get("L2CS_DET_W", "320"))
L2CS_DET_H = int(os.environ.get("L2CS_DET_H", "320"))
# 얼굴 크롭 시 여유 비율
CROP_MARGIN = float(os.environ.get("L2CS_CROP_MARGIN", "0.25"))

# -------------------
# L2CS-Net 정의
#  - 분류(66 bins, 3° 간격) 기대값으로 각도 회귀
# -------------------
NUM_BINS = 66
BIN_SIZE_DEG = 3
BIN_MIN_DEG = -99
IDX_TENSOR = torch.arange(0, NUM_BINS, dtype=torch.float32)

class L2CSNet(nn.Module):
    def __init__(self, backbone: str = "resnet50", pretrained: bool = False):
        super().__init__()
        if backbone != "resnet50":
            raise ValueError("Only resnet50 is supported in this minimal impl.")
        base = models.resnet50(weights=models.ResNet50_Weights.DEFAULT if pretrained else None)
        feat_dim = base.fc.in_features
        base.fc = nn.Identity()
        self.backbone = base
        self.fc_yaw = nn.Linear(feat_dim, NUM_BINS)
        self.fc_pitch = nn.Linear(feat_dim, NUM_BINS)

    def forward(self, x):
        feat = self.backbone(x)
        yaw_logits = self.fc_yaw(feat)
        pitch_logits = self.fc_pitch(feat)
        return yaw_logits, pitch_logits

def _logits_to_deg(yaw_logits: torch.Tensor, pitch_logits: torch.Tensor, device: str) -> Tuple[float, float]:
    idx = IDX_TENSOR.to(device)
    yaw_prob = F.softmax(yaw_logits, dim=1)
    pitch_prob = F.softmax(pitch_logits, dim=1)
    yaw = torch.sum(yaw_prob * idx, dim=1) * BIN_SIZE_DEG + BIN_MIN_DEG
    pitch = torch.sum(pitch_prob * idx, dim=1) * BIN_SIZE_DEG + BIN_MIN_DEG
    return yaw.item(), pitch.item()

def _crop_with_margin(img_np: np.ndarray, bbox, margin: float = CROP_MARGIN) -> np.ndarray:
    # bbox = [x1,y1,x2,y2]
    h, w = img_np.shape[:2]
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * margin), int(bh * margin)
    nx1 = max(0, int(x1) - mx)
    ny1 = max(0, int(y1) - my)
    nx2 = min(w, int(x2) + mx)
    ny2 = min(h, int(y2) + my)
    return img_np[ny1:ny2, nx1:nx2, :]

class GazeEngine:
    """
    - FaceAnalysis(InsightFace)로 얼굴 검출
    - L2CS-Net으로 yaw/pitch 추정
    - PIL.Image(RGB) 입력 → dict(yaw, pitch) 출력
    """
    def __init__(self,
                 weights_path: str = L2CS_WEIGHTS,
                 device: str = L2CS_DEVICE,
                 input_size: int = L2CS_INPUT_SIZE,
                 det_size: Tuple[int, int] = (L2CS_DET_W, L2CS_DET_H)):
        self.device = device
        self.input_size = input_size
        self.det_size = det_size

        # 얼굴 검출기
        from insightface.app import FaceAnalysis
        self.face_app = FaceAnalysis(name="buffalo_l")
        # ctx_id=-1: CPU. GPU 사용 시 0으로.
        ctx_id = -1 if device == "cpu" else 0
        self.face_app.prepare(ctx_id=ctx_id, det_size=det_size)

        # 모델 로드
        self.model = L2CSNet("resnet50", pretrained=False).to(self.device)
        state = torch.load(weights_path, map_location=self.device)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        new_state = {}
        for k, v in state.items():
            nk = k[7:] if k.startswith("module.") else k
            new_state[nk] = v
        self.model.load_state_dict(new_state, strict=False)
        self.model.eval()

        # 전처리 파이프라인
        self.transform = transforms.Compose([
            transforms.Resize((self.input_size, self.input_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]),
        ])

    @torch.inference_mode()
    def infer_from_pil(self, rgb_img: Image.Image) -> Optional[Dict[str, float]]:
        """
        Args:
            rgb_img: PIL.Image in RGB
        Returns:
            {"yaw": float, "pitch": float} or None (no face)
        """
        np_img = np.array(rgb_img)  # RGB
        # InsightFace는 BGR 기준이 일반적 → 채널 반전
        bgr = np_img[:, :, ::-1]
        faces = self.face_app.get(bgr)
        if not faces:
            return None

        # 가장 큰 얼굴로 선택
        faces.sort(key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]), reverse=True)
        f = faces[0]
        crop = _crop_with_margin(np_img, f.bbox, margin=CROP_MARGIN)  # RGB crop
        pil_crop = Image.fromarray(crop).convert("RGB")

        x = self.transform(pil_crop).unsqueeze(0).to(self.device)
        yaw_logits, pitch_logits = self.model(x)
        yaw_deg, pitch_deg = _logits_to_deg(yaw_logits, pitch_logits, self.device)

        return {"yaw": yaw_deg, "pitch": pitch_deg}

    def health(self) -> Dict[str, str]:
        return {
            "status": "ok",
            "device": self.device,
            "input_size": str(self.input_size),
            "det_size": f"{self.det_size[0]}x{self.det_size[1]}",
        }

# 모듈 import 시 바로 엔진을 구성하려면 아래 사용 (원하면 지워도 됨)
# ENGINE = GazeEngine()
