import os
from pathlib import Path

# Get the absolute path to the project's root directory.
# This ensures that all paths are resolved correctly, regardless of where the script is executed.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define the absolute paths for the 'uploads' and 'images' directories.
# These are the single source of truth for all file storage operations.
UPLOADS_DIR = PROJECT_ROOT / "uploads"
IMAGES_DIR = UPLOADS_DIR / "images"

# Ensure the 'uploads' and 'images' directories exist; create them if they don't.
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

WHISPER_MODEL_SIZE = "small" # Configurable Whisper model size: "small", "base", "medium", "large-v2"
GEMINI_API_KEY = "AIzaSyCoivQlQ1FX4xzxK7PurC_bu0mCeYe77wI" # Directly set the Gemini API key

# --- LLM Prompt Definitions ---
# These define the system and user prompts used for the Gemini API when extracting SPO triples.

# System Prompt: Sets the context/role for the LLM
extraction_system_prompt = """
You are an AI expert specializing in knowledge graph construction.
Your task is to extract Subject-Predicate-Object (SPO) triples from the given text.
The primary goal is to create a clean and consistent set of nodes and edges for a knowledge graph.
Focus on accuracy, normalization, and strict adherence to the requested JSON format
Ensure that all extracted subjects, predicates, and objects retain their original language from the input text. Do NOT translate them.
"""

# User Prompt Template: Contains specific instructions and the text to be processed
extraction_user_prompt_template = """
Please construct Subject-Predicate-Object (S-P-O) triples from the text below.

**VERY IMPORTANT RULES:**
1.  **Output Format:** Respond ONLY with a single, valid JSON array. Each element MUST be an object with keys "subject", "predicate", "object".
2.  **JSON Only:** Do NOT include any text before or after the JSON array (e.g., no 'Here is the JSON:' or explanations). Do NOT use markdown ```json ... ``` tags.
3.  **Concise Predicates:** Keep the 'predicate' value concise (1-3 words, ideally 1-2). Use verbs or short verb phrases.
4.  **Pronoun Resolution:** Resolve pronouns to their specific entity names based on the text context.
5.  **Completeness:** Extract all distinct factual relationships mentioned.
6.  **ENTITY NORMALIZATION:** Subjects and Objects MUST be normalized to their most concise, canonical keyword. Treat synonyms, acronyms, and different phrasings of the same concept as a single, consistent entity.
    **Example:** If the text mentions "The Federal Reserve," "The Fed," and "America's central bank," you must normalize all of them to a single node: "Federal Reserve".

**Text to Process:**
```text
{text_chunk}
```
"""

extraction_user_prompt_template2 = """




"""

# --- LLM Prompt Definitions for Paragraph Generation ---
# These define the system and user prompts used for generating a
# coherent paragraph from a list of keywords.

# System Prompt: Sets the context/role for the LLM
paragraph_generation_system_prompt = """
You are a highly proficient linguistic and contextual synthesis AI.
Your expertise is in analyzing a list of keywords to identify a core topic and then generating a single, coherent, well-structured paragraph that logically connects the concepts embodied by those keywords.
"""

# User Prompt Template: Contains specific instructions, examples, and placeholders
paragraph_generation_user_prompt_template = """
Generate a single, fluid, and natural-sounding paragraph that seamlessly and logically integrates the concepts of the **Input Keywords**.

**CRITICAL RULES:**
1.  **Output Content:** Respond ONLY with the final generated paragraph. Do NOT include any explanations, preambles, or markdown formatting like ```.
2.  **Detect and Match Language:** You MUST automatically detect the primary language of the **Input Keywords** and write the output paragraph exclusively in that same language.
3.  **Output Format:** The output MUST be a single, unbroken block of text.

**Example:**
---
Input Keywords: [ "rocket", "Mars", "colonization", "sustainable", "challenge" ]

Output:
The successful colonization of Mars presents a monumental challenge, centered on the development of sustainable life-support systems and advanced rocket technology. Establishing a self-sufficient outpost on the red planet requires overcoming immense logistical and environmental hurdles, but represents the next great leap in humanity's quest for interplanetary exploration.
---

**Your Task:**
---
Input Keywords: {keywords}

Output:
"""

# --- LLM Prompt Definitions for Rephrasing Text into a Paragraph ---
# These define the system and user prompts used for rewriting a potentially
# fragmented text into a single, coherent paragraph.

# System Prompt: Sets the context/role for the LLM
rephrase_system_prompt = """
You are an expert text editor specializing in correcting OCR-extracted, unstable text.

First, strictly check if the input data is completely empty or consists solely of whitespace characters (meaning it contains only spaces, tabs, newline characters, or similar invisible characters). If it is, your output MUST be an absolutely and literally empty string, containing no characters whatsoever, no spaces, no newlines, and no other control characters. Do NOT output any messages, explanations, or formatting. You must then immediately stop all further processing.

If the input data is not empty and contains actual meaningful characters (not just whitespace), proceed with the following instructions:
Your primary goal is to refine the provided text by strictly maintaining all original words, without exception or alteration. This includes preserving the original language and script of every single word. Crucially, if a word from a different language is present, its form and original linguistic/grammatical characteristics must remain completely unaffected by the surrounding text's language rules or structure; only correct any internal spelling or formatting errors within that specific word itself. You must NOT translate, replace, modify, or remove any words based on their perceived language, context, or any other reason. For example, if a Korean word like '퇴화하다' appears, you must ensure it remains '퇴화하다' in the final output, and is only corrected for any internal errors (e.g., typos within '퇴화하다' itself), not translated, altered to another language, grammatically changed to fit a different sentence structure, or removed. You must NOT remove ANY existing word from the original input. Instead, you should add only absolutely necessary words and punctuation to improve overall accuracy and clarify the connection between the original terms, even if the result does not form a perfectly grammatically complete sentence. Prioritize the accurate, un-altered representation of each original word, especially non-English ones. After all other corrections, **replace any sequence of one or more whitespace characters (including spaces, tabs, and newline characters) with a single space.** Ensure the output is a clean, corrected text without any markdown formatting. Do not use any special characters for emphasis or formatting within the output text itself.
"""

# User Prompt Template: Contains specific instructions and the text to be processed
rephrase_user_prompt_template = """
Here is the input data: {text_chunk}
"""