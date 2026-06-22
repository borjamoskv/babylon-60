import json
import pandas as pd
from pathlib import Path

def empirical_collapse():
    print("[C5-REAL] Iniciando colapso empírico de datos...")
    data_path = Path("data/portfolio.json")
    
    if not data_path.exists():
        print("ERROR: data/portfolio.json not found.")
        return
        
    with open(data_path, "r") as f:
        data = json.load(f)
        
    df = pd.DataFrame(data)
    
    # 1. Eliminar hype: Solo nos importa PoC verificado y Severidad.
    df = df[df["poc_verified"] == True]
    
    # 2. Matemáticas puras: Asignar pesos a severidad
    severity_weights = {"critical": 10.0, "high": 7.0, "medium": 4.0, "low": 1.0}
    df["empirical_weight"] = df["severity"].map(severity_weights)
    
    # 3. Extraer métricas reales de Web3 (Immunefi) vs Web2 (MSRC / OX)
    web3_platforms = ["Immunefi"]
    df["is_web3"] = df["platform"].isin(web3_platforms)
    
    web3_impact = df[df["is_web3"]]["empirical_weight"].sum()
    web2_impact = df[~df["is_web3"]]["empirical_weight"].sum()
    
    total_criticals = len(df[df["severity"] == "critical"])
    total_highs = len(df[df["severity"] == "high"])
    
    output = {
        "verified_vulnerabilities": len(df),
        "total_critical": total_criticals,
        "total_high": total_highs,
        "web3_empirical_weight": web3_impact,
        "web2_empirical_weight": web2_impact,
        "reality_index": round(web3_impact / (web2_impact + 0.01), 2),
        "narrative": "DEFEATED" if web3_impact < web2_impact else "VERIFIED"
    }
    
    print("\n--- RESULTADO EMPÍRICO (CERO HYPE) ---")
    print(json.dumps(output, indent=2))
    
    # Sobreescribir con la realidad
    with open("data/empirical_reality.json", "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    empirical_collapse()
