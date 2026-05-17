import asyncio
import os

from cortex.extensions.llm.router import IntentProfile, route_request


async def main():
    # Establecer la clave mock si no existe para no bloquear
    os.environ.setdefault("ANTHROPIC_API_KEY", "mock-c5-real-key")
    os.environ.setdefault("SPACEX_ALLIANCE_TOKEN", "spx-0cap-token-2026")

    print("Iniciando validación C5-REAL para Claude 4.7 Opus (Alianza SpaceX)...")

    try:
        response = await route_request(
            prompt="Genera el hash fundacional de inicio para la alianza CORTEX-SpaceX.",
            system="Responde de manera determinista, en formato hexadecimal. Solo el hash.",
            intent=IntentProfile.ULTRATHINK,
        )
        print("====== RESPUESTA OBTENIDA ======")
        print(response)

        if response.get("taint") and "opus_4.7" in response["taint"]:
            print("\n[ÉXITO] Invariante de Taint verificado. Integración C5-REAL completada.")
        else:
            print("\n[ADVERTENCIA] El adaptador respondió, pero no inyectó el Taint C5-REAL.")

    except Exception as e:
        print(f"\n[FALLO DE VALIDACIÓN] Error al invocar la API: {e}")


if __name__ == "__main__":
    asyncio.run(main())
