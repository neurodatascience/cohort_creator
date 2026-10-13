"""General utilities."""

from pathlib import Path

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


def glob_files(pth: Path, pattern: str) -> list[Path]:
    """Glob paths in a dataset, ignoring macOS metadata files (``._*``)."""
    return [
        x
        for x in pth.glob(pattern)
        if not any(part.startswith("._") for part in x.relative_to(pth).parts)
    ]


def list_participants_in_dataset(data_pth: Path) -> list[str]:
    return sorted([x.name for x in data_pth.iterdir() if x.is_dir() and x.name.startswith("sub-")])


def progress_bar(text: str, color: str = "green") -> Progress:
    return Progress(
        TextColumn(f"[{color}]{text}"),
        SpinnerColumn("dots"),
        TimeElapsedColumn(),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    )
