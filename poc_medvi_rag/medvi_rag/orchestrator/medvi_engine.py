import logging
from medvi_rag.core.vector_store import MedviVectorStore
from medvi_rag.core.llm_client import LocalLLMClient
from medvi_rag.guards.json_guard import CORTEXJSONGuard

logger = logging.getLogger("medvi_rag.engine")

class MedviEngine:
    def __init__(self, db_path: str):
        self.store = MedviVectorStore(db_path)
        self.llm = LocalLLMClient()
        self.guard = CORTEXJSONGuard()
        
    def process_intent(self, intent: str):
        logger.info(f"--- Processing Intent: '{intent}' ---")
        
        # 1. RAG Retrieval
        logger.info("[SAGA-1] Searching Vector DB for operational protocols...")
        results = self.store.semantic_search(intent, limit=1)
        
        if not results:
            logger.error("No relevant vendor protocols found. Aborting.")
            return
            
        context = results[0]
        logger.info(f"Retrieved Context: Vendor '{context['vendor_name']}' with score {context['score']}")
        
        # 2. LLM Synthesis
        logger.info("[SAGA-2] Passing context to Local LLM for Action Synthesis...")
        llm_output = self.llm.synthesize_action(intent, context)
        logger.debug(f"Raw LLM Output: {llm_output}")
        
        # 3. Guard Validation
        logger.info("[SAGA-3] Validating LLM Output through CORTEX Guard...")
        try:
            validated_payload = self.guard.validate_and_parse(llm_output, context['api_schema'])
        except Exception as e:
            logger.error(f"Pipeline aborted at SAGA-3 due to Guard Failure: {e}")
            return
            
        # 4. External Execution (Mock)
        logger.info("[SAGA-4] Executing External Vendor API Call (Zero-Employee Architecture)...")
        return self._execute_api(context['vendor_name'], validated_payload)
        
    def _execute_api(self, vendor: str, payload: dict):
        # En el mundo real, aquí iría el request POST HTTP al vendor
        logger.info(f"🚀 [C5-REAL] MEDVI API CALL EXECUTED")
        logger.info(f"Target Vendor: {vendor}")
        logger.info(f"Payload: {payload}")
        logger.info("✅ Operation Outsourced Successfully.")
        return {"status": "success", "vendor": vendor, "payload": payload}
