"""Turn code and questions into vectors with a code-embedding model, on CPU."""

import os

import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Pinned commits so results are reproducible. Settings copied from each model's own
# sentence-transformers config (pooling + prompts); loaded with transformers' built-in code only.
MODELS = {
    "coderank": {
        "repo": "nomic-ai/CodeRankEmbed",
        "revision": "3c4b60807d71f79b43f3c4363786d9493691f8b1",
        "pooling": "cls",
        "query_prefix": "Represent this query for searching relevant code: ",
        "doc_prefix": "",
        "license": "MIT",
    },
    "jina": {
        "repo": "jinaai/jina-code-embeddings-0.5b",
        "revision": "4db235132dafbe56a8b9c5f59b59795ecf58a4a7",
        "pooling": "last",
        "query_prefix": "Find the most relevant code snippet given the following query:\n",
        "doc_prefix": "Candidate code snippet:\n",
        "license": "CC-BY-NC-4.0 (non-commercial: comparison only, never the default)",
    },
}
# shortcut: code past 512 tokens is cut off for CPU speed; raise it if long functions rank badly
MAX_TOKENS = 512


class Embedder:
    def __init__(self, name: str):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch, self.cfg = torch, MODELS[name]
        self.tokenizer = AutoTokenizer.from_pretrained(self.cfg["repo"],
                                                       revision=self.cfg["revision"])
        self.tokenizer.padding_side = "right"  # last-token pooling below relies on this
        self.model = AutoModel.from_pretrained(self.cfg["repo"], revision=self.cfg["revision"])
        self.model.eval()

    def encode(self, texts: list[str], query: bool = False, batch: int = 16) -> np.ndarray:
        """Unit-length vectors, one row per text, in input order."""
        prefix = self.cfg["query_prefix" if query else "doc_prefix"]
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))  # similar lengths batch well
        out = np.zeros((len(texts), self.model.config.hidden_size), dtype=np.float32)
        with self.torch.inference_mode():
            for start in range(0, len(order), batch):
                idx = order[start:start + batch]
                enc = self.tokenizer([prefix + texts[i] for i in idx], padding=True,
                                     truncation=True, max_length=MAX_TOKENS, return_tensors="pt")
                hidden = self.model(**enc).last_hidden_state
                if self.cfg["pooling"] == "cls":
                    vecs = hidden[:, 0]
                else:
                    last = enc["attention_mask"].sum(dim=1) - 1
                    vecs = hidden[self.torch.arange(hidden.shape[0]), last]
                vecs = self.torch.nn.functional.normalize(vecs.float(), dim=-1)
                out[idx] = vecs.numpy()
        return out
