import os
import json

def reconstruct_manifest():
    checkpoints_dir = "yolo_checkpoints"
    out_file = "yolo_movie_scenes.json"
    
    if not os.path.exists(checkpoints_dir):
        print(f"Error: {checkpoints_dir} not found.")
        return

    escenas = []
    # Sort by filename to ensure scene_0001 comes before scene_0002
    filenames = sorted([f for f in os.listdir(checkpoints_dir) if f.endswith(".json")])
    
    print(f"Loading {len(filenames)} checkpoints...")
    
    for f in filenames:
        path = os.path.join(checkpoints_dir, f)
        try:
            with open(path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
                # Ensure the data has the required fields
                if "page" in data:
                    escenas.append(data)
                else:
                    print(f"Warning: {f} missing 'page' field.")
        except Exception as e:
            print(f"Error loading {f}: {e}")

    # Re-sort scenes by page index to be absolutely sure
    escenas.sort(key=lambda x: x.get("page", 0))

    movie_data = {
        "metadata": {
            "tema": "ROBALAS — The Great Extraction",
            "total_pages": len(escenas),
            "aesthetic": "ULTRATHINK_RITXIE",
            "generation_model": "gemini-2.0-flash-exp"
        },
        "scenes": escenas
    }

    with open(out_file, "w", encoding="utf-8") as out:
        json.dump(movie_data, out, ensure_ascii=False, indent=2)
    
    print(f"MANIFEST RECONSTRUCTED: {len(escenas)} scenes saved to {out_file}")

if __name__ == "__main__":
    reconstruct_manifest()
