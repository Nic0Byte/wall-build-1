"""
Common types and helpers for parsing modules.
"""

from __future__ import annotations

from typing import List, Tuple

from shapely.geometry import Polygon

ParseResult = Tuple[Polygon, List[Polygon]]

__all__ = ["ParseResult"]
