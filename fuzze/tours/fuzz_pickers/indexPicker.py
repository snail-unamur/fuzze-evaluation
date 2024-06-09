from typing import Any, Collection, Self
import itertools as it
import functools as ft

from fuzze.tours.fuzz_pickers import PickerABC


class SelectIndexPicker(PickerABC):
    def __init__(
        self,
        number: int,
        include: Collection[int],
    ) -> None:
        super().__init__(number)
        self.include = include
        # Add an indented block of code here

    def __call__(self, *args: Any, **kwds: Any) -> bool:
        """Return True if the given index is in the includes, False otherwise."""
        idx = kwds.get("index", -1)
        return idx in self.include

    @classmethod
    def combinations(
        cls, number: int, indexes: Collection[int], *args: Any, **kwds: Any
    ) -> tuple[Self, ...]:
        """Factory method to create all possible combinations of the given indexes.

        Args:
            indexes (Collection[int]): The indexes to create the combinations from

        Returns:
            list[Self]: The created pickers for all possible combinations of the given indexes
        """

        def _f(acc: list[tuple[int, ...]], e: it.combinations):
            return acc + list(e)

        return tuple(
            cls(number, col, *args, **kwds)
            for col in ft.reduce(
                _f,
                list(it.combinations(indexes, i) for i in range(1, len(indexes) + 1)),
                [],
            )
        )


class ExcludeIndexPicker(PickerABC):
    def __init__(self, number: int, exclude: Collection[int]) -> None:
        super().__init__(number)
        self.exclude = exclude

    def __call__(self, *args: Any, **kwds: Any) -> bool:
        """Return True if the given index is not in the excludes, False otherwise."""
        idx = kwds.get("index", -1)
        return idx not in self.exclude
