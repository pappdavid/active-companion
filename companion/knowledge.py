"""Knowledge ingest (markdown/PDF) and retrieval.

numpy TF-IDF + cosine by default; auto-upgrades to sentence-transformers
embeddings when installed.
"""
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from companion import config


@dataclass
class Chunk:
    id: str
    title: str
    text: str

    def to_dict(self):
        return asdict(self)


def _read_markdown(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    # split on markdown headings; fall back to paragraph blocks
    parts = re.split(r"\n(?=#{1,3} )", raw)
    chunks = []
    for i, part in enumerate(parts):
        lines = part.strip().splitlines()
        if not lines:
            continue
        title = lines[0].lstrip("# ").strip() or path.stem
        body = "\n".join(lines).strip()
        if len(body) < 20:
            continue
        chunks.append(Chunk(id=f"{path.stem}:{i}", title=title, text=body))
    return chunks


def _read_pdf(path: Path) -> list[Chunk]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    reader = PdfReader(str(path))
    return [Chunk(id=f"{path.stem}:p{n}", title=f"{path.stem} p{n}",
                  text=(page.extract_text() or "").strip())
            for n, page in enumerate(reader.pages)
            if (page.extract_text() or "").strip()]


class KnowledgeIndex:
    """In-memory chunk store.

    Retrieval is numpy-only TF-IDF + cosine by default (no heavyweight deps).
    If sentence-transformers/torch are installed, `use_embeddings=True`
    auto-upgrades to local embedding retrieval; see README.
    """

    _STOP = set("the a an and or of to in for with on at is are was were be been "
                "it its this that these those we you our your their i me my they "
                "he she as by from about into over under can will would should "
                "do does did have has had not no yes so if then than there here".split())

    def __init__(self, use_embeddings: bool | None = None):
        self._chunks: list[Chunk] = []
        self._embeddings = None   # tf-idf matrix or embedding matrix
        self._model = None
        self._by_id = {}
        self._idf = None
        self._vocab = {}
        self._use_embeddings = use_embeddings

    @property
    def model(self):
        """Embedding model, or None when running the TF-IDF path."""
        if self._model is None and self._use_embeddings is not False:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(config.EMBEDDING_MODEL)
            except Exception:
                self._model = False  # sentinel: unavailable, use TF-IDF
        return self._model or None

    # ---- TF-IDF ----------------------------------------------------
    def _tokenize(self, text: str) -> list[str]:
        return [w for w in re.findall(r"[a-z0-9$%]+", text.lower())
                if w not in self._STOP]

    def _fit_tfidf(self, texts: list[str]):
        import numpy as np
        counts = []
        df = {}
        for t in texts:
            toks = self._tokenize(t)
            c = {}
            for w in toks:
                c[w] = c.get(w, 0) + 1
            counts.append(c)
            for w in c:
                df[w] = df.get(w, 0) + 1
        n = len(texts)
        vocab = {w: i for i, w in enumerate(sorted(df))}
        idf = np.zeros(len(vocab))
        for w, i in vocab.items():
            idf[i] = np.log((1 + n) / (1 + df[w])) + 1.0
        mat = np.zeros((n, len(vocab)))
        for r, c in enumerate(counts):
            tot = sum(c.values()) or 1
            for w, f in c.items():
                mat[r, vocab[w]] = (f / tot) * idf[vocab[w]]
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._embeddings = mat / norms
        self._vocab = vocab
        self._idf = idf

    def _tfidf_query(self, query: str):
        import numpy as np
        q = np.zeros(len(self._vocab))
        toks = self._tokenize(query)
        tot = len(toks) or 1
        for w in toks:
            i = self._vocab.get(w)
            if i is not None:
                q[i] += 1
        q = (q / tot) * self._idf
        norm = np.linalg.norm(q)
        return q / norm if norm else q

    def load_dir(self, directory: Path | None = None):
        directory = directory or config.KNOWLEDGE_DIR
        for f in sorted(Path(directory).rglob("*")):
            if f.suffix.lower() == ".md":
                self._chunks.extend(_read_markdown(f))
            elif f.suffix.lower() == ".pdf":
                self._chunks.extend(_read_pdf(f))
        self._by_id = {c.id: c for c in self._chunks}
        if self._chunks:
            import numpy as np
            model = self.model
            if model is not None:
                self._embeddings = np.asarray(model.encode(
                    [c.text for c in self._chunks], normalize_embeddings=True))
            else:
                self._fit_tfidf([c.text for c in self._chunks])
        return len(self._chunks)

    def search(self, query: str, k: int = config.TOP_K) -> list[dict]:
        """Return top-k chunks (as dicts) ranked by cosine similarity."""
        if not self._chunks or self._embeddings is None:
            return []
        import numpy as np
        model = self.model
        if model is not None:
            q = np.asarray(model.encode([query], normalize_embeddings=True))[0]
        else:
            q = self._tfidf_query(query)
        scores = self._embeddings @ q
        order = scores.argsort()[::-1][:k]
        out = []
        for idx in order:
            if scores[idx] <= 0:
                continue
            d = self._chunks[int(idx)].to_dict()
            d["score"] = round(float(scores[idx]), 4)
            out.append(d)
        return out
