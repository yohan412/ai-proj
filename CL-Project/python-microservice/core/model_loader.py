import torch
import google.generativeai as genai
from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE, GEMINI_API_KEY

whisper_model = None

def initialize_models():
    """
    Initializes the Whisper model and configures the Gemini API key.
    This function is called once when the Flask application starts.
    """
    global whisper_model

    # Initialize Whisper model for audio transcription
    try:
        if torch.cuda.is_available():
            device = "cuda"
            compute_type = "float16"
            print("CUDA is available. Using GPU for Whisper model.")
        else:
            device = "cpu"
            compute_type = "int8"
            print("CUDA is not available. Using CPU for Whisper model.")
        
        whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device=device, compute_type=compute_type)
        print(f"Whisper model ('{WHISPER_MODEL_SIZE}') initialized on device: {device} with compute type: {compute_type}")
    except Exception as e:
        print(f"Fatal: Error initializing Whisper model: {e}")
        whisper_model = None

    # Configure Gemini API key
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            print("Gemini API key configured successfully.")
        except Exception as e:
            print(f"Fatal: Error configuring Gemini API: {e}")
    else:
        print("Warning: GEMINI_API_KEY not set. All Gemini-based features will be disabled.")

def get_whisper_model():
    """Returns the initialized Whisper model instance."""
    return whisper_model

def get_gemini_model(system_instruction: str):
    """
    Creates and returns a new Gemini model instance with a specific system instruction.
    This acts as a model factory.
    """
    if not GEMINI_API_KEY:
        return None
    try:
        return genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_instruction
        )
    except Exception as e:
        print(f"Error creating Gemini model with instruction: {e}")
        return None