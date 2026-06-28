#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[C5-REAL] Ultra-Optimized Random Substack Note Feed Generator.
Features:
  - Causal Diversity (preventing adjacent domain clustering: Music, Tech, Rants, Crypto).
  - Recency-Cooling (persisting history to avoid duplication in last 12 selections).
  - Native macOS Clipboard Integration (using pbcopy natively).
  - Clean Title sanitization (Unicode-aware, emoji purging, punctuation balance).
"""

import json
import os
import random
import subprocess
import sys

CORTEX_DIR = os.path.expanduser('~/30_CORTEX')
JSON_PATH = os.path.join(CORTEX_DIR, 'public', 'substack_nodes.json')
HISTORY_PATH = os.path.join(CORTEX_DIR, '.cortex_feed_history.json')
HISTORY_LIMIT = 12

HEADERS = [
    "🗜️ Compresión e Invariantes:",
    "⚡ Ensayos y Arquitectura Causal:",
    "🌌 Convergencia y Análisis:",
    "⚙️ Nodos de Tránsito Causal:",
    "🧬 Estructuras de Exergía Completa:",
    "🛡️ Invariantes Estructurales:"
]

# Categorización heurística para maximizar la entropía de la mezcla
CATEGORIES = {
    "TECH": ["ia", "bot", "openai", "embeddings", "antigravity", "xokas", "programadores", "senior", "cortex", "algorithm", "software", "desarrollo"],
    "CRYPTO": ["domains", "ens", "unstoppable", "phishing", "drainer", "eip", "crypto", "blockchain", "tokens"],
    "MUSIC": ["deftones", "nine inch", "manos de topo", "raveros", "rave", "música", "dj", "vj", "auditoría", "kase.o", "camisa", "compuesto", "sonido", "beat"],
    "PHILOSOPHY": ["excepción", "regla", "inmanencia", "singularidad", "epistémica", "matemáticas", "conspiración", "indignación", "wifi", "coherencia", "pensar", "humana"]
}

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
    t = title.strip()
    # Purge potential leading emojis or quotes
    while t and not t[0].isalnum() and t[0] not in ['"', "'", "“", "”"]:
        t = t[1:].strip()
    return t

def get_category(title: str) -> str:
    title_lower = title.lower()
    for cat_name, keywords in CATEGORIES.items():
        if any(kw in title_lower for kw in keywords):
            return cat_name
    return "GENERAL"

def load_history() -> list:
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history: list):
    try:
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"Warning: failed to save history: {e}\n")

def copy_to_clipboard(text: str) -> bool:
    try:
        # Native macOS pbcopy
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=text)
        return process.returncode == 0
    except Exception:
        return False

def generate_feed():
    if not os.path.exists(JSON_PATH):
        sys.stderr.write(f"Error: {JSON_PATH} not found. Run scripts/export_substack_nodes.py first.\n")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Filter high exergy posts
    valid_posts = [p for p in data if len(p.get('title', '')) > 10 and p.get('exergy_score', 0) >= 500]
    
    if len(valid_posts) < 4:
        sys.stderr.write("Error: Not enough high exergy posts available.\n")
        return

    history = load_history()
    # Filter out recent posts to prevent duplication
    filtered_posts = [p for p in valid_posts if p['post_id'] not in history]
    
    # If cooling pool is too small, release 50% of the history
    if len(filtered_posts) < 8:
        history = history[len(history)//2:]
        filtered_posts = [p for p in valid_posts if p['post_id'] not in history]

    # Select 4 posts ensuring category diversity (maximum entropy)
    selected_posts = []
    selected_categories = set()
    
    # Shuffle to ensure randomness within the pool
    random.shuffle(filtered_posts)
    
    # Pass 1: Try to select posts with unique categories
    for post in filtered_posts:
        cat = get_category(post['title'])
        if cat not in selected_categories or len(selected_categories) >= 4:
            selected_posts.append(post)
            selected_categories.add(cat)
        if len(selected_posts) == 4:
            break
            
    # Pass 2: Fallback if category diversity is not met
    if len(selected_posts) < 4:
        for post in filtered_posts:
            if post not in selected_posts:
                selected_posts.append(post)
            if len(selected_posts) == 4:
                break

    header = random.choice(HEADERS)
    output_lines = [header]
    
    new_history_entries = []
    for post in selected_posts:
        title = clean_title(post['title'])
        emoji = get_emoji_for_title(title)
        url = f"https://borjamoskv.substack.com/p/{post['post_id']}"
        output_lines.append(f"• {emoji} [{title}]({url})")
        new_history_entries.append(post['post_id'])

    # Update and persist history
    updated_history = (history + new_history_entries)[-HISTORY_LIMIT:]
    save_history(updated_history)

    final_output = "\n".join(output_lines)
    print(final_output)

    # Clipboard copy
    if copy_to_clipboard(final_output):
        print("\n⚡ [C5-REAL] Copiado al portapapeles automáticamente (Command+V listo).")
    else:
        print("\n⚠️ [C4-SIM] Portapapeles no disponible. Copiar manualmente.")

if __name__ == "__main__":
    generate_feed()
