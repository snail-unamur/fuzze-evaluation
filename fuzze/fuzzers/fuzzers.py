import logging
import random

from .bases import GrammarBasedFuzzerBase
from .cost_estimators import CostTraceDict, GrammarCostEstimator
from fuzze.grammars import (
    Grammar,
    get_expansion,
    is_expandable,
)
from fuzze.grammars.types import DerivationTree, Expansion
from fuzze.grammars import Grammar

logger = logging.getLogger(__name__)


class GrammarCostBasedFuzzer(GrammarBasedFuzzerBase):
    """
    A fuzzer that uses a grammar to generate strings. The expansions are chosen based on a cost estimator.
    """

    _logger = logging.getLogger(__name__ + ".DummyGrammarBasedFuzzer")

    def __init__(
        self,
        grammar: Grammar,
        cost_estimator: GrammarCostEstimator[CostTraceDict],
        max_expansion_treshold=50,
        min_expansion_treshold=100,
    ) -> None:
        super().__init__(grammar)
        self._max_expansion_treshold = max_expansion_treshold
        self._min_expansion_treshold = min_expansion_treshold
        self._estimations = cost_estimator.make_estimation()
        self._fitness = 0
        self._fitness_estimate = cost_estimator.fitness

    def _expand(self, treshold=-1) -> DerivationTree:
        exp_number = 0
        worklist = [self._tree]
        while (len(worklist) > 0) and treshold < exp_number:
            current = worklist.pop(0)
            self._fitness = self._fitness_estimate(tree=self._tree)
            if current.children is None:
                current.children = self._expand_once(current.name)
                # Means that we encountered an optional expansion which was not expanded
                if current.children is None:
                    continue
            for child in current.children:
                if is_expandable(child.name):
                    worklist.append(child)

            exp_number += 1
        return self._tree

    def _get_expansions(self, rule: str):
        if self._fitness < self._max_expansion_treshold:
            indices = self._estimations[rule]["max"][1]
        elif self._fitness >= self._min_expansion_treshold:
            indices = self._estimations[rule]["min"][1]
        else:
            return self._grammar[rule]
        return [e for i, e in enumerate(self._grammar[rule]) if i in indices]

    def _select_expansion(self, expansions: list[Expansion]) -> Expansion:
        return random.choice(expansions)

    def _additionnal_actions(self, rule: str, chosen: Expansion):
        return None

    def _expand_macro(self, rule, **_):
        mini: int = max(0, self._min_expansion_treshold - self._fitness)
        maxi = max(mini, self._max_expansion_treshold - self._fitness)
        return super()._expand_macro(rule, min=mini, max=maxi)

    def reset(self) -> None:
        return None


class DummyGrammarBasedFuzzer(GrammarBasedFuzzerBase):
    """
    A fuzzer that uses a grammar to generate strings.The expansions are chosen randomly.
    """

    _logger = logging.getLogger(__name__ + ".DummyGrammarBasedFuzzer")

    def _get_expansions(self, rule: str) -> list[Expansion]:
        return self[rule]

    def _select_expansion(self, expansions: list[Expansion]) -> Expansion:
        return random.choice(expansions)

    def _expand(self, treshold=-1) -> DerivationTree:
        exp_number = 0
        worklist = [self._tree]
        while (len(worklist) > 0) and treshold < exp_number:
            current = worklist.pop(0)
            if current.children is None:
                current.children = self._expand_once(current.name)
                # Means that we encountered an optional expansion which was not expanded
                if current.children is None:
                    continue
            for child in current.children:
                if is_expandable(child.name):
                    worklist.append(child)

            exp_number += 1
        return self._tree

    def reset(self) -> None:
        return None


class CoverageGrammarFuzzer(GrammarBasedFuzzerBase):
    """
    A fuzzer that uses a grammar to generate strings. The fuzzer will try to maximize the coverage of the grammar.
    """

    _logger = logging.getLogger(__name__ + ".CoverageGrammarFuzzer")

    def __init__(self, grammar: Grammar, min_length=1) -> None:
        super().__init__(grammar)
        self._min_length = min_length
        self._covered_exp = set()
        self.__possible_expansions = self.__gen_all_expansions()

    def _expand(self, treshold=-1) -> DerivationTree:
        exp_number = 0
        worklist = [self._tree]
        while len(worklist) > 0 and treshold < exp_number:
            current = worklist.pop(0)
            if current.children is None:
                current.children = self._expand_once(current.name)
                # Means that we encountered an optional expansion which was not expanded
                if current.children is None:
                    continue
            for child in current.children:
                if is_expandable(child.name):
                    worklist.append(child)

            exp_number += 1
        return self._tree

    def is_fully_covered(self) -> bool:
        return self._covered_exp == self.__possible_expansions

    def __gen_all_expansions(self) -> set[tuple[str, str]]:
        s = set[tuple[str, str]]()
        for rule in self._grammar.grammar.keys():
            s = s.union(self.__map_rule_to_expansions(rule))
        return s

    def __map_rule_to_expansions(
        self,
        rule: str,
    ) -> set[tuple[str, str]]:
        return set((rule, get_expansion(expansion)) for expansion in self[rule])

    def __get_uncovered_expansions(self, rule: str) -> list[Expansion]:
        def _t(x: tuple[str, str]) -> Expansion:
            return x[1]

        return list(map(_t, self.__extract_exps(rule) - self._covered_exp))

    def __extract_exps(self, rule: str) -> set[tuple[str, str]]:
        return set(filter(lambda x: x[0] == rule, self.__possible_expansions))

    def _get_expansions(self, rule: str) -> list[Expansion]:
        uncovered_expansions: list[Expansion] = self.__get_uncovered_expansions(rule)
        if len(uncovered_expansions) == 0:
            # Means that all expansions were covered at least once.
            # Then, we can just select a random expansion
            uncovered_expansions = self[rule]
        return uncovered_expansions

    def _select_expansion(self, expansions: list[Expansion]) -> Expansion:
        return random.choice(expansions)

    def _additionnal_actions(self, rule: str, chosen: Expansion):
        if isinstance(chosen, str):
            self._covered_exp.add((rule, chosen))
        else:
            self._covered_exp.add((rule, chosen[0]))

    @property
    def possible_expansions(self) -> set[tuple[str, str]]:
        return self.__possible_expansions

    @property
    def uncovered_expansions(self) -> set[tuple[str, str]]:
        return self.__possible_expansions - self._covered_exp

    @property
    def covered_expansions(self) -> set[tuple[str, str]]:
        return self._covered_exp

    @property
    def ratio_covered(self) -> float:
        """The ratio of covered expansions over the total possible expansions (in %) ."""
        return len(self._covered_exp) / len(self.__possible_expansions) * 100

    def reset(self):
        """Resets the fuzzer internal state. This will clear the working string and the covered expansions."""
        self._covered_exp = set()
        self.__possible_expansions = self.__gen_all_expansions()
        self._logger.info(f"Resetting fuzzer internal state")
