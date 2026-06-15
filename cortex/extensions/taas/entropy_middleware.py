import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Suponemos la existencia de un cliente del Ledger para CORTEX
# from cortex.audit.ledger import AsyncLedgerClient

logger = logging.getLogger("cortex.taas.entropy_middleware")

class ThermodynamicMiddleware(BaseHTTPMiddleware):
    """
    Middleware (Capa TaaS) que intercepta el ciclo de vida de la petición HTTP
    para calcular el pulso de Entropía Computacional (Sc).
    """
    def __init__(self, app, base_latency_ms: float = 200.0, alpha: float = 1.0):
        super().__init__(app)
        self.base_latency_ms = base_latency_ms
        self.alpha = alpha
        # self.ledger = AsyncLedgerClient()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> None:
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            process_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Extraer consumo de tokens del header si está disponible (vía LLM gateway)
            tokens_used_str = response.headers.get("X-Cortex-Tokens-Used", "0")
            tokens_used = int(tokens_used_str) if tokens_used_str.isdigit() else 0
            
            # Cálculo de la fracción L_i / L_base
            latency_ratio = process_time_ms / self.base_latency_ms
            
            # Cálculo parcial de entropía (Sc) solo basado en latencia
            # La parte de tokens redundantes (beta) y precisión (gamma) se calcula asíncronamente
            partial_entropy = self.alpha * latency_ratio
            
            response.headers["X-Cortex-Entropy-Pulse"] = f"{partial_entropy:.4f}"
            
            # Log de la fricción (Debería ir al Ledger en producción)
            logger.info(
                f"[TaaS] Path: {request.url.path} | Latency: {process_time_ms:.2f}ms | "
                f"Tokens: {tokens_used} | Partial Entropy (Sc): {partial_entropy:.4f}"
            )
            
            return response
            
        except Exception as e:
            process_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"[TaaS] Fallo térmico en ruta {request.url.path}: {e}. Latency: {process_time_ms:.2f}ms")
            raise

