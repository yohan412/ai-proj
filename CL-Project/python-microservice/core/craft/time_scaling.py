import re
from datetime import timedelta
import cv2

def time_from_filename(filename: str, fps: float = 5.0) -> float:
    """
    frame_{count}.jpg  ➜  초(실수) 단위로 변환

    예) 'video_123.jpg', fps=5  →  24.6   (123 ÷ 5)
    """
    m = re.search(r"_(\d+)\.jpg$", filename)
    if not m:
        raise ValueError(f"잘못된 파일 이름: {filename}")

    frame_idx = int(m.group(1))
    return frame_idx / fps 

def get_fps_opencv(path: str) -> float:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise IOError(f"열 수 없는 파일: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS)   # 고정 FPS(CFR)일 때만 정확
    cap.release()
    return fps