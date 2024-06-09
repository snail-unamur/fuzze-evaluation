import random
from typing import Self, Sequence
from fuzze.tours.fuzz_pickers import PickerABC


class SamplePicker(PickerABC):
    """Picker to fuzz the input by sampling k indexes from a sequence of integers."""

    def __init__(self, number: int, population: Sequence[int], k) -> None:
        assert k <= len(population)
        assert k > 0
        super().__init__(number)
        self.samples = random.sample(population, k)

    def __call__(self, *args, **kwargs) -> bool:
        return kwargs.get("index", -1) in self.samples

    @classmethod
    def from_range(cls, number: int, max: int, k: int) -> Self:
        """Factory method to create a SamplePicker from
        a range ([0 to max[) of integers reprensting indexes where to fuzz the input.

        Args:
            number (int): The number of fuzzes to perform
            max (int): The maximum value of the range
            k (int): The number of indexes to sample

        Returns:
            SamplePicker: The created SamplePicker

        Raises:
            AssertionError: If the maximum value is less than or equal to 0
            AssertionError: If the number of indexes to sample is greater than the maximum value
        """
        assert max > 0
        assert k <= max
        return cls(number, range(max), k)
