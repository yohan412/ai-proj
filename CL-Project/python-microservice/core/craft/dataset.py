import os
from torch.utils.data import Dataset
from PIL import Image

# 사용자 정의 Dataset 클래스
class TrOCRDataset(Dataset):
    def __init__(self, image_dir, label_dir, processor):
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.processor = processor
        self.image_paths = sorted([
            os.path.join(image_dir, fname)
            for fname in os.listdir(image_dir)
            if fname.lower().endswith((".png", ".jpg", ".jpeg"))
        ])
        self.label_paths = [
            os.path.join(label_dir, os.path.splitext(os.path.basename(p))[0] + ".txt")
            for p in self.image_paths
        ]

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image = Image.open(self.image_paths[idx]).convert("RGB")
        with open(self.label_paths[idx], "r", encoding="utf-8") as f:
            text = f.read().strip()

        pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.squeeze(0)

        # tokenizer 처리
        encoding = self.processor.tokenizer(
            text,
            return_tensors="pt",
            padding="max_length",
            max_length=64,
            truncation=True
        )
        input_ids = encoding.input_ids.squeeze(0)

        return {
            "pixel_values": pixel_values,
            "labels": input_ids,  # 여전히 labels로 전달해야 trainer에서 loss 계산 가능
            "decoder_input_ids": input_ids,  # 명시적으로 전달
            "image_path": self.image_paths[idx],
            "label_text": text
        }