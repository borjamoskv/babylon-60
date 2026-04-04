import json
import os
import random

def generate_sovereign_text(page_idx):
    subjects = ["ENJAMBRE", "CORTEX", "AGENTE OMEGA", "PULSO DIGITAL", "NODO SOMBRA", "HILO NEGRO", "VECTOR SHANNON", "PROTOCOLO VOID"]
    actions = ["perfora", "disuelve", "analiza", "intercepta", "colapsa", "extrae", "rastrea", "decodifica"]
    targets = ["la ledger", "el contrato maestro", "la pool de liquidez", "el firewall Web3", "la red descentralizada", "el hash persistente", "la clave privada", "el bloque genesis"]
    atmospheres = ["Industrial Noir.", "Silencio binario.", "Exergía máxima.", "Sin rastro.", "Asalto confirmado.", "Fricción cero.", "Visión térmica.", "Espectro YInMn."]

    s = random.choice(subjects)
    a = random.choice(actions)
    t = random.choice(targets)
    atm = random.choice(atmospheres)

    # Occasionally prepend "ESCENA {idx}: " to keep it in line with previous styles
    return f"{s} {a} {t}. {atm}"

def run():
    print("CORTEX-Ω: INICIANDO SÍNTESIS SOBERANA...")
    os.makedirs("yolo_checkpoints", exist_ok=True)

    # Identificamos el rango faltante (2-947)
    # No sobreescribimos los buenos (ej. 1, 21, 27, 37, 38, 81, 104-111, 115, 119, 212, 215, 249, 298, 312)
    # Ya hicimos purge, así que simplemente checamos si falta el archivo.
    
    count = 0
    for i in range(1, 948):
        file_path = f"yolo_checkpoints/scene_{i:04d}.json"
        if not os.path.exists(file_path):
            text = generate_sovereign_text(i)
            telemetry = f"0x{os.urandom(4).hex().upper()} >> SOVEREIGN_EXTRACTION"
            
            scene_data = {
                "page": i,
                "text": text,
                "telemetry": telemetry,
                "audio_file": f"scene_{i}.wav",
                "durationInSeconds": 6.0,
                "duracion_frames": 180
            }
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f, ensure_ascii=False)
            count += 1
            
    print(f"SÍNTESIS COMPLETADA: {count} escenas generadas localmente.")

if __name__ == "__main__":
    run()
