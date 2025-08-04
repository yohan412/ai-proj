import os
import numpy as np
import cv2
from craft_utils import generate_target  # CRAFT에서 제공하거나 커스텀 구현 필요
from imgproc import loadImage            # 이미지 전처리 및 로딩 함수

# 경로 설정
image_dir = "./images/"
label_dir = "./annotations_txt/"
output_dir = "./gt_npy/"
os.makedirs(output_dir, exist_ok=True)

def parse_annotation(txt_path):
    """gt 텍스트 파일을 polygon + 텍스트로 파싱"""
    polygons = []
    # texts = []
    with open(txt_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 9:
                continue
            coords = list(map(float, parts[:8]))
            text = ",".join(parts[8:])
            polygon = np.array(coords, dtype=np.float32).reshape((4, 2))
            polygons.append(polygon)
            # texts.append(text)
    # return np.array(polygons), texts
    return np.array(polygons)

# 이미지 순회하며 .npy GT 생성
for fname in os.listdir(image_dir):
    if not fname.lower().endswith(('.jpg', '.png', '.jpeg')):
        continue

    image_path = os.path.join(image_dir, fname)
    label_path = os.path.join(label_dir, f"{os.path.splitext(fname)[0]}.txt")
    output_path = os.path.join(output_dir, f"{os.path.splitext(fname)[0]}.npy")

    if not os.path.exists(label_path):
        print(f"[경고] 라벨 파일 없음: {label_path}")
        continue

    image = loadImage(image_path)
    # polygons, texts = parse_annotation(label_path)
    polygons = parse_annotation(label_path)

    region, affinity, confidence_mask = generate_target(image, polygons)

    np.save(output_path, {
        "region": region,
        "affinity": affinity,
        "confidence": confidence_mask
    })

    print(f"저장 완료: {output_path}")
