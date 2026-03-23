import asyncio
from typing import Dict, Any, List
from temporalio import activity

@activity.defn
async def ingest_aws_telemetry(tenant_id: str) -> List[Dict[str, Any]]:
    """
    [Lectura Cero-Riesgo] Escanea Cost Explorer y CloudWatch en busca de 
    instancias huérfanas, Snapshots obsoletos y RDS sin conexiones.
    """
    activity.logger.info(f"[AWS] Ingestando telemetría de nube para {tenant_id}")
    await asyncio.sleep(1)
    
    # Mocking causal data 
    return [
        {"resource": "rds-staging-legacy", "cost_monthly": 1200, "status": "idle_30_days", "confidence": "C5"},
        {"resource": "ec2-ml-training-forgotten", "cost_monthly": 3400, "status": "0%_cpu_14_days", "confidence": "C5"}
    ]

@activity.defn
async def ingest_okta_telemetry(tenant_id: str) -> List[Dict[str, Any]]:
    """
    [Lectura Cero-Riesgo] Escanea Okta/Google Workspace logs en busca de 
    asientos de SaaS donde ningún empleado ha hecho login en >30 días.
    """
    activity.logger.info(f"[Okta] Analizando logs de actividad de empleados para {tenant_id}")
    await asyncio.sleep(1)
    
    return [
        {"saas": "Salesforce", "unused_seats": 14, "cost_monthly": 2100, "status": "no_login_45_days", "confidence": "C5"},
        {"saas": "Datadog", "unused_seats": 5, "cost_monthly": 800, "status": "never_activated", "confidence": "C5"}
    ]

@activity.defn
async def calculate_opex_entropy(aws_data: List[Dict], okta_data: List[Dict]) -> Dict[str, Any]:
    """
    Consolida las fugas térmicas (dinero perdido) y calcula el ROI potencial.
    """
    activity.logger.info("Calculando entropía financiera (Dinero Quemado por Ineficiencia)...")
    await asyncio.sleep(1)
    
    total_waste = sum(item["cost_monthly"] for item in aws_data + okta_data)
    cortex_fee = total_waste * 0.15 # El 15% de comisión Soberana
    net_savings = total_waste - cortex_fee
    
    return {
        "monthly_waste_usd": total_waste,
        "cortex_fee_usd": cortex_fee,
        "net_client_savings_usd": net_savings,
        "targets": {
            "aws": aws_data,
            "saas": okta_data
        }
    }

@activity.defn
async def generate_cfo_draft(report: Dict[str, Any]) -> str:
    """
    Genera el mensaje asíncrono para el CFO (Slack/Email) con el ledger link.
    """
    activity.logger.info("Forjando comunicación C-Level para aprobación atómica.")
    msg = (
        f"CORTEX OPEX AUDIT: Hemó detectado ${report['monthly_waste_usd']}/mes de entropía financiera pura.\n"
        f"- RDS/EC2 huérfanos detectados via AWS Cost Explorer.\n"
        f"- 19 asientos SaaS pagados y no usados (Okta inactivity).\n\n"
        f"Acción Soberana Preparada: Apagar AWS instances, downgrade de licencias via API.\n"
        f"Ahorro Neto Empresa: ${report['net_client_savings_usd']}/mes.\n"
        f"Comisión CORTEX (15%): ${report['cortex_fee_usd']} (Pago único descontado hoy).\n\n"
        f"[ RESPONDA 'EXECUTE' PARA PURGAR DEUDA TÉCNICA Y LIBERAR FONDOS ]"
    )
    return msg

@activity.defn
async def execute_purge_and_invoice(report: Dict[str, Any]) -> str:
    """
    La ejecución termodinámica real. Borra AWS, borra SaaS, factura en Stripe.
    """
    activity.logger.info("SEÑAL CFO CONFIRMADA. Ejecutando APIs de Destrucción y Facturando Stripe.")
    await asyncio.sleep(2) # Simula API calls destructivas
    
    return (
        f"EJECUCIÓN COMPLETADA.\n"
        f"Facturados ${report['cortex_fee_usd']} vía Stripe Connect.\n"
        f"Contratos AWS terminados y Licencias revocadas. CORTEX Ledger Registrado: 0x93FA..."
    )
