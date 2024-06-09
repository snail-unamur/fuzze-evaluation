import random

from fuzze.tours.fuzz_pickers import PickerABC


class GaussianPicker(PickerABC):
    def __init__(
        self, number: int, mean: float = 0, std_dev: float = 1, treshold: float = 0.0
    ) -> None:
        super().__init__(number)
        self.mean = mean
        self.std_dev = std_dev
        self.treshold = treshold

    def __call__(self, *args, **kwargs) -> bool:
        """Return a random value from a Gaussian distribution with the given mean and standard deviation."""
        return random.gauss(self.mean, self.std_dev) < self.treshold
