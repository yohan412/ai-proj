# services/wikipedia_tool.py
import wikipedia

def search_wikipedia(query: str, lang: str = "ko", sentences: int = 3) -> str:
    """
    Wikipedia에서 정보 검색
    
    Args:
        query: 검색어
        lang: 언어 코드 (ko, en, ja 등)
        sentences: 반환할 문장 수
        
    Returns:
        Wikipedia 요약 텍스트
    """
    try:
        # 언어 설정
        wikipedia.set_lang(lang)
        
        # 페이지 검색
        summary = wikipedia.summary(query, sentences=sentences, auto_suggest=True)
        
        return f"[Wikipedia] {summary}"
    
    except wikipedia.exceptions.DisambiguationError as e:
        # 동음이의어 처리 - 첫 번째 옵션 사용
        try:
            if e.options:
                first_option = e.options[0]
                summary = wikipedia.summary(first_option, sentences=sentences)
                return f"[Wikipedia] {summary}"
        except:
            pass
        return f"[Wikipedia] 검색 실패: 여러 의미가 있습니다 - {', '.join(e.options[:3])}"
    
    except wikipedia.exceptions.PageError:
        return f"[Wikipedia] 검색 실패: '{query}' 페이지를 찾을 수 없습니다."
    
    except Exception as e:
        return f"[Wikipedia] 검색 실패: {str(e)}"

