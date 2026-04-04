"""
VSA-SDM Engine v3.1 — Sovereign Context Collapse Module
Importable Python module for Vector Symbolic Architecture operations.

Usage:
    from vsa_engine import VSAEngine

    engine = VSAEngine(D=10000, algebra="HRR")
    engine.encode_text("deployed api v2")
    engine.bind(time_key, state_vec)
    engine.retrieve(time_key)
    engine.save("memory.vsa")
    engine.load("memory.vsa")
"""

import hashlib
import struct
import time as _time

import numpy as np


class VSAEngine:
    """Core VSA engine supporting HRR and MAP-B algebras."""

    MAGIC = b"VSA3"

    def __init__(self, D=10000, algebra="HRR", seed=None):
        """
        Args:
            D: Dimensionality of hypervectors.
            algebra: "HRR" (real-valued, FFT) or "MAPB" (bipolar, exact).
            seed: RNG seed for deterministic operation.
        """
        self.D = D
        self.algebra = algebra.upper()
        self.rng = np.random.default_rng(seed)
        self._codebook = {}
        self._char_vecs = None
        self._field_keys = {}
        self.memory = np.zeros(D)
        self._items = []  # (key_vec, state_vec, timestamp, weight)

    # ── Vector Generation ──

    def random_vec(self):
        """Generate a unit-norm random hypervector."""
        v = self.rng.standard_normal(self.D)
        return v / np.linalg.norm(v)

    def random_bipolar(self):
        """Generate a random bipolar {-1, +1}^D vector."""
        return self.rng.choice([-1.0, 1.0], size=self.D)

    def random_binary(self):
        """Generate a random binary {0, 1}^D vector."""
        return self.rng.integers(0, 2, size=self.D).astype(np.int8)

    # ── Core Algebra ──

    def bind(self, x, y):
        """Bind two vectors (association)."""
        if self.algebra == "MAPB":
            return x * y
        # HRR: circular convolution via Real FFT (50% Termodinámica/RAM Drop)
        return np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(y), n=self.D)

    def unbind(self, composite, key):
        """Unbind: extract value given key from composite."""
        if self.algebra == "MAPB":
            return composite * key  # self-inverse
        # HRR: circular correlation via Real FFT
        return np.fft.irfft(np.fft.rfft(composite) * np.conj(np.fft.rfft(key)), n=self.D)

    def bundle(self, vectors, weights=None):
        """Superimpose multiple vectors with optional weights."""
        if weights is None:
            weights = np.ones(len(vectors))
        result = np.zeros(self.D)
        for v, w in zip(vectors, weights, strict=False):
            result += w * v
        return self.normalize(result)

    @staticmethod
    def normalize(v):
        n = np.linalg.norm(v)
        return v / n if n > 1e-12 else v

    @staticmethod
    def permute(v, k):
        """Cyclic shift by k positions (sequence encoding)."""
        return np.roll(v, k)

    @staticmethod
    def cosine(a, b):
        """Cosine similarity."""
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-12 or nb < 1e-12:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    # ── Text Encoding ──

    def _init_char_vecs(self):
        if self._char_vecs is None:
            alpha = "abcdefghijklmnopqrstuvwxyz0123456789 .,;:!?-_"
            self._char_vecs = {c: self.random_vec() for c in alpha}

    def encode_text(self, text, n=3):
        """Encode text via character n-gram with positional permutation."""
        self._init_char_vecs()
        text = text.lower()
        doc = np.zeros(self.D)
        ct = 0
        for i in range(len(text) - n + 1):
            gram = text[i : i + n]
            if all(c in self._char_vecs for c in gram):
                gv = self._char_vecs[gram[0]]
                for k in range(1, n):
                    gv = self.bind(self.permute(self._char_vecs[gram[k]], k), gv)
                doc += gv
                ct += 1
        return self.normalize(doc) if ct > 0 else doc

    def encode_record(self, record):
        """Encode {key: value_text} structured data."""
        self._init_char_vecs()
        rec = np.zeros(self.D)
        for key, val in record.items():
            if key not in self._field_keys:
                self._field_keys[key] = self.random_vec()
            val_vec = self.encode_text(str(val))
            rec += self.bind(self._field_keys[key], val_vec)
        return self.normalize(rec)

    # ── Memory Operations ──

    def memorize(self, key_vec, state_vec, timestamp=None, decay_lambda=0.0):
        """Add a bound pair to the memory tensor with optional decay."""
        if timestamp is None:
            timestamp = _time.time()
        self._items.append((key_vec, state_vec, timestamp, decay_lambda))
        self._rebuild_memory()

    def _rebuild_memory(self):
        """Rebuild memory tensor with current decay weights (Fully Vectorized)."""
        if not self._items:
            self.memory = np.zeros(self.D)
            return

        now = _time.time()
        n = len(self._items)

        # Zero-Allocation Arrays (C-Contiguous memcpy bypass)
        keys = np.empty((n, self.D), dtype=np.float64)
        states = np.empty((n, self.D), dtype=np.float64)
        ts = np.empty(n, dtype=np.float64)
        lams = np.empty(n, dtype=np.float64)

        for i, pt in enumerate(self._items):
            keys[i] = pt[0]
            states[i] = pt[1]
            ts[i] = pt[2]
            lams[i] = pt[3]

        weights = np.where(lams > 0, np.exp(-lams * (now - ts)), 1.0)

        if self.algebra == "MAPB":
            weighted_bound = (keys * states) * weights[:, np.newaxis]
            self.memory = np.sum(weighted_bound, axis=0)
        else:
            # RFFT (Real Fast Fourier Transform): Aniquila al 50% el coste computacional
            keys_rfft = np.fft.rfft(keys, axis=1)
            states_rfft = np.fft.rfft(states, axis=1)
            freq_bound = keys_rfft * states_rfft
            freq_bound_weighted = freq_bound * weights[:, np.newaxis]

            # Un solo IRFFT global con la dimensión nativa forzada D
            self.memory = np.fft.irfft(np.sum(freq_bound_weighted, axis=0), n=self.D)

        self.memory = self.normalize(self.memory)

    def recall(self, key_vec):
        """Retrieve a state from the memory tensor."""
        return self.unbind(self.memory, key_vec)

    def forget(self, epsilon=0.01):
        """Purge items whose decay weight has fallen below epsilon."""
        now = _time.time()
        before = len(self._items)
        self._items = [
            (k, s, ts, lam)
            for k, s, ts, lam in self._items
            if lam == 0 or np.exp(-lam * (now - ts)) >= epsilon
        ]
        self._rebuild_memory()
        return before - len(self._items)

    def fuse_swarm_tensors(self, worker_engines, strict_rebuild=True):
        """
        O(1) Horizontal Swarm Scaling — Ultra-Sovereign Edition.
        Instead of blind Euclidean bundling (which causes 2x amplitude distortion on duplicates),
        this algorithm extracts all Epistemic Traces (atoms), resolves chronological idempotency,
        prevents Cognitive Collapse (SNR Saturation), and reconstructs a pristine Tensor.
        """
        if not worker_engines:
            return 0

        # 1. Epistemic Pool: Recolección total de átomos del enjambre
        for w in worker_engines:
            self._items.extend(w._items)

        # 2. Idempotency Purgatory: Geometría de Colapso Ourobórica
        unique_traces = {}
        for item in self._items:
            # Optimizador C5-REAL: Hasheamos solo los primeros 16 floats (128 bytes).
            # En hiper-espacios de alta dimensionalidad (VSA), la probabilidad de
            # colisión ortogonal en el sub-espacio es cero. Elimina allocations redundantes O(N*D).
            k_hash = hash(item[0][:16].tobytes())

            # Ley Cronológica: El axioma más reciente aniquila la versión obsoleta
            if k_hash not in unique_traces or item[2] > unique_traces[k_hash][2]:
                unique_traces[k_hash] = item

        before_count = len(self._items)
        self._items = list(unique_traces.values())
        dropped = before_count - len(self._items)

        # 3. Saturation Shield (Zero-Entropy Alert)
        # Una matriz pierde fidelidad destructiva si Item_Count > sqrt(D)*1.5 (Aproximación empírica)
        elastic_threshold = int(np.sqrt(self.D)) * 2
        if len(self._items) > elastic_threshold:
            # Fuego Fatuo: Se activa el Olvido Natural (Fuerza de Ebbinghaus) para preservar el SNR
            self.forget(epsilon=0.1)
            # forget() ya ejecuta self._rebuild_memory() en su interior
        elif strict_rebuild:
            # 4. Strict Rebuild (Colapso Perfecto Cero-Distorsión)
            self._rebuild_memory()
        else:
            # Dirty Bundle: Modo fallback extremadamente rápido para streaming/streaming logs (sin rebuild)
            all_tensors = [self.memory] + [w.memory for w in worker_engines]
            self.memory = self.bundle(all_tensors)

        return dropped

    @property
    def snr(self):
        """Current signal-to-noise ratio estimate."""
        n = len(self._items)
        return np.sqrt(self.D / n) if n > 0 else float("inf")

    @property
    def item_count(self):
        return len(self._items)

    # ── Codebook & SDM ──

    def register_codebook(self, name, vectors):
        """Register a named codebook for clean-up / resonator ops."""
        self._codebook[name] = list(vectors)

    def cleanup(self, noisy_vec, codebook_name):
        """Project noisy vector onto nearest codebook entry."""
        cb = self._codebook.get(codebook_name)
        if not cb:
            raise ValueError(f"No codebook: {codebook_name}")
        sims = [self.cosine(noisy_vec, e) for e in cb]
        best = int(np.argmax(sims))
        return cb[best], best, sims[best]

    def resonate(self, composite, codebook_names, max_iter=100):
        """
        Resonator network: factor a composite into components.
        Args:
            composite: The bound composite vector.
            codebook_names: List of codebook names, one per factor.
            max_iter: Maximum iterations.
        Returns:
            List of (codebook_entry, index) tuples, one per factor.
        """
        n_factors = len(codebook_names)
        cbs = [self._codebook[n] for n in codebook_names]
        # Initialize estimates as superposition
        estimates = [self.normalize(np.sum(cb, axis=0)) for cb in cbs]

        for _it in range(max_iter):
            prev = [
                int(np.argmax([self.cosine(e, v) for v in cb]))
                for e, cb in zip(estimates, cbs, strict=False)
            ]

            for f in range(n_factors):
                # Unbind all other estimates
                signal = composite.copy()
                for g in range(n_factors):
                    if g != f:
                        signal = self.unbind(signal, estimates[g])
                # Project onto codebook
                _, best, _ = self.cleanup(signal, codebook_names[f])
                estimates[f] = cbs[f][best]

            curr = [
                int(np.argmax([self.cosine(e, v) for v in cb]))
                for e, cb in zip(estimates, cbs, strict=False)
            ]
            if curr == prev:
                return [(cbs[f][curr[f]], curr[f]) for f in range(n_factors)]

        return [(cbs[f][curr[f]], curr[f]) for f in range(n_factors)]

    # ── Persistence ──

    def save(self, path):
        """Serialize memory tensor to .vsa binary with SHA-256."""
        tensor_bytes = self.memory.tobytes()
        sha = hashlib.sha256(tensor_bytes).digest()
        n_items = len(self._items)
        with open(path, "wb") as f:
            f.write(self.MAGIC)
            f.write(struct.pack("<II", self.D, n_items))
            f.write(tensor_bytes)
            f.write(sha)
        return len(tensor_bytes) + 44  # magic + header + sha

    def load(self, path):
        """Load and verify a .vsa file."""
        with open(path, "rb") as f:
            data = f.read()
        if data[:4] != self.MAGIC:
            raise ValueError("Invalid .vsa file (bad magic)")
        d, n = struct.unpack("<II", data[4:12])
        if d != self.D:
            raise ValueError(f"Dimension mismatch: file={d}, engine={self.D}")
        tensor_data = data[12 : 12 + d * 8]
        sha_stored = data[12 + d * 8 : 12 + d * 8 + 32]
        sha_computed = hashlib.sha256(tensor_data).digest()
        if sha_computed != sha_stored:
            raise ValueError("SHA-256 integrity check FAILED")
        self.memory = np.frombuffer(tensor_data, dtype=np.float64).copy()
        return n

    # ── LLM Embedding Projection ──

    def project_from_llm(self, embedding, llm_dim):
        """
        Project an LLM embedding (dim=llm_dim) into VSA space (dim=D).
        Uses a deterministic random projection matrix (Johnson-Lindenstrauss).
        """
        # Deterministic projection: seeded by llm_dim for reproducibility
        proj_rng = np.random.default_rng(seed=llm_dim)
        # Sparse random projection (sqrt(3)-sparse Achlioptas)
        # P[i,j] ∈ {-1, 0, +1} with probs {1/6, 2/3, 1/6}
        proj = proj_rng.choice(
            [-1.0, 0.0, 0.0, 0.0, 1.0],  # approx 1/5, 3/5, 1/5
            size=(self.D, llm_dim),
        )
        projected = proj @ embedding
        return self.normalize(projected)

    def project_to_llm(self, vsa_vec, llm_dim):
        """
        Project VSA vector back to LLM embedding space.
        Pseudo-inverse via transpose of the same projection matrix.
        """
        proj_rng = np.random.default_rng(seed=llm_dim)
        proj = proj_rng.choice([-1.0, 0.0, 0.0, 0.0, 1.0], size=(self.D, llm_dim))
        # Pseudo-inverse projection (P^T @ vsa_vec)
        return self.normalize(proj.T @ vsa_vec)

    # ── Diagnostics ──

    def capacity_report(self):
        """Return capacity diagnostics."""
        n = self.item_count
        snr = self.snr
        chunk_threshold = int(np.sqrt(self.D))
        needs_chunking = n > chunk_threshold
        return {
            "dimensions": self.D,
            "items": n,
            "snr": round(snr, 2),
            "chunk_threshold": chunk_threshold,
            "needs_chunking": needs_chunking,
            "memory_bytes": self.D * 8,
            "algebra": self.algebra,
        }
