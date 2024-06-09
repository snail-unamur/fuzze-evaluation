from collections import defaultdict
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
import json


@dataclass(frozen=True)
class FuzzDataObject:
    name: str
    index: int
    step: str
    fuzz: str
    original: str


@dataclass(frozen=True)
class FailedData:
    tour: str
    step: str
    data: list[FuzzDataObject] = field(default_factory=list)


@dataclass(frozen=True)
class Report:
    total_fuzzed: int
    failed_fuzzed: int
    date: str
    failed: list[FailedData] = field(default_factory=list)


def extract(path) -> Report:
    with open(path) as f:
        data = json.load(f)
        failed = []
        for tour in data["failed"]:
            failed_data = []
            for step in tour["data"]:
                failed_data.append(FuzzDataObject(**step))
            failed.append(
                FailedData(tour=tour["tour"], step=tour["step"], data=failed_data)
            )
        return Report(
            total_fuzzed=data["total_fuzzed"],
            failed_fuzzed=data["failed_fuzzed"],
            date=data["date"],
            failed=failed,
        )


def main():
    all_strat = extract("./data/all-strategy/report/report_2024-05-21_0.json")
    random_strat = extract("./data/random-strategy/report/report_2024-05-22_0.json")
    sample_strat = extract("./data/sample-strategy/report/report_2024-05-24_0.json")

    select_strat = extract("./data/select-strategy/report/report_2024-04-26_0.json")

    fig, ax = plt.subplots(figsize=(8, 8))
    plt.subplots_adjust(bottom=0.7)

    steps = defaultdict(int)
    for failed in select_strat.failed:
        steps[failed.step] += 1

    data = [(k, (v / select_strat.failed_fuzzed) * 100) for k, v in steps.items()]

    ax.bar(*zip(*data), edgecolor="black")
    plt.xlabel("Trigger")
    plt.ylabel("Pourcentage (%)")
    plt.title(
        """Proportion de chaque "trigger" parmi les tours ayant échoué pour la stratégie 2"""
    )
    plt.xticks(rotation=90)
    plt.show()


if __name__ == "__main__":
    main()
