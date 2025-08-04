# loss.py
# CRAFT 학습용 손실 함수 정의
# 예측값과 GT의 region map, affinity map 차이를 MSE로 계산하고 confidence mask로 필터링함

import torch.nn.functional as F

def craft_loss(region_pred, affinity_pred, region_gt, affinity_gt, mask):
    region_loss = F.mse_loss(region_pred * mask, region_gt * mask)
    affinity_loss = F.mse_loss(affinity_pred * mask, affinity_gt * mask)

    # output: [B, 2, H, W]
    # region_pred = output[:, 0, :, :].unsqueeze(1)      # [B, 1, H, W]
    # affinity_pred = output[:, 1, :, :].unsqueeze(1)    # [B, 1, H, W]

    # # mask, region_gt, affinity_gt도 [B, 1, H, W] 형식으로 정리
    # if mask.ndim == 3:
    #     mask = mask.unsqueeze(1)
    # if region_gt.ndim == 3:
    #     region_gt = region_gt.unsqueeze(1)
    # if affinity_gt.ndim == 3:
    #     affinity_gt = affinity_gt.unsqueeze(1)

    # # loss 계산
    # region_loss = F.mse_loss(region_pred * mask, region_gt * mask)
    # affinity_loss = F.mse_loss(affinity_pred * mask, affinity_gt * mask)


    return region_loss + affinity_loss