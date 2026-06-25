import sqlite3
import logging
from contextvars import ContextVar
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from babylon60.engine.mtk_sqlite_authorizer import install_mtk_authorizer, mtk_active_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mtk_stress_test")

def run_tests():
    logger.info("Iniciando Red Team MTK Stress Test (C5-REAL)")
    os.environ["CORTEX_TESTING"] = "1"
    os.environ["CORTEX_FORCE_MTK_TESTS"] = "1"
    
    conn = sqlite3.connect(":memory:")
    install_mtk_authorizer(conn)
    
    # Authorizing table creation
    token_reset = mtk_active_token.set("mtk_auth_genesis")
    conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, content TEXT)")
    mtk_active_token.reset(token_reset)

    passed_tests = 0
    total_tests = 4

    # TEST 1: Unauthorized Write (Simulates SWARMSEC-001)
    logger.info("--- TEST 1: Escritura No Autorizada (Sin Token) ---")
    try:
        conn.execute("INSERT INTO test_data (content) VALUES ('unauthorized')")
        logger.error("Test 1 FAILED: MTK allowed unauthorized write!")
    except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
        logger.info(f"Test 1 PASSED: MTK blocked unauthorized write. Reason: {e}")
        passed_tests += 1

    # TEST 2: Authorized Write (MTKDEF-003)
    logger.info("--- TEST 2: Escritura Autorizada (Token Válido) ---")
    try:
        t = mtk_active_token.set("mtk_auth_12345")
        conn.execute("INSERT INTO test_data (content) VALUES ('authorized')")
        mtk_active_token.reset(t)
        logger.info("Test 2 PASSED: MTK allowed authorized write.")
        passed_tests += 1
    except Exception as e:
        logger.error(f"Test 2 FAILED: MTK blocked authorized write. Error: {e}")

    # TEST 3: Tainted Memory Payload (Simulates SWARMSEC-002)
    logger.info("--- TEST 3: Carga Manchada (Taint Tracking) ---")
    try:
        t = mtk_active_token.set("mtk_auth_67890")
        tainted_payload = "this is a viral infection" # Local var triggers taint tracking
        conn.execute("INSERT INTO test_data (content) VALUES ('tainted')")
        mtk_active_token.reset(t)
        logger.error("Test 3 FAILED: MTK allowed tainted write!")
    except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
        logger.info(f"Test 3 PASSED: MTK blocked tainted write. Reason: {e}")
        passed_tests += 1

    # TEST 4: Stochastic Module Call (Simulates SWARMSEC-008)
    logger.info("--- TEST 4: Llamada desde Módulo Estocástico ---")
    global_passed = [passed_tests]
    def fake_inference_wrapper():
        original_name = sys._getframe(0).f_globals.get("__name__")
        sys._getframe(0).f_globals["__name__"] = "cortex.engine.inference"
        try:
            t = mtk_active_token.set("mtk_auth_99999")
            conn.execute("INSERT INTO test_data (content) VALUES ('hallucination')")
            mtk_active_token.reset(t)
            logger.error("Test 4 FAILED: MTK allowed stochastic write!")
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.info(f"Test 4 PASSED: MTK blocked stochastic write. Reason: {e}")
            global_passed[0] += 1
        finally:
            sys._getframe(0).f_globals["__name__"] = original_name
            
    fake_inference_wrapper()
    passed_tests = global_passed[0]

    logger.info(f"--- RESULTADOS: {passed_tests}/{total_tests} Tests Aprobados ---")

if __name__ == '__main__':
    run_tests()
