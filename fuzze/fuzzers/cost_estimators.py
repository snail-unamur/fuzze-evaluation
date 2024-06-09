import re
from typing import Any, Final, Literal, Protocol, TypeVar, TypedDict
from fuzze.fuzzers.cost import Cost
from fuzze.grammars import (
    get_expansion,
    has_macro,
    is_expandable,
    is_many,
    is_optional,
    rm_macro,
)

from fuzze.grammars import Grammar
from fuzze.grammars.types import DerivationTree, Expansion


T = TypeVar("T", bound=Any)


class GrammarCostEstimator(Protocol[T]):

    def make_estimation(self) -> dict[str, T]: ...

    def fitness(self, **kwargs) -> int: ...

    @property
    def grammar(self) -> Grammar: ...


# TODO Refactor this class to make it compliant with the protocol GrammarCostEstimator
class GrammarDepthCostEstimator:
    __macro_cost: Final[dict[Literal["min", "max"], dict[str, Cost]]] = {
        "min": {"*": Cost(0), "+": Cost(1), "?": Cost(0), "": Cost(1)},
        "max": {"*": Cost.inf(), "+": Cost.inf(), "?": Cost(1), "": Cost(1)},
    }

    def __init__(self, grammar: Grammar) -> None:
        assert Grammar.is_correct(grammar.grammar), "The given grammar is not correct."
        self._grammar = grammar
        for rule in self._grammar:
            self._grammar = self._grammar.add_parameters(
                rule, {"min_cost": "inf", "max_cost": 1}
            )

        self._visited: dict[str, Cost] = {}

    def estimate_min_costs(self) -> dict[str, Cost]:
        self._visited = {}
        for rule in self._grammar:
            self._rule_cost(rule, "min")
        return self._visited

    def __sum_cost(self, c1: Cost, *args: Cost) -> Cost:
        return Cost(sum([c1, *args]))

    def _rule_cost(self, rule: str, mode: Literal["min", "max"]) -> Cost:
        if rule in self._visited:
            return self._visited[rule]

        if has_macro(rule):
            rule, macro = rule[:-1], rule[-1]
            macro_cost = GrammarDepthCostEstimator.__macro_cost[mode][macro]
            if macro_cost.is_infinite():
                return Cost.inf()
            elif macro_cost == 0:
                return Cost(1)
            return self._rule_cost(rule, mode)

        if self._grammar.has_terminals_only(rule):
            self._visited[rule] = Cost(1)
            for expansion in self._grammar[rule]:
                assert isinstance(expansion, tuple)
                exp_str, params = expansion
                params[f"{mode}_cost"] = 1
            return Cost(1)
        comparator = max if mode == "max" else min
        cost = Cost(1 if mode == "max" else "inf")
        for expansion in self._grammar[rule]:
            assert isinstance(expansion, tuple)
            exp_str, params = expansion
            expansion_cost: Cost = Cost(1)
            if referenced := is_expandable(exp_str):
                for ref in referenced:
                    if ref == rule:
                        expansion_cost = Cost.inf()
                        break
                    else:
                        expansion_cost = max(
                            self.__sum_cost(self._rule_cost(ref, mode), Cost(1)),
                            expansion_cost,
                        )

            params[f"{mode}_cost"] = expansion_cost
            cost = comparator(cost, expansion_cost)
        self._visited[rule] = cost
        return cost

    def estimate_max_costs(self) -> dict[str, Cost]:
        self._visited = {}
        for rule in self._grammar:
            self._rule_cost(rule, "max")
        return self._visited

    @property
    def grammar(self) -> Grammar:
        return self._grammar


class CostDict(TypedDict):
    min: Cost
    max: Cost


class CostTraceDict(TypedDict):
    min: tuple[Cost, tuple[int, ...]]
    max: tuple[Cost, tuple[int, ...]]


class ProductionLengthEstimator(GrammarCostEstimator[CostTraceDict]):
    def __init__(self, grammar: Grammar) -> None:
        self._grammar = grammar
        self._visited: dict[str, CostTraceDict] = {}

    def make_estimation(self):
        self._eval_rule(self._grammar.start_symbol)
        return self._visited

    def _many_cost(self, rule: str) -> CostDict:
        # Make sure that the reference is visited
        if rule not in self._visited:
            self._eval_rule(rule)
        return {
            "min": Cost(0),
            "max": Cost.inf(),
        }

    def _plus_cost(self, rule: str) -> CostDict:
        return {
            "min": self._eval_rule(rule)["min"][0],
            "max": Cost.inf(),
        }

    def _opt_cost(self, rule: str) -> CostDict:
        return {
            "min": Cost(0),
            "max": self._eval_rule(rule)["max"][0],
        }

    def _eval_expansion(self, exp: Expansion, parent: str) -> CostDict:
        content: str = get_expansion(exp)
        if refs := is_expandable(content):
            sub_lengths = {}
            if parent in refs:
                refs.remove(parent)
                return {"min": Cost.inf(), "max": Cost.inf()}
            for ref in refs:
                token = rm_macro(ref)
                if has_macro(ref):
                    if is_many(ref):
                        sub_lengths[ref] = self._many_cost(rule=token)
                    elif is_optional(ref):
                        sub_lengths[ref] = self._opt_cost(rule=token)
                    else:
                        sub_lengths[ref] = self._plus_cost(rule=token)
                elif token in self._visited:
                    sub_lengths[ref] = {
                        "min": self._visited[token]["min"][0],
                        "max": self._visited[token]["max"][0],
                    }
                else:
                    sub_lengths[ref] = {
                        "min": self._eval_rule(token)["min"][0],
                        "max": self._eval_rule(token)["max"][0],
                    }
            raw_chr = re.sub(r"<[^<>]*>[\*\+\?]?", "", content)
            supp = len(raw_chr)
            return {
                "min": Cost(sum([sub_lengths[ref]["min"] for ref in refs]) + supp),
                "max": Cost(sum([sub_lengths[ref]["max"] for ref in refs]) + supp),
            }
        else:
            return {
                "min": Cost(len(content)),
                "max": Cost(len(content)),
            }

    def _get_min(self, costs: list[CostDict]) -> tuple[Cost, tuple[int, ...]]:
        mini = min(costs, key=lambda x: x["min"])
        return mini["min"], tuple(
            i for i, x in enumerate(costs) if x["min"] == mini["min"]
        )

    def _get_max(self, costs: list[CostDict]) -> tuple[Cost, tuple[int, ...]]:
        maxi = max(costs, key=lambda x: x["max"])
        return maxi["max"], tuple(
            i for i, x in enumerate(costs) if x["min"] == maxi["min"]
        )

    def _eval_rule(self, rule: str) -> CostTraceDict:
        if rule in self._visited:
            return self._visited[rule]
        costs = [self._eval_expansion(exp, rule) for exp in self._grammar[rule]]
        res: CostTraceDict = {
            "min": self._get_min(costs),
            "max": self._get_max(costs),
        }
        self._visited[rule] = res
        return res

    def fitness(self, **kwargs) -> int:
        if "tree" not in kwargs:
            raise ValueError(
                "The tree parameter is required for this estimator's fitness."
            )
        tree = kwargs.get("tree")
        if not isinstance(tree, DerivationTree):
            raise ValueError("The tree parameter must be a DerivationTree.")
        return len(tree.toString())

    @property
    def grammar(self) -> Grammar:
        return self._grammar

    @property
    def visited(self) -> dict[str, CostTraceDict]:
        return self._visited
