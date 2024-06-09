from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Generic, TypeVar


# Based on the grammar format used in the fuzzingbook. See https://www.fuzzingbook.org/html/Grammars.html
# Allow to pass kwargs to the expansion (useful for generating)
Parametrized_Expansion = tuple[str, dict[str, Any]]

# Grammar expansion
Expansion = str | Parametrized_Expansion
GrammarDict = dict[str, list[Expansion]]
ImmutableGrammar = MappingProxyType[str, list[Expansion]]


@dataclass
class Node:
    name: str
    children: list[Node] | None = None
    parent: Node | None = None

    def __str__(self) -> str:
        if self.children is None:
            return ""
        if len(self.children) == 0:
            return self.name
        return f"{''.join(map(str, self.children))}"

    def toString(self) -> str:
        return self.__str__()

    def depth(self) -> int:
        if self.children is None:
            return 0
        return 1 + max([child.depth() for child in self.children])


# Derivation tree
DerivationTree = Node
