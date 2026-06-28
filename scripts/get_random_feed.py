#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[C5-REAL] Generator of random high exergy Substack Note feeds.
Rotates headers and posts to minimize entropy and prevent redundancy.
"""

import json
import os
import random

CORTEX_DIR = os.path.expanduser('~/30_CORTEX')
JSON_PATH = os.path.join(CORTEX_DIR, 'public', 'substack_nodes.json')

HEADERS = [
    "🗜️ Compresión e Invariantes:",
    "⚡ Ensayos y Arquitectura Causal:",
    "🌌 Convergencia y Análisis:",
    "⚙️ Nodos de Tránsito Causal:",
    "🧬 Estructuras de Exergía Completa:"
]

EMOJI_KEYWORDS = {
    "forense": "🛡️",
    "phishing": "🛡️",
    "drainer": "🛡️",
    "deftones": "🎛️",
    "nine inch": "🎹",
    "manos de topo": "🐭",
    "raveros": "🕺",
    "rave": "🕺",
    "música": "🎧",
    "dj": "🎧",
    "vj": "🎧",
    "auditoría": "🕵️",
    "ia": "🤖",
    "bot": "🤖",
    "openai": "💊",
    "embeddings": "💊",
    "sincronización": "⚙️",
    "economía": "⚙️",
    "excepción": "⚖️",
    "regla": "⚖️",
    "antigravity": "🛹",
    "xokas": "🛹",
    "dominios": "🐐",
    "ens": "🐐",
    "matemáticas": "📐",
    "conspiración": "📐",
    "indignación": "📻",
    "wifi": "📻",
    "coherencia": "🎙️"
}

FALLBACK_EMOJIS = ["🧬", "🔮", "📡", "🛰️", "⛓️", "⚖️", "⚙️", "🔋", "🔑", "🔍"]

def get_emoji_for_title(title: str) -> str:
    title_lower = title.lower()
    for kw, emoji in EMOJI_KEYWORDS.items():
        if kw in title_lower:
            return emoji
    return random.choice(FALLBACK_EMOJIS)

def clean_title(title: str) -> str:
    # Remove leading emojis if present in the database title
    t = title.strip()
    if t and not t[0].isalnum() and not t[0] in ['"', "'", "“"]:
        # Check if first character is emoji or symbol and strip it
        parts = t.split(maxsplit=1)
        if len(parts) > 1 and not parts[0].isalnum():
            t = parts[1]
    return t

def generate_feed():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found. Run scripts/export_substack_nodes.py first.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Filter posts with high exergy
    valid_posts = [p for p in data if len(p.get('title', '')) > 10 and p.get('exergy_score', 0) >= 500]

    if len(valid_posts) < 4:
        print("Error: Not enough high exergy posts available.")
        return

    selected_posts = random.sample(valid_posts, 4)
    header = random.choice(HEADERS)

    print(header)
    for post in selected_posts:
        title = clean_title(post['title'])
        emoji = get_emoji_for_title(title)
        url = f"https://borjamoskv.substack.com/p/{post['post_id']}"
        print(f"• {emoji} [{title}]({url})")

if __name__ == "__main__":
    generate_feed()
