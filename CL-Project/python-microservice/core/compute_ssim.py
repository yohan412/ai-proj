import os
import sys, json, base64
import cv2
from skimage.metrics import structural_similarity as ssim
from core.mk_frame import mk_frame as mf
from core.craft import str_print as cs
from config import UPLOADS_DIR, IMAGES_DIR

def compute_ssim(img1, img2):
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(gray1, gray2, full=True)
    return score

def get_sorted_frame_paths(frame_dir: str, prefix: str):
    files = [
        f for f in os.listdir(frame_dir)
        if f.startswith(prefix) and f.endswith(".jpg")
    ]
    files.sort(key=lambda x: int(x.rsplit('_', 1)[1].split('.')[0]))
    return [os.path.join(frame_dir, f) for f in files]

def remove_similar_frames(video_name: str,
                          frame_dir: str = IMAGES_DIR,
                          threshold: float = 0.95,
                          start_time: float = None,
                          end_time: float = None):
    """
    video_name: The name of the original file (without extension).
    start_time, end_time: Optional start and end times for segment analysis.
    """
    # 영상을 프레임 이미지로 변환 함수
    mf(video_name, start_time=start_time, end_time=end_time)

    prefix = f"{video_name}_"
    paths = get_sorted_frame_paths(frame_dir, prefix)
    if not paths:
        print("No frames found.")
        return

    prev_img = cv2.imread(paths[0])
    kept_count = 1
    min_chk = 1.0

    for path in paths[1:]:
        curr_img = cv2.imread(path)
        if curr_img is None:
            continue

        similarity = compute_ssim(prev_img, curr_img)
        if similarity >= threshold:
            os.remove(path)
        else:
            if similarity < min_chk:
                min_chk = similarity
            prev_img = curr_img
            kept_count += 1

if __name__ == "__main__":
    video_name = sys.argv[1]
    start_time = float(sys.argv[2]) if len(sys.argv) > 2 else None
    end_time = float(sys.argv[3]) if len(sys.argv) > 3 else None

    remove_similar_frames(
        video_name=video_name,
        frame_dir=IMAGES_DIR,
        threshold=0.75,
        start_time=start_time,
        end_time=end_time
    )
    
    stamp_text = cs.str_print(video_name)

    result = {"data": stamp_text}
    
    payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
    print(base64.b64encode(payload).decode(), flush=True)

    sys.exit(0)