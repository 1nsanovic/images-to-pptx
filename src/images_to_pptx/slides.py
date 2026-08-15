from __future__ import annotations

import re
from pathlib import Path

SLIDE_PATTERN = re.compile(r"^slide-(\d+)\.png$")


def list_slide_images(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    items: list[tuple[int, Path]] = []
    for path in directory.iterdir():
        match = SLIDE_PATTERN.match(path.name)
        if match and path.is_file():
            items.append((int(match.group(1)), path))
    items.sort(key=lambda item: item[0])
    return [path for _, path in items]


def next_slide_number(directory: Path) -> int:
    numbers: list[int] = []
    if directory.is_dir():
        for path in directory.iterdir():
            match = SLIDE_PATTERN.match(path.name)
            if match:
                numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1
