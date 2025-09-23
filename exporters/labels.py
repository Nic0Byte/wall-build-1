"""Labeling helpers condivisi tra gli exporter."""

from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Tuple

from utils.config import SIZE_TO_LETTER

try:
    from block_grouping import (
        create_grouped_block_labels,
        create_block_labels_legacy as _grouping_legacy,
    )
except ImportError:  # pragma: no cover
    create_grouped_block_labels = None  # type: ignore
    _grouping_legacy = None  # type: ignore


__all__ = [
    "create_block_labels",
    "create_detailed_block_labels",
]


def create_block_labels(placed: List[Dict], custom: List[Dict]) -> Tuple[Dict[int, str], Dict[int, str]]:
    """Restituisce etichette legacy (stringhe) per blocchi standard e custom."""
    if _grouping_legacy is not None:
        return _grouping_legacy(placed, custom)
    return _create_block_labels_legacy_impl(placed, custom)


def create_detailed_block_labels(
    placed: List[Dict],
    custom: List[Dict],
    size_to_letter: Optional[Dict[int, str]] = None,
) -> Tuple[Dict[int, Dict], Dict[int, Dict]]:
    """Versione strutturata con informazioni per il layout (categoria + numero)."""
    if create_grouped_block_labels is not None:
        if size_to_letter:
            print(f"[DEBUG] create_detailed_block_labels passing custom mapping: {size_to_letter}")
        return create_grouped_block_labels(placed, custom, size_to_letter)

    if size_to_letter:
        std_labels, custom_labels = _create_block_labels_legacy_with_custom_mapping(placed, custom, size_to_letter)
    else:
        std_labels, custom_labels = _create_block_labels_legacy_impl(placed, custom)

    detailed_std: Dict[int, Dict] = {}
    detailed_custom: Dict[int, Dict] = {}

    for i, label in std_labels.items():
        category = label[0] if label else "X"
        number = label[1:] if len(label) > 1 else "1"
        detailed_std[i] = {
            "category": category,
            "number": int(number) if number.isdigit() else 1,
            "full_label": label,
            "display": {
                "bottom_left": category,
                "top_right": number,
                "type": "standard",
            },
        }

    for i, label in custom_labels.items():
        detailed_custom[i] = {
            "category": "D",
            "number": 1,
            "full_label": label,
            "display": {
                "bottom_left": "D",
                "top_right": "1",
                "type": "custom",
            },
        }

    return detailed_std, detailed_custom


def _create_block_labels_legacy_with_custom_mapping(
    placed: List[Dict],
    custom: List[Dict],
    size_to_letter: Dict[int, str],
) -> Tuple[Dict[int, str], Dict[int, str]]:
    """Implementazione legacy con mapping personalizzato dimensione->lettera."""
    std_counters: Dict[str, int] = {letter: 0 for letter in size_to_letter.values()}
    std_labels: Dict[int, str] = {}

    for i, blk in enumerate(placed):
        width = int(blk["width"])
        letter = size_to_letter.get(width, "X")
        if letter == "X":
            candidates = [(abs(width - k), v) for k, v in size_to_letter.items()]
            letter = sorted(candidates, key=lambda item: item[0])[0][1] if candidates else "X"

        std_counters.setdefault(letter, 0)
        std_counters[letter] += 1
        std_labels[i] = f"{letter}{std_counters[letter]}"

    custom_labels: Dict[int, str] = {}
    counts: DefaultDict[object, int] = defaultdict(int)

    for i, c in enumerate(custom):
        ctype = c.get("ctype", 2)
        if ctype == "out_of_spec":
            label_base = "CUX"
            key = "X"
        elif ctype in (1, 2):
            label_base = f"CU{ctype}"
            key = ctype
        else:
            label_base = "CUX"
            key = "X"
        counts[key] += 1
        custom_labels[i] = f"{label_base}({counts[key]})"

    return std_labels, custom_labels


def _create_block_labels_legacy_impl(placed: List[Dict], custom: List[Dict]) -> Tuple[Dict[int, str], Dict[int, str]]:
    """Implementazione legacy del sistema di etichettatura."""
    std_counters: Dict[str, int] = {"A": 0, "B": 0, "C": 0}
    std_labels: Dict[int, str] = {}

    for i, blk in enumerate(placed):
        width = int(blk["width"])
        letter = SIZE_TO_LETTER.get(width, "X")
        if letter == "X":
            candidates = [(abs(width - k), v) for k, v in SIZE_TO_LETTER.items()]
            letter = sorted(candidates, key=lambda item: item[0])[0][1]

        std_counters.setdefault(letter, 0)
        std_counters[letter] += 1
        std_labels[i] = f"{letter}{std_counters[letter]}"

    custom_labels: Dict[int, str] = {}
    counts: DefaultDict[object, int] = defaultdict(int)

    for i, c in enumerate(custom):
        ctype = c.get("ctype", 2)
        if isinstance(ctype, int) and ctype in (1, 2):
            key = ctype
        else:
            key = "X"
        counts[key] += 1
        custom_labels[i] = f"CU{key}({counts[key]})"

    return std_labels, custom_labels

