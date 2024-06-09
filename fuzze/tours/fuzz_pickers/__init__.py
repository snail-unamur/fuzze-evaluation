from abc import ABC, abstractmethod


class PickerABC(ABC):

    def __init__(self, number: int) -> None:
        super().__init__()
        assert number > 0
        self._number = number

    @abstractmethod
    def __call__(self, index: int, *args, **kwargs) -> bool: ...

    @property
    def number_of_fuzzes(self) -> int:
        return self._number


class PickAll(PickerABC):
    def __call__(self, index: int, *args, **kwargs) -> bool:
        return True
