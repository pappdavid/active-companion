"""faster-whisper wrapper. Requires the faster-whisper package + model."""
from companion import config


def transcribe_wav(wav_path) -> list[dict]:
    from faster_whisper import WhisperModel
    model = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(wav_path), word_timestamps=False)
    utts = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            utts.append({"speaker": "call", "text": text,
                         "start": round(seg.start, 2), "end": round(seg.end, 2)})
    return utts
