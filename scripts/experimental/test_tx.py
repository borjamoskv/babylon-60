import asyncio
from cortex.engine import CortexEngine
import cortex.engine.fact_store_core as fsc
import os

os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
orig = fsc.insert_fact_record

async def my_insert(*args, **kwargs):
    res = await orig(*args, **kwargs)
    print("MY_INSERT RETURNED:", res)
    return res

fsc.insert_fact_record = my_insert

class _FakeEnc:
    def encrypt_str(self, v, **k): return v
    def decrypt_str(self, v, **k): return v
    def encrypt_json(self, v, **k): import json; return json.dumps(v)
    def decrypt_json(self, v, **k): import json; return json.loads(str(v))
import cortex.crypto
cortex.crypto.get_default_encrypter = lambda: _FakeEnc()

async def main():
    engine = CortexEngine("/tmp/spy.db", auto_embed=False)
    await engine.init_db()
    res = await engine.store(project="spy", content="h", fact_type="knowledge")
    print("ENGINE STORE RETURNED:", res)

asyncio.run(main())
