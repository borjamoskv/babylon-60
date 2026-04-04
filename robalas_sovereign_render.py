import os
import json
import subprocess
import math
import shutil

def run():
    print("CORTEX-Ω: INICIANDO MOTOR DE RENDERIZADO SOBERANO...")
    
    checkpoint_dir = "yolo_checkpoints"
    out_file = "yolo-remotion/yolo_movie_scenes.json"
    os.makedirs("yolo-remotion/out", exist_ok=True)
    
    # 1. Consolidación
    escenas = []
    for f in sorted(os.listdir(checkpoint_dir)):
        if f.endswith(".json"):
            with open(os.path.join(checkpoint_dir, f), "r", encoding="utf-8") as file:
                escenas.append(json.load(file))
                
    escenas = sorted(escenas, key=lambda x: x["page"])
    print(f"Saga consolidada: {len(escenas)} escenas.")

    # 2. Sharding OOM-Safe
    CHUNK_SIZE = 50
    total_chunks = math.ceil(len(escenas) / CHUNK_SIZE)
    
    for c in range(total_chunks):
        shard_filename = f"shard_{c:03d}.mp4"
        mp4_out = f"out/{shard_filename}"
        
        if os.path.exists(f"yolo-remotion/{mp4_out}"):
            print(f"SHARD {c + 1}/{total_chunks} ya existe. Saltando.")
            continue
            
        chunk_escenas = escenas[c * CHUNK_SIZE : (c + 1) * CHUNK_SIZE]
        chunk_data = {
            "metadata": {"total_pages": len(escenas), "theme": "ROBALAS"},
            "scenes": chunk_escenas
        }
        
        # V2.3: Use a temporary file for props to avoid ARG_MAX limits on macOS
        props_path = os.path.join("yolo-remotion", "props.json")
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(chunk_data, f, ensure_ascii=False)
            
        print(f"RENDERING SHARD [{c + 1}/{total_chunks}] (Sovereign File-Prop Injection)...")
        # Remotion accepts a file path for --props
        cmd = ["npx", "remotion", "render", "src/Root.tsx", "DiegoiChronicles", mp4_out, "--props", "props.json"]
        result = subprocess.run(cmd, cwd="yolo-remotion", capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"SHARD {c + 1} completado.")
        else:
            print(f"ERROR SHARD {c + 1}: {result.stderr}")
            
    print("RENDER SOBERANO FINALIZADO.")

if __name__ == "__main__":
    run()
