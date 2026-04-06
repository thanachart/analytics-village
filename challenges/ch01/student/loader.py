"""Analytics Village — Challenge data loader."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CACHE_DIR = os.path.join(str(Path.home()), ".analytics_village", "cache")


def find_challenge_files(challenge_id: str, data_dir: str | None = None) -> dict[str, str]:
    """Find challenge files locally. Returns {file_type: path}."""
    search_dirs = []
    if data_dir:
        search_dirs.append(data_dir)
        # Also check parent dir (brief.md is in challenges/ch01/, DB is in challenges/ch01/data/)
        parent = os.path.dirname(os.path.abspath(data_dir))
        search_dirs.append(parent)
        # And grandparent for repo-level files
        search_dirs.append(os.path.dirname(parent))
    search_dirs.append(os.getcwd())
    search_dirs.append(os.path.join(DEFAULT_CACHE_DIR, challenge_id))
    search_dirs.append(os.path.join("challenges", challenge_id, "data"))
    search_dirs.append(os.path.join("challenges", challenge_id))
    search_dirs.append(os.path.join("data", challenge_id))

    files = {}
    needed = {
        "db": ["village_normalized.db", "village_star.db", "village.db"],
        "brief": ["brief.md"],
        "questions": ["questions.json"],
        "schema": ["schema.json"],
        "qa": ["qa.json"],
    }

    for file_type, candidates in needed.items():
        for search_dir in search_dirs:
            for candidate in candidates:
                path = os.path.join(search_dir, candidate)
                if os.path.exists(path):
                    files[file_type] = path
                    break
            if file_type in files:
                break

    return files


def download_challenge(
    challenge_id: str,
    github_repo: str = "thanachart/analytics-village",
    cache_dir: str | None = None,
    force: bool = False,
) -> dict[str, str]:
    """Download challenge files from GitHub release."""
    cache = cache_dir or os.path.join(DEFAULT_CACHE_DIR, challenge_id)
    os.makedirs(cache, exist_ok=True)
    if not force:
        files = find_challenge_files(challenge_id, data_dir=cache)
        if "db" in files:
            return files
    try:
        import requests
        tag = f"challenge-{challenge_id}"
        api_url = f"https://api.github.com/repos/{github_repo}/releases/tags/{tag}"
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200:
            for asset in resp.json().get("assets", []):
                local = os.path.join(cache, asset["name"])
                if not os.path.exists(local) or force:
                    print(f"  Downloading {asset['name']}...")
                    r = requests.get(asset["browser_download_url"], timeout=120)
                    with open(local, "wb") as f:
                        f.write(r.content)
    except Exception as e:
        print(f"  Note: Could not download: {e}")
    return find_challenge_files(challenge_id, data_dir=cache)
