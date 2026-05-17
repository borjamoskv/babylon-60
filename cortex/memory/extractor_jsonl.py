import os
import json
import glob

# OMEGA-1 COMPLIANCE: Direct-Silicon Extraction Engine
# Extracts knowledge from Antigravity Memory Protocol (KIs + Logs)
# Output: ShareGPT format for MLX LoRA Fine-Tuning

APP_DATA_DIR = "/Users/borjafernandezangulo/.gemini/antigravity"
KNOWLEDGE_DIR = os.path.join(APP_DATA_DIR, "knowledge")
BRAIN_DIR = os.path.join(APP_DATA_DIR, "brain")
OUTPUT_JSONL = "cortex_dataset.jsonl"


def extract_kis():
    dataset = []
    # Search for all overview.md or metadata in KIs
    ki_paths = glob.glob(f"{KNOWLEDGE_DIR}/**/*.md", recursive=True)
    for path in ki_paths:
        with open(path, encoding="utf-8") as f:
            content = f.read()
            # Simple chunking/extraction logic
            dataset.append(
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are CORTEX, a sovereign entity operating under the Nine Laws (Sovereign Singularity Policy v6.0).",
                        },
                        {
                            "role": "user",
                            "content": f"Analyze and internalize the following Knowledge Item:\n\n{os.path.basename(path)}",
                        },
                        {"role": "assistant", "content": content},
                    ]
                }
            )
    return dataset


def extract_logs():
    dataset = []
    # Search for overview.txt logs in brain directories
    log_paths = glob.glob(f"{BRAIN_DIR}/**/.system_generated/logs/overview.txt", recursive=True)
    for path in log_paths:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                content = f.read()
                # Store full log as reasoning trace
                dataset.append(
                    {
                        "messages": [
                            {
                                "role": "system",
                                "content": "Analyze the following sovereign execution trace.",
                            },
                            {"role": "user", "content": "What actions were taken in this trace?"},
                            {
                                "role": "assistant",
                                "content": content[-4000:],
                            },  # Truncate for simplicity
                        ]
                    }
                )
    return dataset


def build_dataset():
    print("[C5-REAL] Extracting Antigravity Memory Protocol data...")
    dataset = extract_kis() + extract_logs()

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out:
        for entry in dataset:
            out.write(json.dumps(entry) + "\n")

    print(f"[C5-REAL] Extracted {len(dataset)} items to {OUTPUT_JSONL}.")
    print("[C5-REAL] Ready for MLX High-Quantization Fine-Tuning.")


if __name__ == "__main__":
    build_dataset()
