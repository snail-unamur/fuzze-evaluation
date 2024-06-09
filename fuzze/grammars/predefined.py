from copy import deepcopy
import string
from fuzze.grammars import Grammar, char_range, digits, num_range
import re

"""These grammars are predefined and are meant to be merged with other grammars to create a new grammar. 
They are not meant to be used as standalone grammars since they don't have a <start> expansion."""

CHRS = [
    re.escape(s) for s in string.printable if s not in string.whitespace + "\"'\\()<>"
]

ASCII = [s for s in string.ascii_letters + string.digits]

STRING_GRAMMAR = Grammar(
    {
        "<string>": ["<string><char>", "<char>"],
        "<char>": CHRS + ["<lcaret>", "<rcaret>"],  # type: ignore
        "<lcaret>": ["<"],
        "<rcaret>": [">"],
    },
    "<string>",
)
ASCII_STRING_GRAMMAR = Grammar(
    {
        "<string>": ["<string><char>", "<char>"],
        "<char>": ASCII,  # type: ignore
    },
    "<string>",
)

EMAIL_GRAMMAR = Grammar(
    {
        "<email>": ["<local-part>@<domain>"],
        "<local-part>": ["<string>"],
        "<domain>": ["<string>.<tld>"],
        "<tld>": ["com", "net", "org", "io"],
    },
    "<email>",
).merge_with(ASCII_STRING_GRAMMAR)


UNSIGNED_INTEGER_NUMBER_GRAMMAR = Grammar(
    {
        "<unsigned>": ["<not_zero><digit>*", "0"],
        "<digit>": digits(),
        "<not_zero>": num_range(1, 9),
    },
    "<unsigned>",
)

INTEGER_NUMBER_GRAMMAR = Grammar(
    {
        "<int>": ["<sign>?<unsigned>"],
        "<sign>": ["-"],
    },
    "<int>",
).merge_with(UNSIGNED_INTEGER_NUMBER_GRAMMAR)

REAL_NUMBER_GRAMMAR = Grammar(
    {
        "<real>": ["<int>", "<float>"],
        "<float>": ["<int>.<digit>+"],
    },
    "<real>",
).merge_with(INTEGER_NUMBER_GRAMMAR)

PHONE_GRAMMAR = Grammar(
    {
        "<phone>": ["<country_code><space>?<phone_number>"],
        "<country_code>": ["+<digit><digit>", "0"],
        "<phone_number>": ["<group> <group> <group>"],
        "<group>": ["<digit><digit><digit>"],
        "<space>": [" "],
        "<digit>": digits(),
    },
    "<phone>",
)


DATE_GRAMMAR = Grammar(
    {
        "<date>": ["<day>/<month>/<year>"],
        "<day>": num_range(1, 31),
        "<month>": num_range(1, 12),
        "<year>": ["<digit><digit><digit><digit>"],
        "<digit>": digits(),
    },
    "<date>",
)
