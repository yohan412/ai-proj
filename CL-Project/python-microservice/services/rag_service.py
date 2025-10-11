# services/rag_service.py
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

class VideoRAG:
    """영상 자막 기반 RAG 시스템"""
    
    def __init__(self, stored_name: str, segments: List[Dict]):
        """
        Args:
            stored_name: 영상 파일명
            segments: 자막 세그먼트 리스트 [{"start": 0.0, "end": 3.4, "text": "..."}]
        """
        self.stored_name = stored_name
        self.segments = segments
        self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.index = None
        self.texts = []
        self._build_index()
    
    def _build_index(self):
        """FAISS 인덱스 생성"""
        print(f"[RAG] 인덱스 생성 시작 - {len(self.segments)}개 세그먼트")
        
        # 자막 텍스트 추출
        self.texts = [
            f"[{s['start']:.1f}s-{s['end']:.1f}s] {s['text']}"
            for s in self.segments
        ]
        
        # 임베딩 생성
        embeddings = self.embedder.encode(self.texts, show_progress_bar=False)
        
        # FAISS 인덱스 생성
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        
        print(f"[RAG] 인덱스 생성 완료 - {self.index.ntotal}개 벡터")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        쿼리와 가장 유사한 자막 세그먼트 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 개수
            
        Returns:
            검색 결과 리스트 [{"start": 0.0, "end": 3.4, "text": "...", "score": 0.5}]
        """
        # 쿼리 임베딩
        query_embedding = self.embedder.encode([query], show_progress_bar=False)
        
        # 검색
        distances, indices = self.index.search(
            query_embedding.astype('float32'), top_k
        )
        
        # 결과 반환
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.segments):
                seg = self.segments[idx]
                results.append({
                    "start": seg['start'],
                    "end": seg['end'],
                    "text": seg['text'],
                    "score": float(distances[0][i])
                })
        
        return results


def build_index_for_video(stored_name: str, segments: List[Dict]) -> VideoRAG:
    """영상에 대한 RAG 인덱스 생성 (외부 호출용)"""
    return VideoRAG(stored_name, segments)

