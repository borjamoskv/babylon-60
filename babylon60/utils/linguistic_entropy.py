# [C5-REAL] Exergy-Maximized
\"\"\"
Linguistic Entropy Detector (Ω₁₇)
Measures Shannon entropy (character & word-level), lexical diversity,
and detects conversational anergy (LLM slop) in natural language texts.
\"\"\"

import math
import re
from collections import Counter
from typing import Any


class LinguisticEntropyDetector:
    \"\"\"
    Analyzes linguistic entropy, vocabulary diversity, and conversational slop density.
    Erradicates high-entropy noise and low-exergy conversational artifacts.
    \"\"\"

    SLOP_PATTERNS: list[str] = [
        r\"Aquí tienes el código\",
        r\"Espero que esto ayude\",
        r\"Por supuesto\",
        r\"Entendido\",
        r\"Como modelo de lenguaje\",
        r\"Here is the code\",
        r\"I hope this helps\",
        r\"Of course\",
        r\"Understood\",
        r\"As an AI language model\",
        r\"Claro, aquí tienes\",
        r\"No dudes en preguntar\",
        r\"Feel free to ask\"
    ]

    def __init__(self) -> None:
        self.compiled_slop: list[re.Pattern[str]] = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SLOP_PATTERNS
        ]

    def calculate_char_entropy(self, text: str) -> float:
        \"\"\"
        Calculates Shannon Entropy at character level.
        Formula: H(X) = -sum(P(x) * log2(P(x)))
        \"\"\"
        if not text:
            return 0.0
        counts: Counter[str] = Counter(text)
        total_chars: int = len(text)
        entropy: float = -sum(
            (count / total_chars) * math.log2(count / total_chars)
            for count in counts.values()
        )
        return float(round(entropy, 4))

    def calculate_word_entropy(self, text: str) -> float:
        \"\"\"
        Calculates Shannon Entropy at word level.
        Splits by non-alphanumeric characters, converts to lowercase.
        \"\"\"
        words: list[str] = [
            word.lower()
            for word in re.findall(r\"[a-zA-Z0-9áéíóúñÁÉÍÓÚÑ]+\", text)
        ]
        if not words:
            return 0.0
        counts: Counter[str] = Counter(words)
        total_words: int = len(words)
        entropy: float = -sum(
            (count / total_words) * math.log2(count / total_words)
            for count in counts.values()
        )
        return float(round(entropy, 4))

    def calculate_ttr(self, text: str) -> float:
        \"\"\"
        Calculates Type-Token Ratio (Lexical Diversity).
        TTR = unique_words / total_words
        \"\"\"
        words: list[str] = [
            word.lower()
            for word in re.findall(r\"[a-zA-Z0-9áéíóúñÁÉÍÓÚÑ]+\", text)
        ]
        if not words:
            return 0.0
        unique_words: set[str] = set(words)
        return float(round(len(unique_words) / len(words), 4))

    def detect_slop(self, text: str) -> list[dict[str, Any]]:
        \"\"\"
        Detects conversational slop patterns and returns their occurrences.
        \"\"\"
        results: list[dict[str, Any]] = []
        for index, pattern in enumerate(self.compiled_slop):
            matches: list[re.Match[str]] = list(pattern.finditer(text))
            for match in matches:
                results.append(
                    {
                        \"pattern\": self.SLOP_PATTERNS[index],
                        \"matched_text\": match.group(),
                        \"start\": match.start(),
                        \"end\": match.end()
                    }
                )
        return results

    def analyze(self, text: str) -> dict[str, Any]:
        \"\"\"
        Runs the full suite of linguistic entropy and exergy analytics.
        \"\"\"
        char_entropy: float = self.calculate_char_entropy(text)
        word_entropy: float = self.calculate_word_entropy(text)
        ttr: float = self.calculate_ttr(text)
        slop_instances: list[dict[str, Any]] = self.detect_slop(text)

        # Compute Exergy Score (1.0 = Perfect structural content, 0.0 = Pure Anergy/Slop)
        # Base starts at 1.0. Deductions for low entropy, low TTR, and slop presence.
        exergy: float = 1.0

        # Slop penalty
        if slop_instances:
            exergy -= min(0.15 * len(slop_instances), 0.5)

        # Word entropy validation: Natural language typically has word entropy > 4.5
        # Extremely low word entropy indicates excessive repetition (robotic/anergic).
        if word_entropy < 3.0:
            exergy -= 0.3
        elif word_entropy < 4.5:
            exergy -= 0.1

        # TTR validation: If TTR is extremely low (< 0.2) in a long text, it means high repetition.
        words: list[str] = re.findall(r\"[a-zA-Z0-9áéíóúñÁÉÍÓÚÑ]+\", text)
        if len(words) > 50 and ttr < 0.3:
            exergy -= 0.2

        exergy = max(0.0, min(1.0, exergy))

        return {
            \"character_entropy\": char_entropy,
            \"word_entropy\": word_entropy,
            \"lexical_diversity_ttr\": ttr,
            \"slop_instances_count\": len(slop_instances),
            \"slop_instances\": slop_instances,
            \"exergy_score\": round(exergy, 4),
            \"word_count\": len(words),
            \"char_count\": len(text)
        }
