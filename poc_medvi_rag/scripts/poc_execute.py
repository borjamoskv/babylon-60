import logging
import os
import sys

# Add root project path to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from medvi_rag.orchestrator.medvi_engine import MedviEngine

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    engine = MedviEngine("medvi_poc.db")
    
    print("\n" + "="*70)
    print("MEDVI-RAG ZERO-EMPLOYEE ORCHESTRATOR [C5-REAL]")
    print("="*70)
    
    intent1 = "Necesito un equipo de customer support urgente para la nueva campaña con un budget de 5000."
    engine.process_intent(intent1)
    
    print("-" * 70)
    
    intent2 = "Prepara el shipping logístico de la mercancía de China a Estados Unidos en contenedores 40HQ."
    engine.process_intent(intent2)
    
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
