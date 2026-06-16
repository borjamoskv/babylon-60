import logging
import sys
import os

# Add root project path to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from medvi_rag.core.vector_store import MedviVectorStore

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def run_ingestion():
    db_path = "medvi_poc.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    store = MedviVectorStore(db_path)
    
    # Ingest OpenLoop Protocol
    store.insert_protocol(
        vendor_name="OpenLoop_CS",
        protocol_text="Deploy an outsourced customer support agent using CareValidate infrastructure. Requires role, budget, and urgency parameters.",
        api_schema={"action": "string", "vendor": "string", "parameters": {"role": "string", "budget": "number", "urgency": "string"}},
        keywords="customer support agent care deploy user help center"
    )
    
    # Ingest Flexport Protocol
    store.insert_protocol(
        vendor_name="Flexport_Logistics",
        protocol_text="Book international freight shipping containers. Requires origin, destination, and container type.",
        api_schema={"action": "string", "vendor": "string", "parameters": {"origin": "string", "destination": "string", "container_type": "string"}},
        keywords="shipping logistics freight flexport container transport logístic"
    )
    
    print("✅ Ingestion complete. Vendor protocols stored in Vector DB.")

if __name__ == "__main__":
    run_ingestion()
