"""패널에서 `T.spt(...)`로 굳은 stylesheet 를 루트 pt 변경 시 다시 적용."""

from __future__ import annotations

from collections.abc import Callable


class TypographyStyleBundle:
    __slots__ = ("_fns",)

    def __init__(self) -> None:
        self._fns: list[Callable[[], None]] = []

    def add(self, fn: Callable[[], None]) -> None:
        self._fns.append(fn)

    def apply(self) -> None:
        for fn in self._fns:
            fn()
