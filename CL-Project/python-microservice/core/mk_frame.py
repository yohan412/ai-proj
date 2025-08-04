import cv2
import os
from pathlib import Path
from config import UPLOADS_DIR, IMAGES_DIR

def mk_frame(filename: str,
             in_dir: str = UPLOADS_DIR,
             out_dir: str = IMAGES_DIR,
             frame_rate: int = 10,
             default_ext: str = ".mp4",
             start_time: float = None,
             end_time: float = None) -> None:
    """
    Extracts frames from a video file within a specified time range.
    filename: Name of the video file (extension is optional).
    start_time, end_time: Time in seconds to start and end frame extraction.
    """
    base, ext = os.path.splitext(filename)
    if not ext:
        ext = default_ext
    video_path = os.path.join(in_dir, base + ext)

    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if start_time is not None:
        start_frame = int(start_time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    if end_time is not None:
        end_frame = int(end_time * fps)
    else:
        end_frame = float('inf')

    count = start_frame if start_time is not None else 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or count > end_frame:
            break
        
        if count % frame_rate == 0:
            out_name = f"{base}_{count}.jpg"
            cv2.imwrite(os.path.join(out_dir, out_name), frame)
        
        count += 1
        
    cap.release()
