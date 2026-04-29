"""
Field normalizer: standardises units, validates ranges, and merges
data from multiple sources into a single tidy time-series store.
"""
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Valid value ranges for sanity-checking
RANGE_CHECKS: dict[str, tuple[float, float]] = {
    "percent":       (-20.0, 100.0),
    "basis_points":  (-500.0, 5000.0),
    "index_level":   (0.0, 1_000_000.0),
    "fx_rate":       (0.0, 100_000.0),
    "usd_per_unit":  (0.0, 100_000.0),
}

# Conversion factors when source unit differs from target unit
UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    ("percent", "basis_points"): 100.0,
    ("basis_points", "percent"): 0.01,
}


class FieldNormalizer:
    """
    Merges raw DataFrames from multiple collectors, validates values,
    converts units, and returns a consolidated wide-format snapshot DF.
    """

    MISSING_MARKER = "N/A"

    def __init__(self, target_units: Optional[dict[str, str]] = None):
        # Optionally force a unit for specific series_ids
        self.target_units = target_units or {}

    def normalize(self, frames: list[pd.DataFrame]) -> pd.DataFrame:
        """
        Merge all collector outputs, deduplicate, sort, validate, convert.
        Returns tidy long-format DataFrame sorted by (series_id, date).
        """
        if not frames:
            return pd.DataFrame()

        combined = pd.concat([f for f in frames if not f.empty], ignore_index=True)

        if combined.empty:
            return pd.DataFrame()

        combined = self._ensure_columns(combined)
        combined = self._parse_dates(combined)
        combined = self._deduplicate(combined)
        combined = self._validate_ranges(combined)
        combined = self._convert_units(combined)

        combined = combined.sort_values(["series_id", "date"]).reset_index(drop=True)
        logger.info("Normalized: %d rows, %d series", len(combined), combined["series_id"].nunique())
        return combined

    def pivot_latest(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Returns the most recent value for each series_id.
        Useful for building the daily monitoring snapshot.
        """
        if df.empty:
            return pd.DataFrame()
        latest = df.sort_values("date").groupby("series_id").last().reset_index()
        return latest[["series_id", "date", "value", "unit", "source", "quality"]]

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _ensure_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        for col, default in [
            ("series_id", "UNKNOWN"),
            ("date", None),
            ("value", None),
            ("unit", "unknown"),
            ("source", "unknown"),
            ("quality", "ok"),
        ]:
            if col not in df.columns:
                df[col] = default
        return df

    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
        bad = df["date"].isna().sum()
        if bad:
            logger.warning("Dropped %d rows with unparseable dates", bad)
        df = df.dropna(subset=["date"])
        return df

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        # Keep the most recent source observation per (series_id, date)
        before = len(df)
        df = df.drop_duplicates(subset=["series_id", "date"], keep="last")
        after = len(df)
        if before != after:
            logger.debug("Deduplicated: removed %d duplicate rows", before - after)
        return df

    def _validate_ranges(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for unit, (lo, hi) in RANGE_CHECKS.items():
            mask = (df["unit"] == unit) & df["value"].notna()
            out_of_range = mask & ((df["value"] < lo) | (df["value"] > hi))
            if out_of_range.any():
                bad_ids = df.loc[out_of_range, "series_id"].unique().tolist()
                logger.warning(
                    "Out-of-range values for unit=%s in series: %s", unit, bad_ids
                )
                df.loc[out_of_range, "quality"] = "suspect"
        return df

    def _convert_units(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for series_id, target_unit in self.target_units.items():
            mask = df["series_id"] == series_id
            current_units = df.loc[mask, "unit"].unique()
            for current_unit in current_units:
                if current_unit == target_unit:
                    continue
                factor = UNIT_CONVERSIONS.get((current_unit, target_unit))
                if factor is not None:
                    convert_mask = mask & (df["unit"] == current_unit)
                    df.loc[convert_mask, "value"] *= factor
                    df.loc[convert_mask, "unit"] = target_unit
                    logger.debug(
                        "Converted %s from %s to %s (x%.3f)",
                        series_id, current_unit, target_unit, factor
                    )
                else:
                    logger.warning(
                        "No conversion rule for %s → %s (series %s)",
                        current_unit, target_unit, series_id
                    )
        return df
