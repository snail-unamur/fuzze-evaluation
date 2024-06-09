from enum import Enum, auto
import re
from typing import Literal
from fuzze.fuzzers.bases import GrammarBasedFuzzerBase
from fuzze.fuzzers.cost_estimators import ProductionLengthEstimator
from fuzze.grammars.predefined import (
    DATE_GRAMMAR,
    INTEGER_NUMBER_GRAMMAR,
    EMAIL_GRAMMAR,
    PHONE_GRAMMAR,
    REAL_NUMBER_GRAMMAR,
    STRING_GRAMMAR,
    UNSIGNED_INTEGER_NUMBER_GRAMMAR,
)
from .fuzzers import CoverageGrammarFuzzer, GrammarCostBasedFuzzer
from fuzze.grammars.types import DerivationTree

EU_PHONE_PATTERN = re.compile(
    r"""^((\+\d{2})|0)?\s?((\d{3}\s?){3}|(\d{3}\s?(\d{2}\s?){3}))$"""
)

EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

EU_DATE_PATTERN = re.compile(r"^\d{2}\/\d{2}\/\d{4}$")

UNSIGNED_INTEGER_NUMBER_PATTERN = re.compile(r"^([1-9]\d+)|\d$")

INTEGER_NUMBER_PATTERN = re.compile(r"^([-+]?[1-9]\d+)|(0)$")

FLOAT_NUMBER_PATTERN = re.compile(r"^[-+]?\d*\.\d+$")


class InputType(Enum):
    INTEGER = auto()
    NATURAL = auto()
    REAL = auto()
    EMAIL = auto()
    STRING = auto()
    PHONE = auto()
    DATE = auto()


class TourInputsFuzzer:
    """Class that offers a fuzz method that produces a fuzz using the correct grammar based of the given input.
    The input can be of type: natural, integer, real, email, phone, date and string.
    """

    _input_type_fuzz_mapping: dict[InputType, GrammarBasedFuzzerBase] = {
        InputType.NATURAL: CoverageGrammarFuzzer(UNSIGNED_INTEGER_NUMBER_GRAMMAR),
        InputType.INTEGER: CoverageGrammarFuzzer(INTEGER_NUMBER_GRAMMAR),
        InputType.REAL: CoverageGrammarFuzzer(REAL_NUMBER_GRAMMAR),
        InputType.EMAIL: CoverageGrammarFuzzer(EMAIL_GRAMMAR),
        InputType.PHONE: CoverageGrammarFuzzer(PHONE_GRAMMAR),
        InputType.DATE: CoverageGrammarFuzzer(DATE_GRAMMAR),
        InputType.STRING: GrammarCostBasedFuzzer(
            STRING_GRAMMAR, ProductionLengthEstimator(STRING_GRAMMAR), 8, 12
        ),
    }

    def fuzz(self, input: str) -> str:
        """Produce a fuzz of the input based on the type of the input.
        Types of fuzz are: natural, integer, real, email, phone, date and string.

        Args:
            input (str): The input to base the type of fuzz of.

        Returns:
            str: A generated fuzz using the proper grammar.
        """

        type = self._find_input_type(input)
        return self._apply_fuzz(type, input).toString()

    def _find_input_type(self, text: str) -> InputType:
        # If a phone number is written in a way that could match a number we should prioritize the phone number
        if self._is_phone(text):
            return InputType.PHONE
        if self._is_natural_number(text):
            return InputType.NATURAL
        if self._is_integer_number(text):
            return InputType.INTEGER
        if self._is_real_number(text):
            return InputType.REAL
        if self._is_email(text):
            return InputType.EMAIL
        if self._is_date(text):
            return InputType.DATE
        return InputType.STRING

    def _is_date(self, text: str) -> Literal[False] | str:
        # date format: dd/mm/yyyy
        if (
            match := re.match(
                EU_DATE_PATTERN,
                text,
            )
        ) is not None and match.group() == text:
            return text
        return False

    def _is_real_number(self, text: str) -> Literal[False] | float:
        if (
            match := re.match(
                FLOAT_NUMBER_PATTERN,
                text,
            )
        ) is not None and match.group() == text:
            return float(text)
        return False

    def _is_natural_number(self, text: str) -> Literal[False] | int:
        if (
            match := re.match(
                UNSIGNED_INTEGER_NUMBER_PATTERN,
                text,
            )
        ) is not None and match.group() == text:
            return int(text)
        return False

    def _is_integer_number(self, text: str) -> Literal[False] | int:
        if (
            match := re.match(
                INTEGER_NUMBER_PATTERN,
                text,
            )
        ) is not None and match.group() == text:
            return int(text)
        return False

    def _is_email(self, text: str) -> Literal[False] | str:
        if (
            match := re.match(
                EMAIL_PATTERN,
                text,
            )
        ) is not None and match.group() == text:
            return text
        return False

    def _is_phone(self, text: str) -> Literal[False] | str:
        if (
            match := re.match(
                EU_PHONE_PATTERN,
                text,
            )
        ) is not None and match.group() == text:
            return text
        return False

    def _apply_fuzz(self, type: InputType, default: str) -> DerivationTree:
        fuzzer = self._input_type_fuzz_mapping.get(type)
        if fuzzer is not None:
            return fuzzer.fuzz()
        return DerivationTree(default)

    def reset(self, tp: InputType | None = None) -> None:
        if tp is not None:
            self._input_type_fuzz_mapping[tp].reset()
        else:
            for fuzzer in self._input_type_fuzz_mapping.values():
                fuzzer.reset()
