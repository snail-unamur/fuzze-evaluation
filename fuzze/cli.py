from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from simple_parsing import ArgumentParser

from fuzze import fuzz
from fuzze.tours.fuzz_pickers import PickAll
from fuzze.tours.fuzz_pickers.gaussianPicker import GaussianPicker
from fuzze.tours.fuzz_pickers.indexPicker import ExcludeIndexPicker, SelectIndexPicker
from fuzze.tours.fuzz_pickers.samplePicker import SamplePicker

s = "all", "index", "random", "sample"

StrategyType = Literal["all", "index", "random", "sample"]


@dataclass
class SourceData:
    tour_name: str
    source: Path


@dataclass
class IndexOptions:
    # Indices to include
    include: tuple[int, ...] = field(default_factory=lambda: tuple())
    # Indices to exclude
    exclude: tuple[int, ...] = field(default_factory=lambda: tuple())

    def __post_init__(self):
        assert bool(self.include) or bool(
            self.exclude
        ), "Either the includes or the excludes indices must be given in index strategy"


@dataclass
class SampleOptions:
    # Indices to base the samples on
    include: tuple[int, ...] = field(default_factory=lambda: tuple())
    # Number of indices to include in samples
    k: int = 0


@dataclass
class GeneralOptions:
    def __post_init__(self):
        assert self.iterations > 0, "The number of iterations must be greater than 0."
        assert self.strategy in s, "Unknown strategy"
        if self.strategy == "index":
            assert (
                self.indexStrategy is not None
            ), "Index strategy must be provided when using index strategy"

        if self.strategy == "sample":
            assert (
                self.sampleStrategy is not None
            ), "Sample strategy must be provided when using sample strategy"

    # The fuzzing strategy to use:
    # - all: fuzz all inputs
    # - random: randomly select text to fuzz
    # - index: specific indices (must provide IndexOptions)
    # - sample: sample indices (must provide SampleOptions)
    strategy: StrategyType
    # Number of fuzzs to make
    iterations: int
    # Name of the tour
    name: str
    # Base path of the source tour file
    source: Path
    # Base path of the destination addon
    destination: Path
    # Index strategy options
    indexStrategy: IndexOptions | None = field(default_factory=lambda: None)
    # Sample strategy options
    sampleStrategy: SampleOptions | None = field(default_factory=lambda: None)
    # Whether to clean the destination directory before copying the files
    clean: bool = False


def main():
    parser = ArgumentParser()
    parser.add_arguments(GeneralOptions, dest="Options")
    args = parser.parse_args()
    options: GeneralOptions = args.Options
    if options.strategy == "all":
        strategy_class = PickAll(options.iterations)
    elif options.strategy == "random":
        strategy_class = GaussianPicker(options.iterations)
    elif options.strategy == "index":
        assert options.indexStrategy is not None
        if bool(options.indexStrategy.include):
            strategy_class = SelectIndexPicker(
                options.iterations, options.indexStrategy.include
            )
        elif bool(options.indexStrategy.exclude):
            strategy_class = ExcludeIndexPicker(
                options.iterations, options.indexStrategy.exclude
            )
        else:
            raise ValueError(
                "You must provide a value for include or exclude when using the index strategy"
            )
    elif options.strategy == "sample":
        assert options.sampleStrategy is not None
        assert options.sampleStrategy.include is not None
        strategy_class = SamplePicker(
            options.iterations, options.sampleStrategy.include, options.sampleStrategy.k
        )
    else:
        raise ValueError("Unknown strategy")
    fuzz(
        options.name, options.source, options.destination, strategy_class, options.clean
    )
