from abc import ABC, abstractmethod
import random
from typing import Any
from fuzze.grammars import (
    Grammar,
    decompose_in_expansions,
    is_at_least_once,
    is_expandable,
    is_many,
    is_optional,
)
from fuzze.grammars.types import DerivationTree, Expansion


class GrammarBasedFuzzerBase(ABC):
    def __init__(self, grammar: Grammar) -> None:

        self._grammar = grammar
        self._tree: DerivationTree

    def fuzz(self, treshold=-1) -> DerivationTree:
        """Fuzzes the grammar. If treshold is -1, it will fuzz until there are no more expansions.

        Args:
            treshold (int, optional): The treshold of expansions. Defaults to -1 (= no control over the max number of iterations).

        Returns:
            DerivationTree: The fuzzed grammar as a derivation tree
        """
        self._tree = DerivationTree(self._grammar.start_symbol, None)
        return self._expand(treshold)

    @abstractmethod
    def _expand(self, treshold=-1) -> DerivationTree:
        """Expands the grammar until treshold is reached or there are no more expansions.
        If treshold is -1, it will expand until there are no more expansions."""

    def _expand_once(self, rule: str) -> list[DerivationTree] | None:
        """Expands the given rule once.

        Args:
            rule (str): The rule to expand

        Returns:
            DerivationTree: The expanded rule as a derivation tree
        """
        if rule[-1] in "*+?":
            ls = self._expand_macro(rule)
            return ls if len(ls) > 0 else None

        expansions = self._get_expansions(rule)
        selected_expansion = self._select_expansion(expansions)
        self._additionnal_actions(rule, selected_expansion)
        if isinstance(selected_expansion, str):
            return self._str_to_tree(selected_expansion)
        else:
            return self._str_to_tree(selected_expansion[0])

    @abstractmethod
    def _get_expansions(self, rule: str) -> list[Expansion]:
        """Retrieves the expansions for a rule in a way which is specific to the subclass.

        Args:
            rule (str): The rule to get the expansions for

        Returns:
            list[Expansion]: The expansions of the given rule (using the subclass specific way of getting them)
        """

    @abstractmethod
    def _select_expansion(self, expansions: list[Expansion]) -> Expansion:
        """
        Selects an expansion from the given list of expansions in a way which is specific to the subclass it is implemented in.

        Args:
            expansions (list[Expansion]): The expansions to select from

        Returns:
            Expansion: The selected expansion (using the subclass specific way of selecting it)
        """

    @abstractmethod
    def _additionnal_actions(self, rule: str, chosen: Expansion) -> Any:
        """Performs additionnal actions inside expand once method when the next expansion is chosen for the given rule.
        The return value is not used.

        Args:
            rule (str): The rule to expand
            chosen (Expansion): The chosen expansion

        Returns:
            Any: The return value is not used.
        """
        ...

    def _expand_many(
        self, rule: str, min: int = 0, max: int = 10, **_
    ) -> list[DerivationTree]:
        """Expands the given rule a random number of times between min and max.
        Preconditions:
            - min must be >= 0
            - max must be >= 0
            - min <= max.

        Args:
            rule (str): The rule to expand
            min (int, optional): The minimum number of expansions. Defaults to 0.
            max (int, optional): The maximum number of expansions. Defaults to 10.

        Returns:
            list[DerivationTree]: The expanded rule (1 level deep)
        """
        assert min >= 0
        assert max >= 0
        assert min <= max
        assert rule in self._grammar
        num_expansions = random.randint(min, max)
        result: list = []
        for _ in range(num_expansions):
            r = self._expand_once(rule)
            if r is not None:
                result.extend(r)
        return result

    def _expand_at_least_once(
        self, rule: str, min: int = 1, max: int = 10, **_
    ) -> list[DerivationTree]:
        """Expands the given rule at least once and at most max times. max and min must be >= 1.

        Args:
            rule (str): The rule to expand
            max (int, optional): The maximum number of expansions. Defaults to 10.

        Returns:
            list[DerivationTree]: The expanded rule (1 level deep)
        """
        assert min >= 1
        return self._expand_many(rule, min, max)

    def _expand_optional(self, rule: str, **_) -> list[DerivationTree]:
        """Expands the given rule 0 or 1 times.

        Args:
            rule (str): The rule to expand

        Returns:
            list[DerivationTree]: The expanded rule (1 level deep)
        """
        return self._expand_many(rule, 0, 1)

    def __getitem__(self, __key: str) -> list[Expansion]:
        """Queries the grammar for the given key.
        The key can be either a rule name (<name>) or a rule name with a macro (*, +, ?).

        Args:
            __key (str): The key to query the grammar for.

        Returns:
            list[Expansion]: The expansions of the given key.
        """

        return self._grammar[__key]

    def _expand_macro(self, rule: str, **kwargs) -> list[DerivationTree]:
        """Expands the given rule with a macro (*, +, ?).

        Args:
            rule (str): The rule to expand

        Returns:
            list[str]: The expanded rule

        Raises:
            ValueError: If the macro is not recognized
        """
        if is_many(rule):
            return self._expand_many(rule[:-1], **kwargs)
        elif is_at_least_once(rule):
            return self._expand_at_least_once(rule[:-1], **kwargs)
        elif is_optional(rule):
            return self._expand_optional(rule[:-1], **kwargs)
        else:
            raise ValueError(f"Unrecognized macro in rule {rule}")

    def _str_to_tree(
        self,
        s: str,
    ) -> list[DerivationTree]:
        """Converts a string to a derivation tree with the given name.


        Args:
            s (str): The string to convert

        Returns:
            DerivationTree: The derivation tree
        """

        def _to_tree(s: str) -> DerivationTree:
            if not is_expandable(s):
                return DerivationTree(s, [])
            return DerivationTree(s, None)

        return [_to_tree(c) for c in decompose_in_expansions(s)]

    @property
    def tree(self) -> DerivationTree:
        """The last derivation tree generated by the fuzzer."""
        return self._tree

    @abstractmethod
    def reset(self) -> None:
        """Resets the fuzzer to its initial state if any."""
        ...
