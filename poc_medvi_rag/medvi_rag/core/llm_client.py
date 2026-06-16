import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger("medvi_rag.llm")

class LocalLLMClient:
    def __init__(self, ollama_url: str = "http://localhost:11434/api/generate", model: str = "llama3"):
        self.ollama_url = ollama_url
        self.model = model

    def synthesize_action(self, intent: str, context: dict) -> str:
        """
        Synthesizes the operational action based on the retrieved context.
        Attempts to call local Ollama. Falls back to deterministic mock if unavailable.
        """
        prompt = f"""
        [SYSTEM] You are Medvi-Orchestrator. You map user intents to strict API JSON payloads.
        [CONTEXT]
        Vendor: {context['vendor_name']}
        Protocol: {context['protocol_text']}
        Schema: {json.dumps(context['api_schema'])}
        
        [USER INTENT]
        {intent}
        
        [OUTPUT INSTRUCTION]
        Output ONLY valid JSON matching the Schema. No markdown, no explanations.
        """
        
        try:
            data = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }).encode('utf-8')
            
            req = urllib.request.Request(self.ollama_url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=3) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("response", "{}")
                
        except (urllib.error.URLError, TimeoutError) as e:
            logger.warning(f"Local LLM not reachable ({e}). Falling back to deterministic Medvi mock.")
            return self._mock_fallback(intent, context)

    def _mock_fallback(self, intent: str, context: dict) -> str:
        """Fallback determinista si el LLM local no está corriendo (Zero-Entropy)."""
        if "customer" in intent.lower() or "support" in intent.lower():
            return json.dumps({
                "action": "deploy_agent",
                "vendor": "OpenLoop",
                "parameters": {
                    "role": "customer_support",
                    "budget": 5000,
                    "urgency": "high"
                }
            })
        elif "logistic" in intent.lower() or "shipping" in intent.lower() or "logístic" in intent.lower():
             return json.dumps({
                "action": "book_freight",
                "vendor": "Flexport_API",
                "parameters": {
                    "origin": "CN",
                    "destination": "US",
                    "container_type": "40HQ"
                }
            })
        return "{}"
