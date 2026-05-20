import asyncio
import json
from shazamio import Shazam


async def main():
    shazam = Shazam()
    try:
        out = await shazam.recognize("/tmp/reel_audio.mp3")
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    asyncio.run(main())
