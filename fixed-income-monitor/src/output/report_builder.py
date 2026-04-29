"""
Report Builder — converts PerformanceSnapshot list to CSV + Excel output.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.schema import PerformanceSnapshot

logger = logging.getLogger(__name__)

# Column display order in final output
_FLAT_COLS = [
    "as_of_date", "field_name", "asset_class", "region",
    "rating_bucket", "tenor_bucket", "unit",
    "normalized_value", "d1", "wtd", "mtd", "ytd",
    "chg_1w", "chg_1m", "chg_1y", "pct_rank_1y",
    "source_name", "source_url", "rebuild_grade", "notes",
]

# Rounding by unit (decimal places)
_ROUND_RULES: dict[str, int] = {
    "percent":       3,
    "basis_points":  1,
    "index_level":   2,
    "fx_rate":       5,
    "usd_per_unit":  2,
}

# Excel conditional colours for change columns
_GREEN = "C6EFCE"   # positive credit/rate change = tighter spread / lower yield → good
_RED   = "FFC7CE"
_AMBER = "FFEB9C"


class ReportBuilder:
    """Writes final monitor output from a list of PerformanceSnapshot."""

    def __init__(self, output_dir: str = "data/processed"):
        self.out = Path(output_dir)
        self.out.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        snapshots: list[PerformanceSnapshot],
        as_of: date | None = None,
        write_csv: bool = True,
        write_xlsx: bool = True,
    ) -> dict[str, Path]:
        if not snapshots:
            logger.warning("ReportBuilder: no snapshots to write")
            return {}

        as_of = as_of or date.today()
        df = self._to_dataframe(snapshots)
        tag = as_of.strftime("%Y%m%d")
        outputs: dict[str, Path] = {}

        if write_csv:
            path = self.out / f"fi_monitor_{tag}.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig")
            logger.info("CSV → %s (%d rows)", path, len(df))
            outputs["csv"] = path

        if write_xlsx:
            path = self.out / f"fi_monitor_{tag}.xlsx"
            self._write_xlsx(df, path, as_of)
            outputs["xlsx"] = path

        return outputs

    # ── DataFrame helpers ─────────────────────────────────────────────────────

    def _to_dataframe(self, snapshots: list[PerformanceSnapshot]) -> pd.DataFrame:
        rows = [s.to_flat_dict() for s in snapshots]
        df = pd.DataFrame(rows)

        # Apply rounding by unit
        for unit, decimals in _ROUND_RULES.items():
            mask = df["unit"] == unit
            for col in ["normalized_value", "d1", "wtd", "mtd", "ytd",
                        "chg_1w", "chg_1m", "chg_1y"]:
                if col in df.columns:
                    df.loc[mask, col] = df.loc[mask, col].round(decimals)

        # Sort: asset_class → region → field_name
        sort_order = {"rates": 0, "credit": 1, "equity": 2, "fx": 3, "commodity": 4}
        df["_sort"] = df["asset_class"].map(sort_order).fillna(99)
        df = df.sort_values(["_sort", "region", "field_name"]).drop(columns=["_sort"])

        # Keep only defined columns, fill missing with None
        for c in _FLAT_COLS:
            if c not in df.columns:
                df[c] = None
        return df[_FLAT_COLS].reset_index(drop=True)

    # ── Excel writer ──────────────────────────────────────────────────────────

    def _write_xlsx(self, df: pd.DataFrame, path: Path, as_of: date) -> None:
        try:
            import openpyxl
            from openpyxl.styles import PatternFill, Font, Alignment
            from openpyxl.utils import get_column_letter
        except ImportError:
            logger.warning("openpyxl not installed — skipping XLSX. pip install openpyxl")
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"FI Monitor {as_of}"

        header_fill = PatternFill("solid", fgColor="1F4E79")
        header_font = Font(color="FFFFFF", bold=True, size=9)
        data_font   = Font(size=9)

        # Write headers
        ws.append(list(df.columns))
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", wrap_text=True)

        # Change columns — used for conditional colouring
        chg_cols = {"d1", "wtd", "mtd", "ytd", "chg_1w", "chg_1m", "chg_1y"}
        col_idx = {name: idx + 1 for idx, name in enumerate(df.columns)}

        red_fill   = PatternFill("solid", fgColor=_RED)
        green_fill = PatternFill("solid", fgColor=_GREEN)

        for _, row in df.iterrows():
            ws.append([_fmt(row[c]) for c in df.columns])
            r = ws.max_row
            for cell in ws[r]:
                cell.font = data_font

            ac = str(row.get("asset_class", ""))
            for chg_col in chg_cols:
                if chg_col not in col_idx:
                    continue
                cell = ws.cell(row=r, column=col_idx[chg_col])
                try:
                    v = float(cell.value)
                except (TypeError, ValueError):
                    continue
                # Colour logic:
                #  equity/commodity: positive = green
                #  rates/credit: positive change = red (yield/spread RISING = bad)
                if ac in ("equity", "commodity"):
                    cell.fill = green_fill if v > 0 else (red_fill if v < 0 else PatternFill())
                else:
                    cell.fill = red_fill if v > 0 else (green_fill if v < 0 else PatternFill())

        # Auto-size columns
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 35)

        ws.freeze_panes = "A2"
        wb.save(path)
        logger.info("XLSX → %s", path)


def _fmt(v) -> object:
    """Format a cell value: None → empty string, float → kept as float."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return v
