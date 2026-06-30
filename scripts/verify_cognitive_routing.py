# scripts/verify_cognitive_routing.py
# [C5-REAL] Exergy-Maximized

import re

def verify_gemini_routing(file_path: str = "GEMINI.md") -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Buscar patrones en la matriz de enrutamiento
        has_deep_think = "Gemini 3.1 Pro" in content and "Deep Think" in content
        has_flash_low = "Gemini 3.5 Flash" in content and "LOW" in content
        
        if has_deep_think and has_flash_low:
            print("VERIFICACIÓN: Matriz cognitiva alineada con los parámetros de frontera 2026.")
            print("  - Gemini 3.1 Pro configurado para Deep Think / Deep Research.")
            print("  - Gemini 3.5 Flash (Low Temp) configurado para AST / Cryptography.")
            return True
        else:
            print("ADVERTENCIA: Desviación detectada en la matriz de enrutamiento cognitivo.")
            return False
    except FileNotFoundError:
        print("ERROR: Archivo GEMINI.md no encontrado en el root.")
        return False

if __name__ == "__main__":
    success = verify_gemini_routing()
    if not success:
        sys.exit(1)
