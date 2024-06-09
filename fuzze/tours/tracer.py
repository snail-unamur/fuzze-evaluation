import datetime
import json
from pathlib import Path
from fuzze.tours.parsing import FuzzedFilesDataCollection


class FuzzeTracer:
    def __init__(self, fuzz_data: FuzzedFilesDataCollection) -> None:
        self._trace = []
        self._fuzz_data = fuzz_data

    def trace(self, tour: str, step: str):
        self._trace.append((tour, step))

    def __str__(self):
        return str(self._trace)

    def save(self, path: Path | str):
        path = Path(path)
        counter = 0
        p = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        while p.exists():
            p = path.with_name(f"{path.stem}_{counter}{path.suffix}")
            counter += 1
        with open(p, "w") as f:
            f.write(json.dumps(self._make_dict()))

    def _make_dict(self):
        return {
            "failed": [
                {
                    "tour": tour,
                    "step": step,
                    "data": tuple(
                        d._asdict() for d in self._fuzz_data[tour].data[step]
                    ),
                }
                for tour, step in self._trace
            ],
            "date": datetime.datetime.now(datetime.UTC).isoformat(),
            "total_fuzzed": len(self._fuzz_data),
            "failed_fuzzed": len(self._trace),
        }
