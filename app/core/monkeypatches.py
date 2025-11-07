from __future__ import annotations

import sys
from typing import Any, Union

import sqlalchemy.util.typing as sa_typing


if sys.version_info >= (3, 14):
    _original_make_union = sa_typing.make_union_type

    def _patched_make_union_type(*types: Any):  # type: ignore[override]
        try:
            return _original_make_union(*types)
        except TypeError:
            union: Any = types[0]
            for typ in types[1:]:
                union = union | typ  # type: ignore[operator]
            return union

    sa_typing.make_union_type = _patched_make_union_type  # type: ignore[assignment]
