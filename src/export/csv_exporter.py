"""CSV出力モジュール

日本語を含むデータをExcelで正しく表示できるCSV形式で出力する。
BOM付きUTF-8エンコーディングを使用して文字化けを防止する。
"""

import csv
import io
from pathlib import Path


# Excel で UTF-8 CSV を正しく認識させるための BOM
UTF8_BOM = "\ufeff"


def export_csv(
    rows: list[dict[str, str]],
    filepath: str | Path,
    encoding: str = "utf-8-sig",
) -> Path:
    """データをCSVファイルとして出力する。

    Args:
        rows: 辞書のリスト。各辞書のキーがヘッダーとなる。
        filepath: 出力先ファイルパス。
        encoding: 文字エンコーディング。デフォルトは utf-8-sig（BOM付きUTF-8）。

    Returns:
        出力されたファイルのPathオブジェクト。
    """
    if not rows:
        raise ValueError("出力するデータが空です")

    filepath = Path(filepath)
    fieldnames = list(rows[0].keys())

    with open(filepath, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def export_csv_string(
    rows: list[dict[str, str]],
) -> str:
    """データをCSV文字列として返す（BOM付き）。

    Args:
        rows: 辞書のリスト。各辞書のキーがヘッダーとなる。

    Returns:
        BOM付きUTF-8のCSV文字列。
    """
    if not rows:
        raise ValueError("出力するデータが空です")

    fieldnames = list(rows[0].keys())
    output = io.StringIO()
    output.write(UTF8_BOM)

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue()
