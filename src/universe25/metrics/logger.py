"""Parquet metrics logger (pyarrow)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


class MetricsLogger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rows: list[dict[str, Any]] = []
        self._writer: pq.ParquetWriter | None = None

    def log(self, row: dict[str, Any]) -> None:
        self._rows.append(row)
        if len(self._rows) >= 64:
            self._flush()

    def _flush(self) -> None:
        if not self._rows:
            return
        table = pa.Table.from_pylist(self._rows)
        if self._writer is None:
            self._writer = pq.ParquetWriter(self.path, table.schema, compression="zstd")
        self._writer.write_table(table)
        self._rows.clear()

    def close(self) -> None:
        self._flush()
        if self._writer is not None:
            self._writer.close()
            self._writer = None
