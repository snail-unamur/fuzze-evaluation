from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
import logging
from typing import Any, Callable, Literal, TypeVar
import re
import random

from .types import Expansion, GrammarDict, ImmutableGrammar

logger = logging.getLogger(__name__)

"""
This module contains functions to work with grammars. A grammar is a dictionary where the keys are the names 
of the rules and the values are lists of expansions. An expansion can be a string or a tuple. If it is a string,
it is a simple expansion. If it is a tuple, the first element is the expansion and the second is a dictionary with some parameters.
The second case is useful to attribute some properties to the expansion, like the depth cost of generating it.
Supported macros:
    - '*' : zero or more
    - '+' : one or more
    - '?' : zero or one
"""

T = TypeVar("T")


def expand_with_params(expansion: Expansion, func: Callable[..., str]) -> str:
    """Apply the expansion with the given parameters. If the expansion is a string, it is returned as is.
    If it is a tuple, the first element is the expansion and the second is a dictionary with the parameters to pass to the expansion.

    Args:
        expansion (Expansion): The expansion to apply
        func (Callable[..., str]): The function to apply the expansion

    Returns:
        str: The result of applying func to the expansion with the given parameters
    """
    kwargs = get_params(expansion)
    return func(expansion, **kwargs)


def expand(generated: str, grammar: GrammarDict) -> str:
    """Default expansion function. Expends first expansion matched, otherwise returns the string as is.
    If the expansion has parameters, they are ignored. If the expansion has multiple options, the used one is chosen randomly.
    """
    if matches := is_expandable(generated):
        expansion = matches.pop(0)
        macro = ""
        if expansion[-1] in "*+?":
            expansion, macro = (expansion[:-1], expansion[-1])
            # TODO: handle "macros". They are currently ignored
            if macro == "*":
                pass
            elif macro == "+":
                pass
            elif macro == "?":
                pass
        exps: list[Expansion] | None = grammar.get(expansion)
        if exps is None:
            return generated
        index = random.randint(0, len(exps) - 1)
        # Must ignore parametrized expansions
        return generated.replace(expansion + macro, exps[index] if isinstance(exps[index], str) else exps[index][0], 1)  # type: ignore
    return generated


def get_params(expansion: Expansion) -> dict[str, Any]:
    """Retrieves the parameters of the expansion. If the expansion is a string, it returns an empty dictionary.

    Args:
        expansion (Expansion): The expansion to get the parameters from

    Returns:
        dict[str, Any]: The parameters of the expansion"""
    if isinstance(expansion, str):
        return {}
    else:
        return expansion[1]


def get_expansion(expansion: Expansion) -> str:
    """Retrieves the expansion string from the given expansion. If the expansion is already a string, it is returned as is.

    Args:
        expansion (Expansion): The expansion to get the expansion from

    Returns:
        str: The expansion string from the given expansion
    """
    if isinstance(expansion, str):
        return expansion
    else:
        return expansion[0]


def char_range(start: str, end: str) -> list[Expansion]:
    """Generates a list of characters from start to end (inclusive)

    Args:
        start (str): The start character
        end (str): The end character

    Returns:
        list[str]: The list of characters from start to end (inclusive)
    """
    return [chr(i) for i in range(ord(start), ord(end) + 1)]


def num_range(start: int, end: int) -> list[Expansion]:
    """Generates a list of numbers (string) from start to end (inclusive)

    Args:
        start (int): The start number
        end (int): The end number

    Returns:
        list[str]: The list of numbers from start to end (inclusive)
    """
    return [str(i) for i in range(start, end + 1)]


def digits() -> list[Expansion]:
    """Generates a list of digits (string) from 0 to 9 (inclusive)

    Returns:
        list[str]: The list of digits from 0 to 9 (inclusive)
    """
    return num_range(0, 9)


def extend_grammar(
    name: str, expansions: list[Expansion], grammar: GrammarDict
) -> GrammarDict:
    """Extends the grammar with the given rule name with the given expansions. If the rule does not exist, it is created.

    Args:
        name (str): The name of the expansion to extend
        rules (list[str]): The rules of the expansion
        grammar (Grammar): The grammar to add the expansion to

    Returns:
        Grammar: A deepcopy of the grammar that was extended
    """
    grammar = deepcopy(grammar)
    if not (name.startswith("<") and name.endswith(">")):
        name = f"<{name}>"
    if name not in grammar:
        grammar[name] = expansions
    else:
        grammar[name].extend(expansions)
        grammar[name] = list(set(grammar[name]))
    return grammar


def remove_rule(name: str, grammar: GrammarDict) -> GrammarDict:
    """Removes the given rule from the grammar

    Args:
        name (str): The name of the rule to remove
        grammar (Grammar): The grammar to remove the rule from

    Returns:
        Grammar: The grammar with the rule removed
    """
    if name in grammar:
        del grammar[name]
    return grammar


def is_expandable(s: str) -> list[str] | Literal[False]:
    """Checks if the given string is expandable (i.e. contains a rule to expand)

    Args:
        s (str): The string to check

    Returns:
        list[str] | Literal[False]: the matches, False otherwise
    """
    matches = get_expansions(s)
    if len(matches) == 0:
        return False
    return matches


def get_expansions(s: str | Expansion) -> list[str]:
    """Retrieves the expansions from the given string.

    Args:
        s (str): The string to get the expansions from

    Returns:
        list[str]: The expansions in the given string
    """
    if isinstance(s, tuple):
        s = s[0]
    return re.findall(r"<[^<>]*>[\*\+\?]?", s)


def is_correct(grammar: GrammarDict) -> bool:
    """Check if the grammar is correctly defined. It checks that all expansions are correctly defined.
    <start> is a compulsory rule.
    Args:
        grammar (Grammar): The grammar to check

    Returns:
        bool: True if the grammar is correctly defined, False otherwise

    """
    if "<start>" not in grammar:
        return False
    for expansion in grammar.values():
        if not all(isinstance(e, str) or isinstance(e, tuple) for e in expansion):
            return False
        for e in expansion:
            if isinstance(e, tuple):
                if not isinstance(e[0], str) or not isinstance(e[1], dict):
                    return False
            else:
                if not isinstance(e, str):
                    return False
                exps = get_expansions(e)
                if exps and not all(rm_macro(exp) in grammar for exp in exps):
                    return False
    return True


def rm_macro(s: str) -> str:
    """Removes the macro from the given string

    Args:
        s (str): The string to remove the macro from

    Returns:
        str: The string without the macro
    """
    return s[:-1] if s[-1] in "*+?" else s


def has_macro(s: str) -> bool:
    """Checks if the given string has a macro

    Args:
        s (str): The string to check

    Returns:
        bool: True if the string has a macro, False otherwise
    """
    return s[-1] in "*+?"


def merge_grammars(
    g1: GrammarDict, g2: GrammarDict, priority: str = "first"
) -> GrammarDict:
    """Merges two grammars. If a rule is present in both grammars, priority is used to choose which one to keep.
    Both grammars are left unchanged and a new one is created.

    Args:
        g1 (Grammar): The first grammar
        g2 (Grammar): The second grammar
        priority (str, optional): The priority to use to choose which rule to keep. Defaults to "first". Can be "first" or "second".

    Returns:
        Grammar: The merged grammar (under a new reference)
    """
    if priority == "first":
        g2_c = {k: v for k, v in g2.items() if k not in g1}
        return deepcopy(g1) | deepcopy(g2_c)
    else:
        g1_c = {k: v for k, v in g1.items() if k not in g2}
        return deepcopy(g2) | deepcopy(g1_c)


def add_parameters(
    grammar: GrammarDict, rule: str, params: dict[str, Any]
) -> GrammarDict:
    """Adds parameters to the given rule's exapansions in the grammar

    Args:
        grammar (Grammar): The grammar to add the parameters to
        rule (str): The rule to add the parameter to
        param (dict[str, Any]): The parameter(s) to add

    Returns:
        Grammar: The grammar (deepcopied) with the parameters added
    """
    g: GrammarDict = deepcopy(grammar)
    if rule in grammar:
        new_exps = []
        for exp in grammar[rule]:
            if isinstance(exp, str):
                new_exps.append((exp, deepcopy(params)))
            else:
                new_exps.append((exp[0], deepcopy({**exp[1], **params})))
        g[rule] = new_exps
    return g


def make_all_expansion_parametrized(grammar: GrammarDict) -> GrammarDict:
    """Makes all expansions parametrized. If an expansion is not parametrized, it is transformed into a parametrized one with an empty dictionary as parameters.
    Otherwise parametrized expansions are left as is.

    Args:
        grammar (Grammar): The grammar to transform

    Returns:
        Grammar: The transformed grammar with all expansions parametrized
    """
    grammar = deepcopy(grammar)
    for rule, expansions in grammar.items():
        new_exps = []
        for exp in expansions:
            if isinstance(exp, str):
                new_exps.append((exp, {}))
            else:
                new_exps.append(exp)
        grammar[rule] = new_exps
    return grammar


def is_fully_parametrized(grammar: GrammarDict) -> bool:
    """Checks if the grammar is fully parametrized. A grammar is fully parametrized if all expansions are parametrized.

    Args:
        grammar (Grammar): The grammar to check

    Returns:
        bool: True if the grammar is fully parametrized, False otherwise
    """
    for expansions in grammar.values():
        for exp in expansions:
            if not isinstance(exp, tuple):
                return False
    return True


def is_many(s: str) -> bool:
    """Checks if the given string is a "many" expansion (i.e. ends with a '*')

    Args:
        s (str): The string to check

    Returns:
        bool: True if the string is a "many" expansion, False otherwise
    """
    return s.endswith("*")


def is_at_least_once(s: str) -> bool:
    """Checks if the given string is a "at least once" expansion (i.e. ends with a '+')

    Args:
        s (str): The string to check

    Returns:
        bool: True if the string is a "at least once" expansion, False otherwise
    """
    return s.endswith("+")


def is_optional(s: str) -> bool:
    """Checks if the given string is an "optional" expansion (i.e. ends with a '?')

    Args:
        s (str): The string to check

    Returns:
        bool: True if the string is an "optional" expansion, False otherwise
    """
    return s.endswith("?")


def get_rule(grammar: GrammarDict, rule: str) -> list[Expansion]:
    """Retrieves a rule from the given grammar. Makes sure to ignore macros symbols ('*', '+', '?')

    Args:
        grammar (Grammar): The grammar to search in
        rule (str): The rule to search for

    Returns:
        list[Espansion]: The expansions of the rule
    """

    if rule in grammar:
        return grammar[rule]
    if rule[-1] in "*+?" and rule[:-1] in grammar:
        return grammar[rule[:-1]]

    raise ValueError(f"The given rule is not a valid rule: {rule}")


def has_terminals_only(grammar: GrammarDict, rule: str) -> bool:
    """Checks if the rule has terminals only. A terminal is an expansion that does not expand to another rule.

    Args:
        grammar (Grammar): The grammar to search in
        rule (str): The rule to check

    Returns:
        bool: True if the rule is composed of terminals only, False otherwise
    """
    return all(not is_expandable(get_expansion(exp)) for exp in get_rule(grammar, rule))


def create_rule(base_name: str, grammar: GrammarDict) -> tuple[GrammarDict, str]:
    """Creates a new rule in the grammar. If the base_name is already present, it is extended with a number suffix.

    Args:
        base_name (str): The base name of the rule to create
        grammar (Grammar): The grammar to create the rule in

    Returns:
        tuple[Grammar, str]: The new grammar with the rule created and the name of the new rule
    """
    if not base_name in grammar:
        return extend_grammar(base_name, [], grammar), base_name
    ctr = 0
    name: str = f"{base_name}-{ctr}"
    while name in grammar:
        ctr += 1
        name = f"{base_name}-{ctr}"
    return extend_grammar(name, [], grammar), name


def extract_grammar(grammar: GrammarDict, rule: str) -> GrammarDict:
    """Extracts the grammar starting from the given rule. The extracted grammar contains only the rules that are reachable from the given rule.

    Args:
        grammar (Grammar): The grammar to extract from
        rule (str): The rule to start from

    Returns:
        Grammar: The extracted grammar (deepcopied)
    """
    extracted_grammar: GrammarDict = {}
    to_process = [rule]
    while to_process:
        current_rule = to_process.pop(0)
        if current_rule in extracted_grammar:
            continue
        extracted_grammar[current_rule] = deepcopy(grammar[current_rule])
        for exp in extracted_grammar[current_rule]:
            for sub_rule in get_expansions(exp):
                sub_rule = rm_macro(sub_rule)
                if sub_rule not in extracted_grammar:
                    to_process.append(sub_rule)
    extracted_grammar["<start>"] = [rule]
    return extracted_grammar


def decompose_in_expansions(s: str) -> list[str]:
    """Decomposes the given string into its expansions and other content. If the string is not expandable, it is returned as is.
    Order is preserved.
    Example:
        assert decompose_in_expansions("a<exp1>b<exp2>c") == ["a", "<exp1>", "b", "<exp2>", "c"]
    Args:
        s (str): The string to decompose

    Returns:
        list[str]: The decomposed string
    """
    return list(x for x in re.split(r"(<[^<>]*>[\*\+\?]?)", s) if x)


class Grammar:
    """Immutable grammar class. It is a wrapper around a dictionary of rules (GrammarDict).
    It is immutable, so it is safe to pass it around without worrying about it being modified.
    On top of that it provides an interface to chain methods."""

    def __init__(self, grammar: GrammarDict, start_symbol: str = "<start>") -> None:
        # if start_symbol:
        #    assert Grammar.is_correct(grammar, ignore_start=start_symbol)
        self._grammar = defaultdict(list, grammar)
        self._start_symbol = start_symbol

    def __contains__(self, key: str) -> bool:
        return key in self._grammar

    def __iter__(self):
        return iter(self._grammar)

    def __len__(self) -> int:
        return len(self._grammar)

    def __getitem__(self, key: str) -> list[Expansion]:
        """Retrieves a rule from self. Macros symbols are ignored ('*', '+', '?')

        Args:
            key (str): The rule to search for

        Returns:
            list[Espansion]: The expansions of the rule

        Raises:
            KeyError: If the rule is not in the grammar
        """
        if key in self:
            return self._grammar[key]
        if key[-1] in "*+?" and key[:-1] in self:
            return self._grammar[key[:-1]]

        raise KeyError(f"Rule not found: {key}")

    def get(self, key: str, default: T = None) -> list[Expansion] | T:
        """Retrieves a rule from self. Macros symbols are ignored ('*', '+', '?')

        Args:
            key (str): The rule to search for
            default (T, optional): The default value to return if the rule is not found. Defaults to None.

        Returns:
            list[Espansion] | T: The expansions of the rule or the default value

        """
        try:
            return self[key]
        except KeyError:
            return default

    def items(self):
        return self._grammar.items()

    def dict_copy(self) -> GrammarDict:
        """Returns a (deep) copy of the internal grammar."""
        return deepcopy(self._grammar)

    def copy(self) -> Grammar:
        """Returns a (deep) copy of self."""
        return Grammar(self.dict_copy())

    def set_start_symbol(self, start_symbol: str) -> Grammar:
        """Sets the start symbol of the grammar. It does not modify the grammar itself.

        Args:
            start_symbol (str): The start symbol to set

        Returns:
            Grammar: A new grammar with the start symbol set
        """
        return Grammar(self.dict_copy(), start_symbol)

    def extend(self, rule: str, expansions: list[Expansion]) -> Grammar:
        """Adds expansions to a rule. If the rule is not present, it is created.

        Args:
            rule (str): The rule to add expansions to
            expansions (list[Expansion]): The expansions to add

        Returns:
            Grammar: A new grammar with the expansions added
        """
        cpy = self.dict_copy()
        cpy[rule] += expansions
        return Grammar(cpy)

    def sub_grammar(self, rule: str) -> Grammar:
        """Extracts the grammar starting from the given rule. The extracted grammar contains only the rules that are reachable from the given rule.

        Args:
            rule (str): The rule to start from

        Returns:
            Grammar: The extracted grammar as a copy
        """
        extracted_grammar: GrammarDict = {}
        to_process = [rule]
        while to_process:
            current_rule = to_process.pop(0)
            if current_rule in extracted_grammar:
                continue
            extracted_grammar[current_rule] = deepcopy(self[current_rule])
            for exp in extracted_grammar[current_rule]:
                for sub_rule in get_expansions(exp):
                    sub_rule = rm_macro(sub_rule)
                    if sub_rule not in extracted_grammar:
                        to_process.append(sub_rule)
        extracted_grammar["<start>"] = [rule]
        return Grammar(extracted_grammar)

    def create_rule(self, base_name: str) -> tuple[Grammar, str]:
        """Creates a new rule in the grammar. If the base_name is already present, it is extended with a number suffix.

        Args:
            base_name (str): The base name of the rule to create
        Returns:
            tuple[Grammar, str]: The new grammar with the rule created and the name of the new rule
        """
        if not base_name in self:
            return self.extend(base_name, []), base_name
        ctr = 0
        name: str = f"{base_name}-{ctr}"
        while name in self:
            ctr += 1
            name = f"{base_name}-{ctr}"
        return self.extend(name, []), name

    def has_terminals_only(self, rule: str) -> bool:
        """Checks if the rule has terminals only. A terminal is an expansion that does not expand to another rule.

        Args:
            rule (str): The rule to check

        Returns:
            bool: True if the rule is composed of terminals only, False otherwise
        """
        return all(not is_expandable(get_expansion(exp)) for exp in self[rule])

    def make_all_expansion_parametrized(self) -> Grammar:
        """Makes all expansions parametrized. If an expansion is not parametrized, it is transformed into a parametrized one with an empty dictionary as parameters.
        Otherwise parametrized expansions are left as is.

        Returns:
            Grammar: The transformed grammar with all expansions parametrized
        """
        grammar = self.dict_copy()
        for rule, expansions in grammar.items():
            new_exps = []
            for exp in expansions:
                if isinstance(exp, str):
                    new_exps.append((exp, {}))
                else:
                    new_exps.append(exp)
            grammar[rule] = new_exps
        return Grammar(grammar)

    def add_parameters(self, rule: str, params: dict[str, Any]) -> Grammar:
        """Adds parameters to the given rule's exapansions in the grammar

        Args:
            rule (str): The rule to add the parameter to
            param (dict[str, Any]): The parameter(s) to add

        Returns:
            Grammar: The grammar with the parameters added
        """
        g = self.dict_copy()
        if rule in g:
            new_exps = []
            for exp in g[rule]:
                if isinstance(exp, str):
                    new_exps.append((exp, deepcopy(params)))
                else:
                    new_exps.append((exp[0], deepcopy({**exp[1], **params})))
            g[rule] = new_exps
        return Grammar(g)

    def merge_with(
        self, other: GrammarDict | Grammar, priority: str = "first"
    ) -> Grammar:
        """Merges other Grammar with self into a new Grammar. If a rule is present in both grammars, priority is used to choose which one to keep.
        Both grammars are left unchanged and a new one is created.

        Args:
            g2 (Grammar): The second grammar
            priority (str, optional): The priority to use to choose which rule to keep. Defaults to "first". Can be "first" or "second".

        Returns:
            Grammar: The merged grammar (under a new reference)
        """
        if isinstance(other, Grammar):
            other_grammar: ImmutableGrammar = other.grammar
            other_start = other.start_symbol
        else:
            other_grammar = ImmutableGrammar(other)
            other_start = "<start>"
        if priority == "first":
            g2_c = {k: v for k, v in other.items() if k not in self}
            return Grammar(self.dict_copy() | deepcopy(g2_c), self.start_symbol)
        else:
            g1_c = {k: v for k, v in self.items() if k not in other}
            return Grammar(deepcopy(other_grammar) | deepcopy(g1_c), other_start)

    def remove_rule(self, name: str) -> Grammar:
        """Removes the given rule from the grammar. References to the rule are not removed.

        Args:
            name (str): The name of the rule to remove

        Returns:
            Grammar: The grammar with the rule removed
        """
        grammar = self.dict_copy()
        if name in self:
            del grammar[name]
        return Grammar(grammar)

    @property
    def grammar(self) -> ImmutableGrammar:
        return ImmutableGrammar(self._grammar)

    @property
    def start_symbol(self) -> str:
        return self._start_symbol

    @staticmethod
    def is_correct(grammar: GrammarDict | ImmutableGrammar) -> bool:
        """Check if the grammar is correctly defined. It checks that all expansions are correctly defined.


        Args:
            grammar (Grammar): The grammar to check

        Returns:
            bool: True if the grammar is correctly defined, False otherwise

        """
        for key in grammar:
            if not isinstance(key, str):
                return False
            if not (key.startswith("<") and key.endswith(">")):
                return False
            for expansion in grammar[key]:
                if isinstance(expansion, tuple):
                    if not isinstance(expansion[0], str) or not isinstance(
                        expansion[1], dict
                    ):
                        logger.debug(
                            f"Expansion {expansion} is not correctly defined - type: {type(expansion)}"
                        )
                        return False
                else:
                    if not isinstance(expansion, str):
                        return False
                    exps = get_expansions(expansion)
                    if exps and not all(rm_macro(exp) in grammar for exp in exps):
                        logger.debug(f"Expansion {expansion} not found in grammar")
                        return False
        return True
