import json
import os
from .model_loader import get_whisper_model
from config import UPLOADS_DIR

def transcribe_audio(audio_path: str):
    """
    Transcribes an audio file using the Whisper model.

    Args:
        audio_path: Absolute path to the audio file.

    Returns:
        A tuple containing the transcript data (list of dicts) and the detected language.
    
    Raises:
        RuntimeError: If the Whisper model is not initialized.
    """
    whisper_model = get_whisper_model()
    if whisper_model is None:
        raise RuntimeError("Whisper model is not initialized. Check server logs for initialization errors.")

    # Perform transcription using the loaded Whisper model
    segments, info = whisper_model.transcribe(audio_path, beam_size=5)
    
    transcript = []
    for segment in segments:
        # Store each transcribed segment with its start time, end time, and text
        transcript.append({"start": segment.start, "end": segment.end, "text": segment.text})

    # Return the transcript data and the detected language
    return transcript, info.language