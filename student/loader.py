"""
Analytics Village — Challenge data loader.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CACHE_DIR = os.path.join(str(Path.home()), ".analytics_village", "cache")


def find_challenge_files(challenge_id: str, data_dir: str | None = None) -> dict[str, str]:
    """Find challenge files locally. Returns {file_type: path}."""
    search_dirs = []
    if data_dir:
        search_dirs.append(data_dir)
    search_dirs.append(os.getcwd())
    search_dirs.append(os.path.join(DEFAULT_CACHE_DIR, challenge_id))
    # Also check common relative paths
    search_dirs.append(os.path.join("challenges", challenge_id, "data"))
    search_dirs.append(os.path.join("challenges", challenge_id))
    search_dirs.append(os.path.join("challenges", challenge_id, "data"))
    search_dirs.append(os.path.join("data", challenge_id))

    files = {}
    needed = {
        "db": ["village_normalized.db", "village_star.db", "village.db", f"{challenge_id}_village.db"],
        "qa": ["qa.json", f"{challenge_id}_qa.json"],
        "brief": ["brief.md", f"{challenge_id}_brief.md"],
        "schema": ["schema.json", f"{challenge_id}_schema.json"],
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
            release = resp.json()
            for asset in release.get("assets", []):
                name = asset["name"]
                dl_url = asset["browser_download_url"]
                local_path = os.path.join(cache, name)
                if not os.path.exists(local_path) or force:
                    print(f"  Downloading {name}...")
                    r = requests.get(dl_url, timeout=120)
                    with open(local_path, "wb") as f:
                        f.write(r.content)
        else:
            print(f"  Note: Release not found for {tag}. Using local files.")
    except Exception as e:
        print(f"  Note: Could not download: {e}. Using local files.")

    return find_challenge_files(challenge_id, data_dir=cache)
