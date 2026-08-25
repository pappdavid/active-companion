"""Central configuration for Active Companion."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge"
SCENARIO_DIR = ROOT / "scenarios"
AUDIO_DIR = SCENARIO_DIR / "audio"
ARTIFACT_DIR = ROOT / "artifacts"

WINDOW_SECONDS = 30          # sliding conversation-context window
TOP_K = 3                    # retrieval chunks per card
CONFIDENCE_FLOOR = 1.2       # classifier fires only above this score
RECENT_UTTERANCES = 2        # tail used for recency weighting

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
WHISPER_MODEL = "base.en"
SERVER_PORT = 8734
