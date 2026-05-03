"""Generic DBC downloader with retries and on-disk cache."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from .config import DATA_DIR

log = logging.getLogger(__name__)

CHUNK = 1 << 15  # 32 KiB
TIMEOUT = 60
MAX_RETRIES = 4


def _cache_path(url: str) -> Path:
    name = Path(urlparse(url).path).name
    return DATA_DIR / name


def download(url: str, force: bool = False) -> Path | None:
    """Download a file from DATASUS, return local path or None if not found.

    Returns None for 404 (a given UF/year combination may not exist for SIM
    in older periods, for example). All other HTTP/network failures raise.
    """
    dest = _cache_path(url)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT) as r:
                if r.status_code == 404:
                    log.info("Not found (404): %s", url)
                    return None
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(CHUNK):
                        if chunk:
                            f.write(chunk)
                tmp.replace(dest)
                return dest
        except (requests.RequestException, OSError) as exc:
            last_exc = exc
            wait = 2**attempt
            log.warning(
                "Download failed (%s) attempt %d/%d - retrying in %ds",
                exc, attempt, MAX_RETRIES, wait,
            )
            time.sleep(wait)
    raise RuntimeError(f"Download failed after {MAX_RETRIES} attempts: {url}") from last_exc
