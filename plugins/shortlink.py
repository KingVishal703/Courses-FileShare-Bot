import aiohttp
import random

# Example multiple shortlink APIs
SHORTENER_APIS = [
    {"base": "https://shortxlinks.com", "key": "c97dff111e4017c7a0d0f911d567536805cc34c5"},
    {"base": "https://arolinks.com", "key": "07fd488b04eb3d854b8dcc64f7d43c4be189133f"},
    {"base": "https://dashboard.smallshorts.com", "key": "377565808079977170de7cef039b5db76c49bf42"},
]

async def make_shortlink(original_url: str) -> str:
    """Generate shortlink from random provider."""
    provider = random.choice(SHORTENER_APIS)
    api_url = f"{provider['base']}?api={provider['key']}&url={original_url}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            data = await resp.json()
            if "shortenedUrl" in data:  # provider specific response
                return data["shortenedUrl"]
            elif "short" in data:
                return data["short"]
            else:
                return original_url  # fallback if API fails
