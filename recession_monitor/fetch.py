from __future__ import annotations

import hashlib
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd


class NonRetryableSourceError(RuntimeError):
    """A request/configuration failure that cache fallback must not conceal."""


def _download(
    url: str,
    attempts: int = 3,
    timeout: int = 45,
    display_url: str | None = None,
    secret_values: tuple[str, ...] = (),
) -> bytes:
    error_text = "unknown error"
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "deterministic-recession-monitor/0.1"})
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - network behavior
            error_text = str(exc)
            for secret in secret_values:
                if secret:
                    error_text = error_text.replace(secret, "[REDACTED]")
            if isinstance(exc, HTTPError) and exc.code in {400, 401, 403}:
                raise NonRetryableSourceError(
                    f"FRED API rejected the request at {display_url or url}: {error_text}"
                ) from exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Unable to download {display_url or url}: {error_text}")


def parse_fred_csv(payload: bytes, series_id: str) -> pd.Series:
    frame = pd.read_csv(io.BytesIO(payload))
    if frame.shape[1] != 2:
        raise ValueError(f"Unexpected FRED shape for {series_id}: {frame.columns.tolist()}")
    frame.columns = ["observation_date", "value"]
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="raise")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["value"]).drop_duplicates("observation_date", keep="last")
    return frame.set_index("observation_date")["value"].sort_index().rename(series_id)


def parse_fred_json(payload: bytes, series_id: str) -> pd.Series:
    document = json.loads(payload)
    observations = document.get("observations") if isinstance(document, dict) else None
    if not isinstance(observations, list):
        raise ValueError(f"Unexpected FRED API response for {series_id}")
    frame = pd.DataFrame(observations)
    if not {"date", "value"}.issubset(frame.columns):
        raise ValueError(f"FRED API response lacks date/value fields for {series_id}")
    frame = frame.rename(columns={"date": "observation_date"})
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="raise")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["value"]).drop_duplicates("observation_date", keep="last")
    return frame.set_index("observation_date")["value"].sort_index().rename(series_id)


def _retained_path(raw_dir: Path, series_id: str) -> Path:
    api_path = raw_dir / f"{series_id}.json"
    legacy_path = raw_dir / f"{series_id}.csv"
    if api_path.exists():
        return api_path
    return legacy_path


def fetch_one(
    series_id: str,
    base_url: str,
    start: str,
    raw_dir: Path,
    offline: bool = False,
    vintage_dir: Path | None = None,
    download_attempts: int = 3,
    download_timeout: int = 45,
    api_key: str | None = None,
) -> tuple[str, pd.Series, dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    if offline:
        raw_path = _retained_path(raw_dir, series_id)
        if not raw_path.exists():
            raise FileNotFoundError(f"Offline cache missing: {raw_path}")
        payload = raw_path.read_bytes()
        retrieved_at = datetime.fromtimestamp(raw_path.stat().st_mtime, tz=timezone.utc)
    else:
        if not api_key:
            raise RuntimeError("FRED_API_KEY is required for live retrieval")
        raw_path = raw_dir / f"{series_id}.json"
        public_parameters = {
            "series_id": series_id,
            "observation_start": start,
            "file_type": "json",
        }
        query = urlencode({**public_parameters, "api_key": api_key})
        display_url = f"{base_url}?{urlencode(public_parameters)}"
        payload = _download(
            f"{base_url}?{query}",
            attempts=download_attempts,
            timeout=download_timeout,
            display_url=display_url,
            secret_values=(api_key,),
        )
        raw_path.write_bytes(payload)
        retrieved_at = datetime.now(timezone.utc)
    vintage_path = None
    if vintage_dir is not None:
        vintage_dir.mkdir(parents=True, exist_ok=True)
        vintage_path = vintage_dir / raw_path.name
        if vintage_path.exists() and vintage_path.read_bytes() != payload:
            raise RuntimeError(f"Immutable vintage conflict: {vintage_path}")
        if not vintage_path.exists():
            vintage_path.write_bytes(payload)
    payload_format = "fred_api_json" if raw_path.suffix == ".json" else "fredgraph_csv"
    series = parse_fred_json(payload, series_id) if raw_path.suffix == ".json" else parse_fred_csv(payload, series_id)
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
        "retrieval_status": "OFFLINE_CACHE" if offline else "LIVE",
        "retrieval_error": None,
        "payload_format": payload_format,
        "source_endpoint": (
            base_url
            if payload_format == "fred_api_json"
            else "https://fred.stlouisfed.org/graph/fredgraph.csv"
        ),
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
    download_attempts: int = 3,
    download_timeout: int = 45,
    allow_cache_fallback: bool = False,
    api_key: str | None = None,
) -> tuple[dict[str, pd.Series], dict[str, dict]]:
    base_url = registry["base_url"]
    if not offline and not api_key:
        raise RuntimeError("FRED_API_KEY is required for live retrieval")
    raw_dir = Path(raw_dir)
    vintage_dir = None if vintage_dir is None else Path(vintage_dir)
    collected: dict[str, pd.Series] = {}
    metadata: dict[str, dict] = {}
    ids = sorted(registry["series"])
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                fetch_one,
                sid,
                base_url,
                start,
                raw_dir,
                offline,
                vintage_dir,
                download_attempts,
                download_timeout,
                api_key,
            ): sid
            for sid in ids
        }
        for future in as_completed(futures):
            requested_sid = futures[future]
            try:
                sid, series, meta = future.result()
            except Exception as exc:
                if offline or not allow_cache_fallback or isinstance(exc, NonRetryableSourceError):
                    raise
                sid, series, meta = fetch_one(
                    requested_sid,
                    base_url,
                    start,
                    raw_dir,
                    offline=True,
                    vintage_dir=vintage_dir,
                )
                meta["retrieval_status"] = "CACHE_FALLBACK"
                meta["retrieval_error"] = f"{type(exc).__name__}: {exc}"
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
