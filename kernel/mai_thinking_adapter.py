import os
from openai import AzureOpenAI

def get_mai_thinking_client():
    """
    Inits the AzureOpenAI client configured for MAI-Thinking-1 via Microsoft Foundry.
    Requires environment variables:
      - MAI_FOUNDRY_ENDPOINT
      - MAI_FOUNDRY_API_KEY
    """
    endpoint = os.getenv("MAI_FOUNDRY_ENDPOINT")
    api_key = os.getenv("MAI_FOUNDRY_API_KEY")

    if not endpoint or not api_key:
        raise ValueError("[C5-REAL] FATAL: Faltan credenciales MAI_FOUNDRY_ENDPOINT o MAI_FOUNDRY_API_KEY en el entorno.")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2026-05-01-preview" # Ajustar a la API version actual de Foundry
    )
    return client

def invoke_mai_thinking(prompt: str, max_tokens: int = 4096) -> str:
    """
    Ejecuta un call de inferencia asíncrona (Test-Time Compute) al modelo MAI-Thinking-1.
    """
    client = get_mai_thinking_client()
    
    # MAI-Thinking-1 is fully compatible with OpenAI Chat Completions API format
    response = client.chat.completions.create(
        model="MAI-Thinking-1", 
        messages=[
            {"role": "system", "content": "You are a C5-REAL execution unit. Output structurally valid invariants."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.0 # Force deterministic collapse
    )
    
    return response.choices[0].message.content

if __name__ == "__main__":
    print("[C5-REAL] Adaptador MAI-Thinking-1 inicializado.")
    print("Para probar la matriz BFT, exporta MAI_FOUNDRY_ENDPOINT y ejecuta un prompt de prueba.")
