"""ColSON parser."""

import re
from typing import Any

PATTERNS: dict = {
    "comment": r"^\s*(::)\s*([^:\s].*|(?<=\s)\S.*)\s*$",
    "dict": r"^\s*(:::)\s*$",
    "list": r"^\s*(::)\s*$",
    "escape": r"^\s*(\\)(.*)(\\)\s*$",
    "key_dict": r"^\s*(.*\S(?=\s)|.*[^:\s])\s*(:::)\s*$",
    "key_list": r"^\s*(.*\S(?=\s)|.*[^:\s])\s*(::)\s*$",
    "key_escape": r"^\s*(.*\S(?=\s)|.*[^:\s])\s*(::)\s*(\\)(.*)(\\)\s*$",
    "key_lang": r"^\s*(.*\S(?=\s)|.*[^:\s])\s*(::)\s*(True|False|None)\s*$",
    "key_float": r"^\s*(.*\S(?=\s)|.*[^:\s])\s*(::)\s*([+-]?(?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?)\s*$",
    "key_str": r"^\s*(.*\S(?=\s)|.*[^:\s])\s*(::)\s*((?:[^:\s].*\S|[^:\s])|(?<=\s)(?:\S.*\S|\S))\s*$",
    "lang": r"^\s*(True|False|None)\s*$",
    "float": r"^\s*([+-]?(?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?)\s*$",
    "str": r"^\s*(\S.*\S|\S)\s*$",
}


def loads(data: str, level: int = 0, tab: int = 4) -> Any:
    """
    Parse ColSON into Python.

    :param data: ColSON-like data
    :type data: str
    :param level: initial indentation level, defaults to 0
    :type level: int, optional
    :param tab: tab size in spaces, defaults to 4
    :type tab: int, optional
    :return: Python object
    :rtype: Any
    """
    data_split: list = data.split("\n")
    return _parse_from_colson(
        data=data_split,
        scope=[],
        level=level,
        tab=tab,
    )


def dumps(data: Any, level: int = 0, tab: int = 4) -> str:
    """
    Parse Python into ColSON

    :param data: Python object
    :type data: Any
    :param level: initial indentation level, defaults to 0
    :type level: int, optional
    :param tab: tab size in spaces, defaults to 4
    :type tab: int, optional
    :return: ColSON-like data
    :rtype: str
    """
    return _parse_to_colson(
        data=data,
        scope=[],
        level=level,
        tab=tab,
    )


def _parse_from_colson(data: list, scope: list, level: int = 0, tab: int = 4):
    """Parse ColSON into Python from the list of lines."""

    # finish at the end of the file
    if len(data) == 0:
        if len(scope) == 0:
            raise ValueError("There is nothing to parse.")
        return scope[0]

    line: str = data[0]
    rest: list = data[1:]

    key: Any = None
    value: Any = None

    # skip empty strings
    if re.search(r"^\s*$", line) or re.search(PATTERNS["comment"], line):
        return _parse_from_colson(rest, scope, level, tab)

    # honor indentation
    indented: re.Match | None = re.search(r"^\s*", line)
    if indented is not None:
        level_new: int = indented.end() // tab
    else:
        raise ValueError("Error during indentation check for {line}.")
    indent: int = level_new - level
    scope = scope[:-1] if indent <= 0 else scope
    scope = scope[:indent] if indent < 0 else scope

    # Dict
    if re.search(PATTERNS["dict"], line):
        value = {}
        if len(scope) > 0:
            scope[-1].append(value)
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # List
    if re.search(PATTERNS["list"], line):
        value = []
        if len(scope) > 0:
            scope[-1].append(value)
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # Escaped String
    if match := re.search(PATTERNS["escape"], line):
        value = match.group(2)
        if len(scope) > 0:
            scope[-1].append(value)
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # Key : Dict
    if match := re.search(PATTERNS["key_dict"], line):
        key = match.group(1)
        value = {}
        if len(scope) == 0:
            raise ValueError(f'"{key} :::" must have a parent dictionary.')
        scope[-1][key] = value
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # Key : List
    if match := re.search(PATTERNS["key_list"], line):
        key = match.group(1)
        value = []
        if len(scope) == 0:
            raise ValueError(f'"{key} ::" must have a parent dictionary.')
        scope[-1][key] = value
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # Key : Escaped String
    if match := re.search(PATTERNS["key_escape"], line):
        key = match.group(1)
        value = match.group(4)
        if len(scope) == 0:
            raise ValueError(
                f'"{key} :: \\{value[:6] + "..." if len(value) > 6 else value}\\" must have a parent dictionary.'
            )
        scope[-1][key] = value
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # Key : True|False|None
    if match := re.search(PATTERNS["key_lang"], line):
        key = match.group(1)
        value = match.group(3)

        if len(scope) == 0:
            raise ValueError(f'"{key} :: {value}" must have a parent dictionary.')

        value = _parse_lang(value)

        scope[-1][key] = value
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # Key : Number
    if match := re.search(PATTERNS["key_float"], line):
        key = match.group(1)
        value = match.group(3)

        if len(scope) == 0:
            raise ValueError(f'"{key} :: {value}" must have a parent dictionary.')

        value = _parse_numeric(value)

        scope[-1][key] = value
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # Key : String
    if match := re.search(PATTERNS["key_str"], line):
        key = match.group(1)
        value = match.group(3)
        if len(scope) == 0:
            raise ValueError(
                f'"{key} :: {value[:6] + "..." if len(value) > 6 else value}" must have a parent dictionary.'
            )
        scope[-1][key] = value
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # True|False|None
    if match := re.search(PATTERNS["lang"], line):
        value = match.group(1)

        value = _parse_lang(value)

        if len(scope) > 0:
            scope[-1].append(value)
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # Number
    if match := re.search(PATTERNS["float"], line):
        value = match.group(1)

        value = _parse_numeric(value)

        if len(scope) > 0:
            scope[-1].append(value)
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    # String
    if match := re.search(PATTERNS["str"], line):
        value = match.group(1)
        if len(scope) > 0:
            scope[-1].append(value)
        scope.append(value)
        return _parse_from_colson(rest, scope, level_new, tab)

    return ValueError("The data contains invalid ColSON.")


def _parse_to_colson(
    data: Any, scope: list, prop: Any = None, level: int = 0, tab: int = 4
) -> str:
    """Parse from Python to ColSON."""

    indent: str = " " * tab * level

    if isinstance(data, dict):
        prop = prop + " " if prop else ""
        scope.append(indent + prop + ":::")
        for key, value in data.items():
            _parse_to_colson(value, scope, key, level + 1, tab)

    elif isinstance(data, list):
        prop = prop + " " if prop else ""
        scope.append(indent + prop + "::")
        for item in data:
            _parse_to_colson(item, scope, None, level + 1, tab)

    elif isinstance(data, (int, float, type(None))):
        prop = prop + " :: " if prop else ""
        scope.append(indent + prop + str(data))

    elif (
        (data == "")
        or ("::" in data)
        or (data[0] == " " or data[-1] == " ")
        or (data[0] == "\\" and data[-1] == "\\")
    ):
        prop = prop + " :: " if prop else ""
        scope.append(indent + prop + "\\" + data + "\\")

    else:
        prop = prop + " :: " if prop else ""
        scope.append(indent + prop + data)

    return "\n".join(scope)


def _parse_lang(value) -> bool | None:
    """Parse True | False | None"""
    value = value.strip()

    match value:
        case "True":
            value = True
        case "False":
            value = False
        case "None":
            value = None
        case _:
            raise ValueError(f"{value} cannot be processed as True, False or None.")

    return value


def _parse_numeric(value) -> float | int:
    """Parse numeric values"""
    value = value.strip()

    if "." in value or "e" in value.lower():
        return float(value)

    value = float(value)
    if value % 1 == 0:
        return int(value)

    return value
