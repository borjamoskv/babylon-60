import json
import logging

logger = logging.getLogger("medvi_rag.guards")

class CORTEXJSONGuard:
    """Guardia determinista que asegura que el output del LLM sea JSON válido y respete el esquema."""
    
    @staticmethod
    def validate_and_parse(llm_output: str, required_schema: dict) -> dict:
        try:
            clean_str = llm_output.strip()
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:]
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3]
                
            parsed = json.loads(clean_str)
            
            for key in required_schema.keys():
                if key not in parsed:
                    raise ValueError(f"Missing required key in LLM output: {key}")
                    
            logger.info("CORTEX Guard Passed: JSON Payload Verified.")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"CORTEX Guard Failed: Invalid JSON. {e}")
            raise
        except ValueError as e:
            logger.error(f"CORTEX Guard Failed: Schema mismatch. {e}")
            raise
