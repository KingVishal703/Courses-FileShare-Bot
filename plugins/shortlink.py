import aiohttp
import random

# Example multiple shortlink APIs
SHORTENER_APIS = [
    {"base": "https://shortner1.com/api", "key": "apikey1"},
    {"base": "https://shortner2.com/api", "key": "apikey2"},
    {"base": "https://shortner3.com/api", "key": "apikey3"},
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
