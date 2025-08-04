import os
import torch
import numpy as np
from core.craft import imgproc
from core.craft import craft_utils
from torch.autograd import Variable
from PIL import Image, ImageFont, ImageDraw, ImageOps
import cv2
from itertools import groupby
from operator import itemgetter
from core.craft.craft import CRAFT
from core.craft.craft_utils import getDetBoxes
from easyocr import Reader as EasyOCRReader
from collections import OrderedDict
import re
from core.craft.time_scaling import time_from_filename as tff
from core.craft.time_scaling import get_fps_opencv as gfps
from core.craft.text_scaling import sort_by_timestamp as sbt
from core.craft.text_scaling import blob_to_segments as bts
from pathlib import Path
import paddle
from paddleocr import PaddleOCR

"""
conda 가상환경 Python 3.10.1
OCR 파이프라인 (KOR/ENG 텍스트 + 수식)
· CRAFT → 텍스트 영역 검출
· EasyOCR / TrOCR / Pix2Text → 내용 추출
· 좌우 패널 합성해 ./outputs 에 시각화 저장 (한글 렌더링 지원)
"""

# ───────────────────────────────────────────────────────────────
# 0. 설정
# ───────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent

device      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
upload_dir  = BASE.parent.parent.parent / "uploads"
image_dir   = upload_dir / "images"                 # 입력 이미지 폴더
output_dir  = upload_dir / "outputs"                # 결과 저장 폴더
font_path   = BASE / "fonts/malgun.ttf"  # 한글 지원 TTF (경로 수정 가능)

# os.makedirs(output_dir, exist_ok=True)

print("[INFO] CUDA 사용 가능 여부:", torch.cuda.is_available())
print("[INFO] 현재 사용중인 디바이스:", device)
print("[INFO] GPU 이름:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A")

# ───────────────────────────────────────────────────────────────
# 1. CRAFT 로드
# ───────────────────────────────────────────────────────────────

craft_model = CRAFT().to(device)
state_dict  = torch.load(BASE / "weights/craft_mlt_25k.pth", map_location=device)
state_dict  = OrderedDict((k.replace("module.", ""), v) for k, v in state_dict.items())
craft_model.load_state_dict(state_dict)
craft_model.eval()

# ───────────────────────────────────────────────────────────────
# 2. 전처리 / 유틸리티
# ───────────────────────────────────────────────────────────────

def detect_text_boxes(image_rgb: np.ndarray):
    """CRAFT 박스 검출"""
    img_resized, target_ratio, _ = imgproc.resize_aspect_ratio(
        image_rgb, square_size=1280, interpolation=cv2.INTER_LINEAR, mag_ratio=1.5)
    ratio_h = ratio_w = 1 / target_ratio

    tensor = imgproc.normalizeMeanVariance(img_resized)
    tensor = torch.from_numpy(tensor).permute(2, 0, 1)
    tensor = Variable(tensor.unsqueeze(0)).to(device)

    with torch.no_grad():
        y, _ = craft_model(tensor)
    region_score   = y[0, :, :, 0].cpu().data.numpy()
    affinity_score = y[0, :, :, 1].cpu().data.numpy()

    boxes, _ = getDetBoxes(region_score, affinity_score,
                           text_threshold=0.5, link_threshold=0.2, low_text=0.2)
    boxes = craft_utils.adjustResultCoordinates(boxes, ratio_w, ratio_h)
    return boxes if boxes is not None else []

# ───────────────────────────────────────────────────────────────
# 3. OCR 분류/실행
# ───────────────────────────────────────────────────────────────

ocr_reader = EasyOCRReader(['en', 'ko'])

use_gpu = paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
ocr_eng = PaddleOCR(
    det_model_name="PP-OCRv5_server_det",
    rec_model_name="PP-OCRv5_server_rec",
    use_angle_cls=True,
    use_gpu=use_gpu,
)

# ocr_kor = PaddleOCR(
#     det_model_name="PP-OCRv5_server_det model",
#     rec_model_name="korean_PP-OCRv5_mobile_rec",
#     use_angle_cls=True,
#     lang="korean",
#     use_gpu=use_gpu,
# )

MATH_TOKENS = r"[0-9\+\-\=\*/\^_%√∑∫∞π≈≠≤≥<>⋅×÷∂∇(){}\[\]|\\]"
MATH_RE    = re.compile(MATH_TOKENS)
MULTI_CHAR = re.compile(r"\S{3,}")
BOX_PAD = 3

def classify_box_text(full_pil: Image.Image, box: np.ndarray, math_first=True) -> str:
      
    raw_x1, raw_y1 = map(int, box.min(axis=0)); raw_x2, raw_y2 = map(int, box.max(axis=0))
    img_w, img_h = full_pil.size
    x1 = max(0, raw_x1 - BOX_PAD); y1 = max(0, raw_y1 - BOX_PAD)
    x2 = min(img_w - 1, raw_x2 + BOX_PAD); y2 = min(img_h - 1, raw_y2 + BOX_PAD)
    crop_pil = full_pil.crop((x1, y1, x2, y2))
    texts = ocr_reader.readtext(np.array(crop_pil), detail=0)
    text  = texts[0] if texts else ""

    if len(text) < 1:
        return "unknown"

    digits = sum(ch.isdigit() for ch in text)
    alpha  = sum(ch.isalpha() for ch in text)

    if any('\uac00' <= ch <= '\ud7af' for ch in text):
        return "kor"
    elif alpha / len(text) >= 0.6:
        return "eng"
    elif math_first:
        if MATH_RE.search(text):
            return "eng"
        if MULTI_CHAR.match(text) and digits / len(text) >= 0.4:
            return "eng"

    return "unknown"

# 수식판별 -> latex
# from pix2text import Pix2Text
# p2t = Pix2Text(device="cuda" if torch.cuda.is_available() else "cpu")


# def run_math_ocr(crop: Image.Image) -> str:
#     latex = p2t.recognize(crop, return_format='latex').strip().replace(' ', '')
#     if latex.startswith("$"):
#         latex = latex.strip("$").strip()
#     return latex


def run_ocr_by_type(crop: Image.Image, typ: str) -> str:

    proc = preprocess_crop(
        crop,
        deskew      = False,
        upscale     = True,     # 자동 조건(upscale_if_h)만 사용
        upscale_if_h= 24,
        blur_sigma  = 0.3,
        thicken     = True,
        std_thresh  = 20,
        dilate_iter = 3
    )

    if typ == "eng":
        result = ocr_eng.ocr(np.array(proc), cls=False)
        if result and result[0]:
            return result[0][0][1][0]
        return ""
    elif typ == "kor":
        # ocr_reader2 = EasyOCRReader(['ko'])
        t = ocr_reader.readtext(np.array(proc), 
                                 detail=0,
                                 contrast_ths     = 0.4,   # 배경·글자 대비 임계값
                                 adjust_contrast  = 0.6   # 대비 자동 강화 정도
                                 )
        return t[0].strip() if t else ""
        # result = ocr_kor.ocr(np.array(proc), cls=False)
        # if result and result[0]:
        #     return result[0][0][1][0]
        # return ""
    # elif typ == "math":
    #     return run_math_ocr(crop) 
    return ""

# ───────────────────────────────────────────────────────────────
# 4. 한글 렌더링용 폰트 로드
# ───────────────────────────────────────────────────────────────

# try:
#     DEFAULT_FONT = ImageFont.truetype(font_path, size=16)
# except Exception as e:
#     print(f"[경고] 폰트 로드 실패: {e} → 기본 폰트 사용(한글 미지원 가능)")
#     DEFAULT_FONT = ImageFont.load_default()

# ───────────────────────────────────────────────────────────────
# 5. 결과 이미지 합성 (테스트용)
# ───────────────────────────────────────────────────────────────

# def save_composite(orig_bgr: np.ndarray, box_results: list, out_path: str):
#     """box_results = [(x1,y1,x2,y2,text), ...]"""
#     left  = orig_bgr.copy()
#     for x1, y1, x2, y2, _ in box_results:
#         cv2.rectangle(left, (x1, y1), (x2, y2), (0, 255, 0), 2)

#     right_np  = np.ones_like(left, dtype=np.uint8) * 255
#     right_pil = Image.fromarray(cv2.cvtColor(right_np, cv2.COLOR_BGR2RGB))
#     draw      = ImageDraw.Draw(right_pil)

#     for x1, y1, x2, y2, txt in box_results:
#         draw.rectangle([(x1, y1), (x2, y2)], outline=(0, 0, 0), width=2)
#         draw.multiline_text((x1 + 3, y1 + 3), txt, font=DEFAULT_FONT, fill=(0, 0, 0))

#     right_np = cv2.cvtColor(np.array(right_pil), cv2.COLOR_RGB2BGR)
#     comp = np.hstack([left, right_np])
#     cv2.imwrite(out_path, comp)
    # print(f"[저장] {out_path}")

def preprocess_crop(
    pil: Image.Image,
    *,
    # ───────── 기본 파라미터 ─────────
    min_h:        int  = 32,
    pad:          int  = 4,
    deskew:       bool = False,
    # ────── 스트로크 조건부 팽창 ──────
    thicken:      bool = False,
    std_thresh:   int  = 15,
    dilate_iter:  int  = 1,
    # ──── 초저해상도 업스케일+블러 ────
    upscale:      bool = False,   # True → 무조건 ×2 업스케일
    upscale_if_h: int  = 30,      # h ≤ 이 값일 때만 자동 업스케일
    blur_sigma:   float = 0.3     # 업스케일 뒤 가우시안 블러(픽셀) 0 = off
) -> Image.Image:
    """
    ▸ 컬러 유지 + 최소 리사이즈 + 패딩 + (선택)deskew
    ▸ (선택) 초저해상도인 경우 2× 업스케일 + 미세 블러
    ▸ (선택) 얇은 획 감지 시 살짝 팽창
    """
    # ── 0) EXIF 회전 ───────────────────────────────
    pil = ImageOps.exif_transpose(pil)
    img = np.array(pil.convert("RGB"))
    h, w = img.shape[:2]

    # ── 1) (선택) Deskew ──────────────────────────
    if deskew:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        thr  = cv2.threshold(gray, 0, 255,
                             cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thr > 0))
        if len(coords):
            ang = cv2.minAreaRect(coords)[-1]
            ang = -(90 + ang) if ang < -45 else -ang
            if abs(ang) >= 1:
                M = cv2.getRotationMatrix2D((w//2, h//2), ang, 1.0)
                img = cv2.warpAffine(img, M, (w, h),
                                     flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)
                h, w = img.shape[:2]

    # ── 2) 최소 높이 확보 ──────────────────────────
    if h < min_h:
        scale = min_h / h
        img   = cv2.resize(img, (int(w * scale), min_h),
                           interpolation=cv2.INTER_CUBIC)
        h, w  = img.shape[:2]

    # ── 3) (옵션) 업스케일 ×2 + 미세 블러 ──────────
    if upscale or h <= upscale_if_h:
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        if blur_sigma > 0:
            img = cv2.GaussianBlur(img, (0, 0), blur_sigma)
        h, w = img.shape[:2]

    # ★★★ 추가: ‘유독 작은’ 박스 추가 확대 ★★★
    tiny_h      = 100     # h ≤ tiny_h → 너무 작은 글씨로 간주
    tiny_target = 164     # 최소 목표 높이
    if h <= tiny_h:
        # 필요한 배율 = tiny_target / 현재 높이  (최소 2× 보장)
        scale = max(2, int(np.ceil(tiny_target / h)))
        img   = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        # 선택적 블러(alias 제거) – 작은 글씨는 σ≈0.4 권장
        img   = cv2.GaussianBlur(img, (0, 0), 0.4)
        h, w  = img.shape[:2]

    # ── 4) 패딩 ────────────────────────────────────
    img = cv2.copyMakeBorder(img, pad, pad, pad, pad,
                             cv2.BORDER_CONSTANT, value=[255, 255, 255])

    # ── 5) (선택) 스트로크 조건부 팽창 ──────────────
    if thicken and dilate_iter > 0:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        if gray.std() <= std_thresh:               # ‘얇은 글자’로 판단
            edges = cv2.Canny(gray, 60, 180)
            k     = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.dilate(edges, k, iterations=dilate_iter)
            img[edges > 0] = [0, 0, 0]

    return Image.fromarray(img).convert("RGB")

# ───────────────────────────────────────────────────────────────
# 6. 메인 루프
# ───────────────────────────────────────────────────────────────

def str_print(video_name):

    results = []
    # Construct the full path to the video file.
    # The 'video_name' parameter (e.g., "Jimmy_englishvideo") is the base name for the video file.
    video_path = upload_dir / f"{video_name}.mp4"
    
    # Check if the video file exists before proceeding.
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")
        
    # Get the frames per second (fps) of the video once.
    fps = gfps(str(video_path))

    for img_name in [f for f in os.listdir(image_dir) if video_name in f]:
        if not img_name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        img_path = os.path.join(image_dir, img_name)
        bgr = cv2.imread(img_path)
        if bgr is None:
            print(f"[경고] 이미지 로드 실패: {img_path}")
            continue

        rgb = imgproc.loadImage(img_path)
        pil = Image.fromarray(rgb)

        boxes = detect_text_boxes(rgb)

        if len(boxes) == 0:
            print(f"[정보] 박스 없음 → {img_name}")
            continue

        box_results = []
        for box in boxes:
            typ = classify_box_text(pil, box)
            raw_x1, raw_y1 = map(int, box.min(axis=0)); raw_x2, raw_y2 = map(int, box.max(axis=0))
            img_w, img_h = pil.size
            x1 = max(0, raw_x1 - BOX_PAD); y1 = max(0, raw_y1 - BOX_PAD)
            x2 = min(img_w - 1, raw_x2 + BOX_PAD); y2 = min(img_h - 1, raw_y2 + BOX_PAD)
            crop = pil.crop((x1, y1, x2, y2))
            text = run_ocr_by_type(crop, typ)
            # box_results.append((x1, y1, x2, y2, text))
            results.append((img_name, typ, text, (x1, y1)))

        # save_composite(bgr, box_results, os.path.join(output_dir, f"{os.path.splitext(img_name)[0]}_result.jpg"))

    # ───────────────────────────────────────────────────────────────
    # 7. 콘솔 요약 출력 (Y‑좌표 기반 행 클러스터링)
    # ───────────────────────────────────────────────────────────────

    # (1) 이미지별로 결과 묶기 ──────────────────────────────────
    if not results:
        print("[⚠️] 결과 없음: 박스를 찾지 못함 또는 OCR 실패")
        exit()

    # ➊ 정렬: 이미지 → y → x
    results.sort(key=lambda r: (r[0], r[3][1], r[3][0]))

    res = {}
    res_v = []

    for img_name, group in groupby(results, key=itemgetter(0)):
        group = list(group)

        # (2) 각 박스의 상단 y 좌표 리스트
        y_vals = sorted([rec[3][1] for rec in group])
        if len(y_vals) >= 2:
            # 두 y 사이 차이들의 중앙값 → 행 분리 기준
            y_diffs = [b - a for a, b in zip(y_vals[:-1], y_vals[1:])]
            med_diff = np.median(y_diffs)
            delta = max(10, int(med_diff * 0.5))  # 최소 10px, 중앙값 50%
        else:
            delta = 15  # 박스 한 개면 임의값

        # (3) y 좌표 오름차순으로 행 클러스터링
        group_sorted = sorted(group, key=lambda r: r[3][1])
        rows = []  # [[rec, rec, ...], ...]
        for rec in group_sorted:
            y = rec[3][1]
            if not rows:
                rows.append([rec])
                continue
            # 현재 행의 기준 y (첫 박스의 y)
            base_y = rows[-1][0][3][1]
            if abs(y - base_y) <= delta:
                rows[-1].append(rec)
            else:
                rows.append([rec])

        # (4) 행별 x 좌표로 정렬 후 출력
        
        print(f"■■ {img_name} = {tff(img_name,fps)} ->")
        for row in rows:
            line = sorted(row, key=lambda r: r[3][0])
            # print(' '.join(r[2] for r in line))
            res_v.append(' '.join(r[2] for r in line))

        res[tff(img_name,fps)] = ' '.join(res_v)
        res_v = []
        # for k in res.keys():
            # print(f"{k} = {' '.join(res[k])}")

    return bts(sbt(res))
    
