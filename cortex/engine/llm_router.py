import os
import requests
import json
from cortex.engine.cot_modulator import CoTModulator

# OMEGA-1 COMPLIANCE: Local Fallback LLM Router
# Replaces external APIs with Local Silicon-Native inference.

LOCAL_LLM_URL = "http://localhost:8080/v1/chat/completions"
MODEL_NAME = "cortex-qwen-4bit"


def ensure_air_gapped():
    """Verify that external API keys are purged from environment."""
    forbidden_keys = ["GROQ_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY"]
    for key in forbidden_keys:
        if os.getenv(key):
            print(f"[CORTEX-GUARD] LEY Ω₁ VIOLATION: {key} found in environment.")
            print(f"[CORTEX-GUARD] Forcefully purging {key} to maintain Air-Gapped sovereignty.")
            os.environ.pop(key, None)


def query_local_swarm(messages, temperature=0.1):
    """Routes the inference request to the local MLX-served model with CoT modulation."""
    ensure_air_gapped()

    # CoT Modulation
    if messages and messages[-1]["role"] == "user":
        modulator = CoTModulator()
        last_msg_content = messages[-1]["content"]
        use_cot = modulator.should_use_cot(last_msg_content)

        # Create a copy to avoid mutating the original input
        new_messages = [dict(m) for m in messages]
        new_messages[-1]["content"] = modulator.wrap_prompt(last_msg_content, use_cot)
        print(f"[CORTEX] CoT Modulation: {'ON' if use_cot else 'OFF'} (O(1) mode)")
    else:
        new_messages = messages

    payload = {
        "model": MODEL_NAME,
        "messages": new_messages,
        "temperature": temperature,
        "max_tokens": 4096,
    }

    headers = {"Content-Type": "application/json"}

    try:
        print(f"[C5-REAL] Routing request to local silicon: {MODEL_NAME}")
        # Note: Requires mlx_lm.server to be running on port 8080
        response = requests.post(LOCAL_LLM_URL, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        print("[FATAL] Local MLX Server is not running on port 8080.")
        print("Run: bash cortex/daemons/silicon_server.sh")
        return None


if __name__ == "__main__":
    test_msgs = [
        {"role": "system", "content": "You are CORTEX, operating under the Nine Laws."},
        {"role": "user", "content": "Verify your execution environment."},
    ]
    # Uncomment to test when local server is up
    # print(query_local_swarm(test_msgs))
    print("[C5-REAL] Router configured for 100% Air-Gapped execution.")
