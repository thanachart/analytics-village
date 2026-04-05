"""
Analytics Village — Episode data loader.
Downloads from GitHub release or loads from local path.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


DEFAULT_CACHE_DIR = os.path.join(str(Path.home()), ".analytics_village", "cache")


def find_episode_files(
    episode_id: str,
    data_dir: str | None = None,
) -> dict[str, str]:
    """
    Find episode files locally. Returns dict of {file_type: path}.
    Searches in order: data_dir, current directory, cache directory.
    """
    search_dirs = []
    if data_dir:
        search_dirs.append(data_dir)
    search_dirs.append(os.getcwd())
    search_dirs.append(os.path.join(DEFAULT_CACHE_DIR, episode_id))

    files = {}
    needed = {
        "db": [f"{episode_id}_village.db", "village.db", f"{episode_id}.db"],
        "qa": ["qa.json", f"{episode_id}_qa.json"],
        "brief": ["brief.md", f"{episode_id}_brief.md"],
        "schema": ["schema.json", f"{episode_id}_schema.json"],
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


def download_episode(
    episode_id: str,
    github_repo: str = "analytics-village",
    cache_dir: str | None = None,
    force: bool = False,
) -> dict[str, str]:
    """
    Download episode files from GitHub release.
    Returns dict of {file_type: path}.
    """
    cache = cache_dir or os.path.join(DEFAULT_CACHE_DIR, episode_id)
    os.makedirs(cache, exist_ok=True)

    # Check cache first
    if not force:
        files = find_episode_files(episode_id, data_dir=cache)
        if "db" in files:
            return files

    # Try downloading from GitHub
    try:
        import requests
        tag = f"episode-{episode_id}"
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
            print(f"  Note: GitHub release not found for {tag}. Using local files.")
    except Exception as e:
        print(f"  Note: Could not download from GitHub: {e}. Using local files.")

    return find_episode_files(episode_id, data_dir=cache)
