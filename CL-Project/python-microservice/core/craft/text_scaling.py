import re
from collections import Counter
from typing import Dict, List, Tuple

_ts_re = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")

# 불용어 목록: 관사, 인칭대명사, 소유격 등
STOPWORDS = {
    # 관사
    'a', 'an', 'the',
    # 인칭 대명사 (주격/목적격)
    'i', 'you', 'he', 'she', 'it', 'we', 'they',
    'me', 'him', 'her', 'us', 'them',
    # 소유격 관형사
    'my', 'your', 'his', 'her', 'its', 'our', 'their',
    # 소유 대명사
    'mine', 'yours', 'hers', 'ours', 'theirs',
    # 재귀 대명사
    'myself', 'yourself', 'himself', 'herself', 'itself',
    'ourselves', 'yourselves', 'themselves',
    # 지시 대명사
    # 'this', 'that', 'these', 'those',
    # 관계·의문 대명사
    # 'who', 'whom', 'whose', 'which', 'what', 'that',
    # 부정(불특정) 대명사
    'someone', 'somebody', 'anyone', 'anybody', 'noone', 'nobody',
    'everyone', 'everybody', 'something', 'anything', 'nothing', 'everything',
    'each', 'either', 'neither', 'one', 'another', 'others',
    'some', 'any', 'none', 'both', 'few', 'many', 'several', 'all', 'most'
    # 숫자
    '1','2','3','4','5','6','7','8','9','0'
}

def _ts_to_msec(ts: str) -> int:
    """
    "seconds(.milliseconds)" → 정수 millisec 로 변환

    예)  "107.776"  ➜  107 776
         "2"       ➜  2 000
    """
    try:
        return int(float(ts) * 1_000)
    except ValueError:
        raise ValueError(f"잘못된 타임스탬프 형식: {ts!r}")

def sort_by_timestamp(blob: Dict[str, str]) -> Dict[str, str]:
    """
    {timestamp: text, …}  →  같은 형태(dict)로, 타임스탬프(초 단위) 오름차순 정렬
    """
    return dict(sorted(blob.items(), key=lambda kv: _ts_to_msec(kv[0])))

def blob_to_segments(blob: Dict[str, str]) -> List[Dict[str, str | float]]:
    """
    {timestamp(str): text, …} →  
    [
        {"start": <float>, "end": <float>, "text": <str>},
        …
    ]

    * timestamps는 ‘초(소수 가능)’ 형식의 문자열로 가정
    * end 는 “다음” 타임스탬프, 마지막 구간은 None
    """
    # 1️⃣ 타임스탬프 오름차순 정렬
    ordered = sorted(blob.items(), key=lambda kv: float(kv[0]))

    segments: List[Dict[str, str | float]] = []
    for idx, (ts, txt) in enumerate(ordered):
        start = float(ts)
        if idx + 1 < len(ordered):
            end = float(ordered[idx + 1][0])
        else:
            end = start + 2
        segments.append({"start": start, "end": end, "text": txt})

    return segments

def weighted_top_words(segments, top_n=10):
    weight_counter = Counter()
    
    for seg in segments:
        duration = seg['end'] - seg['start']
        # 1) 소문자 변환
        text = seg['text'].lower()
        # 2) 구두점(알파벳·숫자·언더스코어와 공백이 아닌 모든 문자) 제거
        text = re.sub(r'[^\w\s]', '', text)
        # 3) 공백으로 단어 분리
        words = text.split()
        
        for w in words:
            if w in STOPWORDS:
                continue
            weight_counter[w] += duration
    
    return weight_counter.most_common(top_n)