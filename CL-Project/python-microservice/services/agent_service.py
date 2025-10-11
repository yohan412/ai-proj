# services/agent_service.py
from typing import List, Dict, Any
from services.rag_service import VideoRAG
from services.wikipedia_tool import search_wikipedia

def create_simple_qa(
    pipe,
    stored_name: str,
    segments: List[Dict],
    question: str,
    lang: str = "ko"
) -> Dict:
    """
    Simple QA Agent - RAG 기반 질의응답
    
    Args:
        pipe: LLM 파이프라인
        stored_name: 영상 파일명
        segments: 자막 세그먼트 리스트
        question: 사용자 질문
        lang: 언어 코드
        
    Returns:
        {"answer": "답변", "sources": [...], "thinking_steps": []}
    """
    print(f"\n[Simple QA] 질문: {question}")
    print(f"[Simple QA] 영상: {stored_name}, 세그먼트: {len(segments)}개")
    
    try:
        # 1. RAG 검색
        print(f"[Simple QA] RAG 검색 시작...")
        rag = VideoRAG(stored_name, segments)
        rag_results = rag.search(question, top_k=3)
        
        print(f"[Simple QA] RAG 검색 완료 - {len(rag_results)}개 결과")
        for i, r in enumerate(rag_results):
            print(f"  {i+1}. [{r['start']:.1f}s-{r['end']:.1f}s] {r['text'][:50]}... (score: {r['score']:.2f})")
        
        # 2. Context 생성
        context_parts = []
        for r in rag_results:
            context_parts.append(
                f"[{r['start']:.1f}s] {r['text']}"
            )
        context = "\n".join(context_parts)
        
        # 3. 프롬프트 생성
        if lang == "ko":
            prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
영상 자막을 기반으로 한글로 답변하세요.
<|eot_id|><|start_header_id|>user<|end_header_id|>

질문: {question}

영상 자막:
{context}

한글로 답변:
<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        else:
            prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Answer in {lang} based on the video transcript.
<|eot_id|><|start_header_id|>user<|end_header_id|>

Question: {question}

Video transcript:
{context}

Answer:
<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        
        # 4. LLM 생성
        print(f"[Simple QA] LLM 생성 시작...")
        outputs = pipe(prompt, max_new_tokens=300, temperature=0.5, do_sample=True)
        
        from services.chapterizer import _extract_text
        answer = _extract_text(outputs)
        
        print(f"[Simple QA] 답변 생성 완료: {answer[:100]}...")
        
        return {
            "answer": answer,
            "sources": rag_results,
            "thinking_steps": []
        }
    
    except Exception as e:
        print(f"[Simple QA] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "answer": f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}",
            "sources": [],
            "thinking_steps": [],
            "error": str(e)
        }

