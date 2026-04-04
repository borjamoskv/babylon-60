import json
import os

def run():
    print("CORTEX-Ω: CONSOLIDANDO SAGA...")
    checkpoint_dir = "yolo_checkpoints"
    out_file = "yolo-remotion/yolo_movie_scenes.json"
    
    escenas = []
    for f in sorted(os.listdir(checkpoint_dir)):
        if f.endswith(".json"):
            with open(os.path.join(checkpoint_dir, f), "r", encoding="utf-8") as file:
                escenas.append(json.load(file))
                
    escenas = sorted(escenas, key=lambda x: x["page"])
    
    movie_data = {
        "metadata": {
            "tema": "ROBALAS - The Great Extraction",
            "total_pages": len(escenas),
            "aesthetic": "ULTRATHINK_RITXIE",
            "generation_model": "sovereign-omega"
        },
        "scenes": escenas,
    }
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(movie_data, f, ensure_ascii=False, indent=2)
        
    print(f"CONSOLIDACIÓN COMPLETADA: {len(escenas)} escenas en {out_file}.")

if __name__ == "__main__":
    run()
