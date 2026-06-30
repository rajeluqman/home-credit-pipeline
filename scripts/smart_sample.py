#!/usr/bin/env python3
"""Smart sampler — stratified anchor + referential closure over the 7 Home Credit source CSVs.

Spec: docs/ADDENDUM-A_local-dev-smart-sampling.md §2 (Flow B — reads raw from S3 dev landing).

Produces a small, self-consistent slice of the REAL datasets for Phase-1 local dev:
  1. Anchor: sample applicants from application_train, STRATIFIED by TARGET (default rate ~8%
     preserved in the slice).
  2. Referential closure: keep every child row whose foreign key resolves to a sampled applicant
     (bureau / previous_application via SK_ID_CURR; bureau_balance via the sampled SK_ID_BUREAU;
     installments / POS_CASH / credit_card via SK_ID_CURR). No join is left dangling, so the
     identity + dbt tests hold on the slice exactly as on the full set.

Source and output may each be a local dir OR an s3:// URI. Flow B (the sanctioned Phase-1 path,
addendum §2) keeps raw in the S3 dev landing zone — the durable source-of-truth — and STREAMS it
here, so the 7 GB raw never persists on the ephemeral Codespace disk. Big child tables
(bureau_balance 27M, installments 13M, POS 10M) are read in chunks and filtered incrementally, so
peak memory stays bounded regardless of source.

Output: <out-dir>/<same filename>.csv per table + _manifest.json (seed, realised default rate,
per-table row counts) for reproducibility. Local output (data/sample/) is gitignored.

S3 access: when any path is s3://, AWS creds are loaded from --env-file (default .env.dev) and
AWS_DEFAULT_REGION is set from AWS_REGION. Requires s3fs (see requirements.txt).

Usage:
  # Flow B — read real raw from S3 dev landing, write slice locally for the Glue Docker run:
  python scripts/smart_sample.py \
      --source-dir s3://home-credit-risk-dev-1/landing --out-dir data/sample --frac 0.015
  # Local-only (e.g. raw already on disk):
  python scripts/smart_sample.py --source-dir data --out-dir data/sample --n 4000
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Read big tables in chunks of this many rows so a 27M-row CSV never lands in memory whole.
CHUNK = 500_000


def _is_s3(p) -> bool:
    return str(p).startswith("s3://")


def _join(base, name: str) -> str:
    base = str(base)
    return base.rstrip("/") + "/" + name if _is_s3(base) else str(Path(base) / name)


def _exists(path: str) -> bool:
    if _is_s3(path):
        import fsspec
        return fsspec.filesystem("s3").exists(path)
    return Path(path).exists()


def _read_filtered(path: str, id_col: str, id_set: set, chunksize: int = CHUNK) -> pd.DataFrame:
    """Stream a CSV (local or s3://) in chunks, keeping only rows whose `id_col` is in `id_set`."""
    kept: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, chunksize=chunksize):
        kept.append(chunk[chunk[id_col].isin(id_set)])
    return pd.concat(kept, ignore_index=True) if kept else pd.DataFrame()


def _write(df: pd.DataFrame, out_dir, name: str) -> int:
    path = _join(out_dir, name)
    df.to_csv(path, index=False)
    print(f"  {name}: {len(df):,} rows -> {path}")
    return len(df)


def _write_manifest(out_dir, manifest: dict) -> str:
    path = _join(out_dir, "_manifest.json")
    data = json.dumps(manifest, indent=2)
    if _is_s3(path):
        import fsspec
        with fsspec.open(path, "w") as f:
            f.write(data)
    else:
        Path(path).write_text(data)
    return path


def sample(source_dir, out_dir, frac: float | None, n: int | None, seed: int) -> dict:
    if not _is_s3(out_dir):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    # --- 1. Anchor: stratified sample of applicants by TARGET --------------------------------
    app = pd.read_csv(_join(source_dir, "application_train.csv"))
    full_rate = float(app["TARGET"].mean())
    if n is not None:
        frac = min(1.0, n / len(app))
    if frac is None:
        frac = 0.015
    app_s = app.groupby("TARGET", group_keys=False).sample(frac=frac, random_state=seed)
    curr_ids = set(app_s["SK_ID_CURR"])
    sample_rate = float(app_s["TARGET"].mean())
    print(f"Anchor: {len(app_s):,}/{len(app):,} applicants (frac={frac:.4f}), "
          f"default rate {sample_rate:.4f} vs full {full_rate:.4f}")
    counts["application_train.csv"] = _write(app_s, out_dir, "application_train.csv")

    # --- 2. Referential closure --------------------------------------------------------------
    # bureau: anchored on SK_ID_CURR; its SK_ID_BUREAU set drives bureau_balance.
    bureau = pd.read_csv(_join(source_dir, "bureau.csv"))
    bureau_s = bureau[bureau["SK_ID_CURR"].isin(curr_ids)]
    bureau_ids = set(bureau_s["SK_ID_BUREAU"])
    counts["bureau.csv"] = _write(bureau_s, out_dir, "bureau.csv")

    # bureau_balance has NO SK_ID_CURR — close it on the sampled SK_ID_BUREAU (chunked, 27M rows).
    bb_s = _read_filtered(_join(source_dir, "bureau_balance.csv"), "SK_ID_BUREAU", bureau_ids)
    counts["bureau_balance.csv"] = _write(bb_s, out_dir, "bureau_balance.csv")

    # previous_application: anchored on SK_ID_CURR. The child tables below share the same
    # applicant anchor, so their SK_ID_PREV linkage to this sampled set stays intact.
    prev = pd.read_csv(_join(source_dir, "previous_application.csv"))
    prev_s = prev[prev["SK_ID_CURR"].isin(curr_ids)]
    counts["previous_application.csv"] = _write(prev_s, out_dir, "previous_application.csv")

    # installments / POS_CASH / credit_card: all carry SK_ID_CURR — close on it (chunked).
    for fname in ("installments_payments.csv", "POS_CASH_balance.csv", "credit_card_balance.csv"):
        df_s = _read_filtered(_join(source_dir, fname), "SK_ID_CURR", curr_ids)
        counts[fname] = _write(df_s, out_dir, fname)

    # --- 3. Manifest -------------------------------------------------------------------------
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "seed": seed,
        "frac": frac,
        "n_requested": n,
        "applicants_sampled": len(app_s),
        "applicants_total": len(app),
        "default_rate_full": round(full_rate, 6),
        "default_rate_sample": round(sample_rate, 6),
        "row_counts": counts,
    }
    print(f"Manifest: {_write_manifest(out_dir, manifest)}")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description="Stratified + FK-closure sampler for Home Credit CSVs.")
    p.add_argument("--source-dir", default="data",
                   help="Local dir or s3:// URI holding the 7 source CSVs (default: data).")
    p.add_argument("--out-dir", default="data/sample",
                   help="Local dir or s3:// URI for the slice (default: data/sample).")
    p.add_argument("--env-file", default=".env.dev",
                   help="Loaded for AWS creds when any path is s3:// (default: .env.dev).")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--frac", type=float, help="Fraction of applicants to keep (default 0.015).")
    g.add_argument("--n", type=int, help="Target applicant count (overrides --frac).")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    if _is_s3(args.source_dir) or _is_s3(args.out_dir):
        from dotenv import load_dotenv
        if Path(args.env_file).exists():
            load_dotenv(args.env_file)
        os.environ.setdefault("AWS_DEFAULT_REGION", os.getenv("AWS_REGION", "ap-southeast-1"))

    if not _exists(_join(args.source_dir, "application_train.csv")):
        p.error(f"no application_train.csv under {args.source_dir} — point --source-dir at the "
                f"real Kaggle CSVs (local dir or s3:// landing zone) first")
    print(f"Smart sampling from {args.source_dir} -> {args.out_dir}")
    sample(args.source_dir, args.out_dir, args.frac, args.n, args.seed)
    print("Done — self-consistent sample ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
