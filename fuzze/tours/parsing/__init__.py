from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
import random
import re
from typing import Iterator, Literal, NamedTuple
import json
import logging
import re
from fuzze.tours.parsing.generated.JavaScriptParser import JavaScriptParser
from fuzze.tours.fuzz_pickers import PickerABC
from fuzze.fuzzers.tour import TourInputsFuzzer
from fuzze.tours.parsing.generated.JavaScriptParserVisitor import (
    JavaScriptParserVisitor,
)

logger = logging.getLogger(__name__)


class FuzzData(NamedTuple):
    name: str
    index: int  # type: ignore
    step: str
    fuzz: str
    original: str


RE_STR_CONTENT = re.compile(r"""^["'`](.*)["'`]$""")


def str_content(s: str) -> str:
    match = RE_STR_CONTENT.match(s)
    if match is not None:
        return match.group(1)
    return s


class FuzzedTourData:
    def __init__(
        self, data: dict[str, list[FuzzData]] | None = None, path: str | None = None
    ) -> None:
        self.__path: str | None = path
        if path is not None:
            self.filename = Path(path).name
        if data is None:
            self.data: dict[str, list[FuzzData]] = defaultdict(list)
        else:
            self.data: dict[str, list[FuzzData]] = defaultdict(list, **data)

    def to_json(self):
        return {
            **self.__fuzz_data_json(),
            "path": self.__path,
            "filename": self.filename,
        }

    def __fuzz_data_json(self):
        return {k: [d._asdict() for d in v] for k, v in self.data.items()}

    def __repr__(self) -> str:
        return str((str(dict(self.data)), self.__path, self.filename))

    @property
    def path(self):
        return self.__path

    @path.setter
    def path(self, path: str):
        self.__path = path
        self.filename = Path(path).name


class FuzzedFilesDataCollection(dict[str, FuzzedTourData]):
    def save(self, path):
        with open(path, "w") as f:
            encoded = {k: v.to_json() for k, v in self.items()}
            json.dump(encoded, f, indent=4)

    def to_json(self):
        for k, v in self.items():
            yield v.to_json()

    def __repr__(self) -> str:
        return str({k: v for k, v in self.items()})


TEXT_MACRO_PATTERN = re.compile(r"""^["']text (.*)["']$""")
ODOO_MODULE = "/** @odoo-module **/\n"
CONTAINS_QUERY_PATTERN = re.compile(r""":contains\(['"](.+?)["']\)""")


class FuzzTourTextVisitor(JavaScriptParserVisitor):
    def __init__(
        self, tour_name: str, strategy: PickerABC, seeds: list[str] | None = None
    ) -> None:
        """Fuzz the text of a tour.


        Args:
            tour_name (str): The name of the tour to fuzz.
            strategy (PickerABC): A callable class that returns whether the given input should be fuzzed.
        """
        super().__init__()
        self.fuzz_nb = strategy.number_of_fuzzes
        self.fuzzer = TourInputsFuzzer()
        self.tour_name = tour_name
        self.fuzz_now = False
        self.strategy = strategy
        self.index = 0
        self.seeds = seeds
        self._fuzz_data: FuzzedFilesDataCollection = FuzzedFilesDataCollection(
            {
                f"fuzz_{self.tour_name}_{f_index}": FuzzedTourData(
                    data=defaultdict(list)
                )
                for f_index in range(self.fuzz_nb)
            }
        )
        self.last_trigger = ""
        self.symbols: dict[str, tuple[str, ...]] = {}

    def visitProgram(self, ctx):
        return self.__concatenate(
            self.__to_tuple(ODOO_MODULE), super().visitProgram(ctx)
        )

    def visitPropertyExpressionAssignment(
        self, ctx: JavaScriptParser.PropertyExpressionAssignmentContext
    ) -> tuple[str, ...]:
        if (
            self.fuzz_now
            and ctx.propertyName().getText() == "run"
            and (match := TEXT_MACRO_PATTERN.match(ctx.singleExpression().getText()))
            is not None
        ):
            logger.debug(f"Matched text macro: {match.group(1)}")
            escaped = self.__escape_quotes(match.group(1))
            r = self.__transform(escaped)

            self.index += 1
            return r
        if ctx.propertyName().getText() == "trigger":
            self.last_trigger = str_content(ctx.singleExpression().getText())
            mutated = self.__mutate_trigger(self.last_trigger)

            return mutated
        if ctx.propertyName().getText() == "extra_trigger":
            content = str_content(ctx.singleExpression().getText())
            mutated = self.__mutate_trigger(content, "extra_trigger")
            return mutated
        return super().visitPropertyExpressionAssignment(ctx)

    def __mutate_trigger(self, txt: str, key="trigger") -> tuple[str, ...]:
        tmp = list(self.__to_tuple(f'{key}: "{self.__replace(txt)}"'))

        def _escape(txt: str) -> str:
            return txt.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")

        for k, v in self.symbols.items():
            for f_i, src in enumerate(tmp):
                tmp[f_i] = self.__replace_in_trigger(src, k, _escape(v[f_i]))

        return tuple(tmp)

    def __replace_in_trigger(self, txt, src_sym: str, repl_sym: str) -> str:
        contains = re.sub(
            rf""":contains\(['"]?{src_sym}["']?\)""",
            f""":contains('{repl_sym}')""",
            txt,
        )
        return re.sub(
            rf"""\[data-tooltip\*=["']?{src_sym}["']?\]""",
            f"""[data-tooltip*='{repl_sym}']""",
            contains,
        )

    def __replace(self, txt: str) -> str:
        return txt.replace('"', "'")

    def __escape_quotes(self, txt: str) -> str:
        return re.sub(r"""(['"])""", r"\\\1", txt)

    def visitArgumentsExpression(
        self, ctx: JavaScriptParser.ArgumentsExpressionContext
    ):
        name_expr: JavaScriptParser.SingleExpressionContext = ctx.singleExpression()  # type: ignore
        args_expr: JavaScriptParser.ArgumentsContext = ctx.arguments()  # type: ignore
        args: list[JavaScriptParser.ArgumentContext] = args_expr.argument()  # type: ignore

        # Sometimes there are multiple tours in the same file, we want to fuzz only one that is designated in the test
        if name_expr.getText().endswith("add"):
            self.fuzz_now = self.tour_name == str_content(args[0].getText())

        return super().visitArgumentsExpression(ctx)

    def visitChildren(self, node) -> tuple[str, ...]:
        return self.__concatenate(
            *(child.accept(self) for child in node.getChildren() if child is not None)
        )

    def defaultResult(self) -> tuple[str, ...]:  # type: ignore
        return tuple("" for _ in range(self.fuzz_nb))

    def visitTerminal(self, node) -> tuple[str, ...]:
        if node.getText() == "<EOF>":
            return self.defaultResult()
        if key := self.__contains_symbol(node.getText()):
            return tuple(self.__replace_symbol(node.getText(), key, self.symbols[key]))
        ctn = str_content(node.getText())
        if self.fuzz_now and ctn == self.tour_name:
            return tuple(f"'{self.__f_name(i)}'" for i in range(self.fuzz_nb))
        return self.__to_tuple(node.getText())

    def __replace_symbol(
        self, txt: str, sym: str, reps: Iterable[str]
    ) -> Iterator[str]:
        for r in reps:
            yield txt.replace(sym, r)

    def __contains_symbol(self, r: str) -> Literal[False] | str:
        for k in self.symbols.keys():
            if k in r:
                return k
        return False

    def __concatenate(self, *r: tuple[str, ...]) -> tuple[str, ...]:
        texts = ["" for _ in range(self.fuzz_nb)]
        for i in range(self.fuzz_nb):
            texts[i] += " ".join(r[j][i] for j in range(len(r)))
        return tuple(texts)

    def aggregateResult(
        self, aggregate: tuple[str, ...], nextResult: tuple[str, ...]
    ) -> tuple[str, ...]:
        return self.__concatenate(aggregate, nextResult)

    def visitTemplateStringLiteral(self, ctx):
        return self.__to_tuple(ctx.getText())

    def __to_tuple(self, r: str) -> tuple[str, ...]:
        return tuple(r for _ in range(self.fuzz_nb))

    def __transform(self, r: str) -> tuple[str, ...]:
        # If the symbol is already in the symbols and it has been fuzzed, return it
        existing: tuple[str, ...] | None = self.symbols.get(r)
        self.fuzzer.reset()
        if existing is not None:
            for f_i, e in enumerate(existing):
                self.__add_fuzz_data(
                    f_i,
                    FuzzData(
                        fuzz=e,
                        original=r,
                        index=self.index,
                        name=self.tour_name,
                        step=self.last_trigger,
                    ),
                )
            return tuple(self.__fmt_run(existing))
        # Otherwise, let the strategy decide if we should fuzz it
        if self.strategy(index=self.index, text=r):
            f = tuple(self.__make_fuzz(r))
            text = tuple(self.__fmt_run(f))
        else:
            f = self.__to_tuple(r)
            text = tuple(self.__fmt_run(f))
        self.symbols[r] = f
        return text

    def __fmt_run(self, iter: Iterator[str] | Iterable[str]):
        return (f'run: "text {e}"' for e in iter)

    def __make_fuzz(self, r: str):

        for f_index in range(self.fuzz_nb):
            if self.seeds is not None:
                f = random.choice(self.seeds)
            else:
                f = self.__escape_quotes(self.fuzzer.fuzz(r))
            self.__add_fuzz_data(
                f_index,
                FuzzData(
                    fuzz=f,
                    original=r,
                    index=self.index,
                    name=self.tour_name,
                    step=self.last_trigger,
                ),
            )

            yield f

    def __add_fuzz_data(self, f_index: int, f_data: FuzzData):
        self._fuzz_data[f"fuzz_{self.tour_name}_{f_index}"].data[
            self.last_trigger
        ].append(f_data)

    @property
    def fuzz_data(self):
        return self._fuzz_data

    def __f_name(self, f_index: int):
        return format_tour_name(
            self.tour_name,
            f_index,
        )


def format_tour_name(
    tour_name: str,
    f_index: int,
) -> str:
    return f"fuzz_{tour_name}_{f_index}"
