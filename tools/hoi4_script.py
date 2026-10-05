"""Small, lossless Clausewitz block reader for controlled edits and audits."""
from dataclasses import dataclass
import re

# Match comparison operators before '='; the older tokeniser split '>='.
TOKENS = re.compile(r'#[^\n]*|"(?:\\.|[^"\\])*"|>=|<=|!=|[{}=<>]|[^\s{}=<>!"#]+')


@dataclass
class Entry:
    key: str | None
    value: str | list
    start: int
    end: int
    operator: str | None = None


def parse(text):
    tokens = [m for m in TOKENS.finditer(text) if not m[0].startswith('#')]
    pos = 0

    def block(nested=False):
        nonlocal pos
        rows = []
        while pos < len(tokens):
            token = tokens[pos]
            if token[0] == '}':
                assert nested, 'Unexpected closing brace'
                pos += 1
                return rows, token.end()
            assert token[0] != '{', 'Unassigned opening brace'
            pos += 1
            if pos < len(tokens) and tokens[pos][0] in {'=', '<', '>', '<=', '>=', '!='}:
                operator = tokens[pos][0]
                pos += 1
                assert pos < len(tokens), 'Missing value'
                value_token = tokens[pos]
                pos += 1
                if value_token[0] == '{':
                    value, end = block(True)
                else:
                    assert value_token[0] != '}', 'Missing scalar value'
                    value, end = value_token[0], value_token.end()
                rows.append(Entry(token[0], value, token.start(), end, operator))
            else:
                rows.append(Entry(None, token[0], token.start(), token.end()))
        assert not nested, 'Unclosed block'
        return rows, len(text)

    return block()[0]


def entries(rows, key):
    return [row for row in rows if row.key == key]


def one(rows, key):
    found = entries(rows, key)
    assert len(found) == 1, (key, len(found))
    return found[0]


def scalar(rows, key, default=None):
    found = entries(rows, key)
    return found[0].value if found else default


def walk(rows):
    for row in rows:
        yield row
        if isinstance(row.value, list):
            yield from walk(row.value)


def replace(text, changes):
    for start, end, value in sorted(changes, reverse=True):
        text = text[:start] + value + text[end:]
    parse(text)
    return text
