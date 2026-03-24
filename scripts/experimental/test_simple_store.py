import asyncio
from cortex.engine import CortexEngine

async def main():
    try:
        engine = CortexEngine("/tmp/test_simple_store.db", auto_embed=False)
        fid = await engine.store(project="test", content="hello", fact_type="knowledge")
        print("stored:", fid)
    except Exception as e:
        print("err:", e)

asyncio.run(main())
