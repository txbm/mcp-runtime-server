import aiohttp

# GitHub API constants
GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPOS_PATH = "repos"
RELEASES_PATH = "releases"
LATEST_PATH = "latest"


async def fetch_latest_release_version(owner: str, repo: str):
    url = f"{GITHUB_API_BASE}/{GITHUB_REPOS_PATH}/{owner}/{repo}/releases/latest"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data["tag_name"].lstrip("v")
