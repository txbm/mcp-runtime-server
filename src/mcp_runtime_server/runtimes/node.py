import aiohttp


async def get_latest_release():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://nodejs.org/dist/index.json") as response:
            response.raise_for_status()
            releases = await response.json()
            return releases[0]["version"].lstrip("v")


def install_runtime(sandbox: Sandbox, runtime: RuntimeConfig):
    pass
