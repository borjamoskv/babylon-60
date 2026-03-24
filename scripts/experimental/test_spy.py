import asyncio
from cortex.engine import CortexEngine

async def main():
    engine = CortexEngine("/tmp/spy.db", auto_embed=False)

    # Spy on _store_impl
    orig = engine._store_impl
    async def spy(*args, **kwargs):
        res = await orig(*args, **kwargs)
        print("SPY _store_impl returns:", res)
        return res
    engine._store_impl = spy

    # Spy on store
    orig_store = engine.store
    async def spy_store(*args, **kwargs):
        res = await orig_store(*args, **kwargs)
        print("SPY store returns:", res)
        return res
    engine.store = spy_store

    fid = await engine.store(project="spy", content="hello", fact_type="knowledge")
    print("FINAL return:", fid)

asyncio.run(main())
