# services/agent_service.py
from typing import List, Dict, Any
from services.rag_service import VideoRAG
from services.wikipedia_tool import search_wikipedia
import os
import glob

# JAVA_HOME 자동 설정 (KoNLPy용)
if 'JAVA_HOME' not in os.environ:
    print("[KoNLPy] JAVA_HOME 미설정, 자동 탐색 시작...", flush=True)
    
    # 1순위: java 명령어로 경로 찾기
    jvm_found = False
    try:
        import subprocess
        result = subprocess.run(
            ['java', '-XshowSettings:properties', '-version'],
            capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
        for line in result.stderr.split('\n'):
            if 'java.home' in line:
                java_home = line.split('=')[1].strip()
                if os.path.exists(java_home):
                    os.environ['JAVA_HOME'] = java_home
                    print(f"[KoNLPy] JAVA_HOME 자동 설정: {java_home}", flush=True)
                    jvm_found = True
                    break
    except Exception as e:
        print(f"[KoNLPy] java 명령어 실패: {e}", flush=True)
    
    # 2순위: 직접 탐색
    if not jvm_found:
        possible_paths = [
            "C:/Program Files/Java/jdk*",
            "C:/Program Files/Java/jre*",
            "C:/Program Files (x86)/Java/jdk*",
            "C:/Program Files (x86)/Java/jre*",
        ]
        
        for pattern in possible_paths:
            matches = glob.glob(pattern)
            for match in matches:
                jvm_path = os.path.join(match, "bin", "server", "jvm.dll")
                if os.path.exists(jvm_path):
                    os.environ['JAVA_HOME'] = match
                    print(f"[KoNLPy] JAVA_HOME 자동 설정: {match}", flush=True)
                    jvm_found = True
                    break
            if jvm_found:
                break
    
    if not jvm_found:
        print("[KoNLPy] ⚠️ Java를 찾을 수 없습니다. KoNLPy는 패턴 매칭으로 폴백됩니다.", flush=True)

def extract_keywords_pattern(question: str, lang: str) -> List[str]:
    """패턴 매칭으로 키워드 추출 (KoNLPy 폴백용)"""
    import re
    
    if lang == "ko":
        # 조사 제거
        cleaned = re.sub(r'(은|는|이|가|을|를|와|과|의|에서|에게|로|으로|도|만|부터|까지)(?=\s|$)', '', question)
        # 어미 제거
        cleaned = re.sub(r'(뭐야|뭔가|무엇|어떻게|왜|언제|어디|누구|해줘|해주세요|하세요)\??', '', cleaned)
        cleaned = cleaned.replace('?', '').strip()
        
        # 공백/쉼표 분리
        words = cleaned.replace(',', ' ').split()
        
        # 1-5자 한글만
        candidates = [w for w in words if re.match(r'^[가-힣]{1,5}$', w)]
        
        # 메타 명사 필터
        meta_nouns = {
            '설명', '대해', '질문', '답변', '내용', '정보', '이야기', '얘기',
            '것', '거', '뭐', '무엇', '방법', '이유', '시간', '장소', '사람'
        }
        
        # 동사/형용사 어미 제거 + 메타 명사 제거
        verb_endings = r'(대해|에서|으로|되어|이다|있다|없다|해서|하여)$'
        keywords = [w for w in candidates 
                    if not re.search(verb_endings, w) 
                    and w not in meta_nouns]
        
        return keywords
    else:
        # 영어
        keywords = re.findall(r'\b[A-Z][a-z]+\b|\b[a-z]{3,}\b', question)
        stopwords = {'what', 'how', 'is', 'are', 'the', 'a', 'an', 'when', 'where', 'why', 'who'}
        return [k for k in keywords if k.lower() not in stopwords]

def create_simple_qa(
    stored_name: str,
    segments: List[Dict],
    question: str,
    lang: str = "ko"
) -> Dict:
    """
    Simple QA Agent - Wikipedia 답변 + 영상 자막 출처
    
    Args:
        stored_name: 영상 파일명
        segments: 자막 세그먼트 리스트
        question: 사용자 질문
        lang: 언어 코드
        
    Returns:
        {"answer": "답변", "sources": [...], "thinking_steps": []}
    """
    print(f"\n[Simple QA] 질문: {question}", flush=True)
    print(f"[Simple QA] 영상: {stored_name}, 세그먼트: {len(segments)}개", flush=True)
    
    try:
        # 1. 질문에서 키워드 추출 및 정제
        import re
        
        # KoNLPy 시도 (한글 전용)
        keywords = []
        if lang == "ko":
            try:
                from konlpy.tag import Okt
                okt = Okt()
                
                # 명사만 추출
                nouns = okt.nouns(question)
                print(f"[Simple QA] KoNLPy 원본 명사: {nouns}", flush=True)
                
                # 메타 명사 필터링 (질문/요청 관련 단어 제거)
                meta_nouns = {
                    '설명', '대해', '질문', '답변', '내용', '정보', '이야기', '얘기',
                    '것', '거', '뭐', '무엇', '어떻게', '왜', '언제', '어디', '누구',
                    '방법', '이유', '시간', '장소', '사람', '알려', '해줘', '주세요'
                }
                
                # 1-5자 + 메타 명사 제외
                keywords = [n for n in nouns 
                            if 1 <= len(n) <= 5 and n not in meta_nouns]
                
                print(f"[Simple QA] 메타 명사 제거 후: {keywords}", flush=True)
                
            except Exception as e:
                print(f"[Simple QA] KoNLPy 실패 ({e}), 패턴 매칭 사용", flush=True)
                # 폴백: 패턴 매칭
                keywords = extract_keywords_pattern(question, lang)
        else:
            # 영어: 패턴 매칭
            keywords = extract_keywords_pattern(question, lang)
        
        # 중복 제거, 최대 3개
        keywords = list(dict.fromkeys(keywords))[:3]
        print(f"[Simple QA] 최종 키워드: {keywords}", flush=True)
        
        # 2. 키워드로 RAG 검색 (영상 자막에서 출처 찾기)
        final_sources = []
        if keywords and len(segments) > 0:
            print(f"[Simple QA] RAG 검색 시작...", flush=True)
            rag = VideoRAG(stored_name, segments)
            all_sources = []
            
            for kw in keywords:
                results = rag.search(kw, top_k=1)  # 키워드당 1개씩
                all_sources.extend(results)
            
            # 중복 제거 (start 기준)
            seen = set()
            unique_sources = []
            for src in all_sources:
                if src['start'] not in seen:
                    seen.add(src['start'])
                    unique_sources.append(src)
            
            # 점수 순 정렬 후 상위 3개
            unique_sources.sort(key=lambda x: x['score'])
            final_sources = unique_sources[:3]
            
            print(f"[Simple QA] 자막 출처: {len(final_sources)}개", flush=True)
            for i, src in enumerate(final_sources):
                print(f"  {i+1}. [{src['start']:.1f}s] {src['text'][:50]}...", flush=True)
        else:
            print(f"[Simple QA] 키워드 없음 또는 자막 없음, 출처 스킵", flush=True)
        
        # 3. Wikipedia에서 답변 생성 (각 키워드별로 검색)
        print(f"[Simple QA] Wikipedia 검색 시작...", flush=True)
        
        wiki_results = []
        if keywords:
            for kw in keywords:
                print(f"[Simple QA]   - '{kw}' 검색 중...", flush=True)
                wiki_result = search_wikipedia(kw, lang=lang, sentences=2)
                # [Wikipedia] 접두사 제거
                cleaned = wiki_result.replace("[Wikipedia] ", "")
                # "검색 실패" 메시지가 아니면 추가
                if "검색 실패" not in cleaned:
                    separator = "━" * 30
                    wiki_results.append(f"{separator}\n📌 {kw}\n{separator}\n{cleaned}")
        
        # 키워드가 없거나 모든 검색 실패 시 질문 전체로 검색
        if not wiki_results:
            print(f"[Simple QA]   - 질문 전체로 검색...", flush=True)
            wiki_answer = search_wikipedia(cleaned_question or question, lang=lang, sentences=3)
            answer = wiki_answer.replace("[Wikipedia] ", "")
        else:
            # 각 키워드 결과 결합
            answer = "\n\n".join(wiki_results)
        
        print(f"[Simple QA] Wikipedia 답변: {answer[:100]}...", flush=True)
        
        return {
            "answer": answer,
            "sources": final_sources,
            "thinking_steps": []
        }
    
    except Exception as e:
        print(f"[Simple QA] 오류 발생: {e}", flush=True)
        import traceback
        traceback.print_exc()
        
        return {
            "answer": f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}",
            "sources": [],
            "thinking_steps": [],
            "error": str(e)
        }

