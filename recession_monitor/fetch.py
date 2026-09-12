from __future__ import annotations

import hashlib
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


def _download(url: str, attempts: int = 3, timeout: int = 45) -> bytes:
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "deterministic-recession-monitor/0.1"})
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - network behavior
            error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Unable to download {url}: {error}")


def parse_fred_csv(payload: bytes, series_id: str) -> pd.Series:
    frame = pd.read_csv(io.BytesIO(payload))
    if frame.shape[1] != 2:
        raise ValueError(f"Unexpected FRED shape for {series_id}: {frame.columns.tolist()}")
    frame.columns = ["observation_date", "value"]
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="raise")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["value"]).drop_duplicates("observation_date", keep="last")
    return frame.set_index("observation_date")["value"].sort_index().rename(series_id)


def fetch_one(
    series_id: str,
    base_url: str,
    start: str,
    raw_dir: Path,
    offline: bool = False,
    vintage_dir: Path | None = None,
) -> tuple[str, pd.Series, dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{series_id}.csv"
    if offline:
        if not raw_path.exists():
            raise FileNotFoundError(f"Offline cache missing: {raw_path}")
        payload = raw_path.read_bytes()
        retrieved_at = datetime.fromtimestamp(raw_path.stat().st_mtime, tz=timezone.utc)
    else:
        query = urlencode({"id": series_id, "cosd": start})
        payload = _download(f"{base_url}?{query}")
        raw_path.write_bytes(payload)
        retrieved_at = datetime.now(timezone.utc)
    vintage_path = None
    if vintage_dir is not None:
        vintage_dir.mkdir(parents=True, exist_ok=True)
        vintage_path = vintage_dir / f"{series_id}.csv"
        if vintage_path.exists() and vintage_path.read_bytes() != payload:
            raise RuntimeError(f"Immutable vintage conflict: {vintage_path}")
        if not vintage_path.exists():
            vintage_path.write_bytes(payload)
    series = parse_fred_csv(payload, series_id)
    if series.empty:
        raise ValueError(f"No valid observations for {series_id}")
    meta = {
        "series_id": series_id,
        "retrieved_at": retrieved_at.isoformat(),
        "release_date": None,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "first_observation": series.index.min().date().isoformat(),
        "last_observation": series.index.max().date().isoformat(),
        "observation_count": int(series.size),
        "raw_path": str(raw_path),
        "vintage_raw_path": None if vintage_path is None else str(vintage_path),
    }
    return series_id, series, meta


def fetch_registry(
    registry: dict,
    start: str,
    raw_dir: str | Path,
    metadata_path: str | Path,
    offline: bool = False,
    workers: int = 6,
    vintage_dir: str | Path | None = None,
) -> tuple[dict[str, pd.Series], dict[str, dict]]:
    base_url = registry["base_url"]
    raw_dir = Path(raw_dir)
    vintage_dir = None if vintage_dir is None else Path(vintage_dir)
    collected: dict[str, pd.Series] = {}
    metadata: dict[str, dict] = {}
    ids = sorted(registry["series"])
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_one, sid, base_url, start, raw_dir, offline, vintage_dir): sid
            for sid in ids
        }
        for future in as_completed(futures):
            sid, series, meta = future.result()
            collected[sid] = series
            metadata[sid] = meta
    metadata_path = Path(metadata_path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    if vintage_dir is not None:
        manifest = {
            "capture_date": vintage_dir.name,
            "series": {
                sid: {
                    "payload_sha256": metadata[sid]["payload_sha256"],
                    "first_observation": metadata[sid]["first_observation"],
                    "last_observation": metadata[sid]["last_observation"],
                    "observation_count": metadata[sid]["observation_count"],
                }
                for sid in sorted(metadata)
            },
        }
        manifest_path = vintage_dir / "manifest.json"
        manifest_payload = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        if manifest_path.exists() and manifest_path.read_bytes() != manifest_payload:
            raise RuntimeError(f"Immutable vintage manifest conflict: {manifest_path}")
        if not manifest_path.exists():
            manifest_path.write_bytes(manifest_payload)
    return collected, metadata
