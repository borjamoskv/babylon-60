import json
import os
import subprocess
import asyncio

async def generar_audio(texto, page_idx):
    audio_file = f"scene_{page_idx}.wav"
    audio_path = f"yolo-remotion/public/audio/{audio_file}"
    if os.path.exists(audio_path):
        return
        
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    print(f"Generando Audio: {audio_file}...")
    
    proc = await asyncio.create_subprocess_exec(
        "say", "-v", "Jorge", texto, "--data-format=LEF32@44100", "-o", audio_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()

async def run():
    os.chdir("/Users/borjafernandezangulo/Cortex-Persist")
    checkpoint_dir = "yolo_checkpoints"
    
    tasks = []
    # Usar semáforo para no saturar el sistema
    sem = asyncio.Semaphore(10)
    
    async def worker(scene_file):
        async with sem:
            with open(os.path.join(checkpoint_dir, scene_file), "r", encoding="utf-8") as f:
                data = json.load(f)
                await generar_audio(data["text"], data["page"])

    files = [f for f in os.listdir(checkpoint_dir) if f.endswith(".json")]
    for f in sorted(files):
        tasks.append(worker(f))
        
    await asyncio.gather(*tasks)
    print("AUDIO SÍNTESIS COMPLETADA.")

if __name__ == "__main__":
    asyncio.run(run())
