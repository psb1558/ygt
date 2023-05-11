from typing import Any
from schema import Or, Optional, Schema, SchemaError, Use, And # type: ignore

# from .ygModel import unicode_categories
import re

_error_message = ""

DELTA_DIST = [-8, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8]
DELTA_SHIFT = [2, 4, 8, 16, 32, 64]


def set_error_message(t: str) -> None:
    global _error_message
    if not _error_message:
        _error_message = t


def error_message(reset: bool = True) -> str:
    global _error_message
    r = _error_message
    if reset:
        _error_message = ""
    return r


def have_error_message() -> bool:
    return bool(_error_message)


def is_cv_distance_valid(s: Any) -> bool:
    try:
        sss = float(s)
    except Exception:
        sss = s
    if type(sss) is float or type(sss) is int:
        f = float(sss)
        return f >= -4.0 and f <= 4.0
    if type(sss) is str:
        ss = sss.split("/", 1) # type: ignore
        try:
            left = int(ss[0])
            right = int(ss[1])
        except Exception:
            return False
        return left in DELTA_DIST and right in DELTA_SHIFT
    return False


def is_point_valid_1(pt: int | str | list | dict) -> bool:
    if type(pt) is int:
        return True
    if type(pt) is str:
        if re.match("^[a-zA-Z][0-9A-Za-z-_]*", pt):
            return True
        if re.search("\{[\d\-][\d]{0,3};[\d\-][\d]{0,3}\}", pt):
            return True
    if type(pt) is list:
        err = False
        for p in pt:
            if not is_point_valid_1(p):
                err = True
        if not err:
            return True
    if type(pt) is dict:
        err = False
        for v in pt.values():
            if not is_point_valid_1(v):
                err = True
        if not err:
            return True
    set_error_message("point " + str(pt) + " is not valid")
    return False


def is_point_valid_2(pt: int | str | list) -> bool:
    if type(pt) is int:
        return True
    if type(pt) is str:
        if re.match("^[a-zA-Z][0-9A-Za-z-_]*", pt):
            return True
        if re.search("\{[\d\-][\d]{0,3};[\d\-][\d]{0,3}\}", pt):
            return True
    if type(pt) is list:
        err = False
        for p in pt:
            if not is_point_valid_1(p):
                err = True
        if not err:
            return True
    set_error_message("point " + str(pt) + " is not valid")
    return False


def validate_points(pt: list) -> bool:
    try:
        for p in pt:
            nested_point_schema.validate(p)
        return True
    except Exception as e:
        set_error_message("point " + str(pt) + " is not valid.")
    return False


def is_round_valid(r: bool | str) -> bool:
    if type(r) is bool:
        return True
    return r in [
        "to-grid",
        "to-half-grid",
        "to-double-grid",
        "down-to-grid",
        "up-to-grid",
    ]


nested_point_struct = {
    "ptid": is_point_valid_2,
    Optional("ref"): is_point_valid_2,
    Optional("valid"): bool,
    Optional("dist"): str,
    Optional("pos"): str,
    Optional("round"): is_round_valid,
    Optional("min"): bool,
    "rel": Or(
        "stem", "blackdist", "whitedist", "graydist", "shift", "align", "interpolate"
    ),
    Optional("points"): validate_points,
}

point_struct = {
    "points": [
        {
            "ptid": is_point_valid_1,
            Optional("ref"): is_point_valid_2,
            Optional("valid"): bool,
            Optional("dist"): str,
            Optional("pos"): str,
            Optional("round"): is_round_valid,
            Optional("min"): bool,
            Optional("function"): Or(str, dict),
            Optional("macro"): Or(str, dict),
            Optional("rel"): Or(
                "stem",
                "blackdist",
                "whitedist",
                "graydist",
                "shift",
                "align",
                "interpolate",
            ),
            Optional("points"): validate_points,
        }
    ]
}

cv_ppem_struct = {"ppem": int, "cv": str}

cv_same_as_struct = {
    Optional("above"): cv_ppem_struct,
    Optional("below"): cv_ppem_struct,
}

cv_var_struct = {str: int}

cv_origin_struct = {"glyph": str, "ptnum": [int]}

cv_delta_struct = {
    "size": And(Use(int), lambda n: 9 <= n <= 56),
    "distance": is_cv_distance_valid,
}

cvt_entry_struct = {
    "val": int,
    "type": Or("pos", "dist"),
    "axis": Or("y", "x"),
    Optional("round"): bool,
    Optional("col"): Or("black", "white", "gray"),
    Optional("suffix"): str,
    Optional("cat"): Or(
        "Lu",
        "Ll",
        "Lt",
        "LC",
        "Lm",
        "Lo",
        "L",
        "Mn",
        "Mc",
        "Me",
        "M",
        "Nd",
        "Nl",
        "No",
        "N",
        "Pc",
        "Pd",
        "Ps",
        "Pe",
        "Pi",
        "Pf",
        "Po",
        "P",
        "Sm",
        "Sc",
        "Sk",
        "So",
        "S",
        "Zs",
        "Zl",
        "Zp",
        "Z",
        "Cc",
        "Cf",
        "Cs",
        "Co",
        "Cn",
        "C",
    ),
    Optional("same-as"): cv_same_as_struct,
    Optional("var"): cv_var_struct,
    Optional("origin"): cv_origin_struct,
    Optional("deltas"): [cv_delta_struct],
}

function_entry_struct = {
    Optional("stack-safe"): bool,
    Optional("primitive"): bool,
    Optional(str): {
        "type": Or("point", "pos", "dist", "int", "float"),
        Optional("subtype"): Or("target", "ref"),
        Optional("val"): Or(str, int, float),
    },
    "code": str,
}

macro_entry_struct = {
    str: {
        "type": Or("point", "pos", "dist", "int", "float"),
        Optional("subtype"): Or("target", "ref"),
        Optional("val"): Or(str, int, float),
    },
    "code": str,
}

hint_types = [
    "blackdist",
    "whitedist",
    "graydist",
    "anchor",
    "shift",
    "align",
    "interpolate",
]

defaults_struct = {
    Optional("use-truetype-defaults"): bool,
    Optional("init-graphics"): bool,
    Optional("assume-always-y"): bool,
    Optional("cleartype"): bool,
    Optional("counterclockwise"): bool,
    Optional("round"): hint_types,
    Optional("no-round"): hint_types,
    Optional("cv_vars_generated"): bool,
    Optional("merge-mode"): bool,
    Optional("replace-prep"): bool,
    Optional("function-base"): int,
}

properties_struct = {
    Optional("category"): Or(
        "Lu",
        "Ll",
        "Lt",
        "LC",
        "Lm",
        "Lo",
        "L",
        "Mn",
        "Mc",
        "Me",
        "M",
        "Nd",
        "Nl",
        "No",
        "N",
        "Pc",
        "Pd",
        "Ps",
        "Pe",
        "Pi",
        "Pf",
        "Po",
        "P",
        "Sm",
        "Sc",
        "Sk",
        "So",
        "S",
        "Zs",
        "Zl",
        "Zp",
        "Z",
        "Cc",
        "Cf",
        "Cs",
        "Co",
        "Cn",
        "C",
    ),
    Optional("xoffset"): int,
    Optional("yoffset"): int,
    Optional("assume-y"): bool,
    Optional("init-graphics"): bool,
    Optional("compact"): bool,
}

names_struct = {str: is_point_valid_2}


def tag_checker(s: str) -> bool:
    return bool(re.match("^[A-Za-z]{4}$", s))


def name_checker(s: str) -> bool:
    return bool(re.match("^[a-zA-Z][0-9A-Za-z-_]*$", s))


cvar_entry_struct = [
    {
        "regions": [{"tag": tag_checker, "val": float}],
        "vals": [{"nm": name_checker, "val": int}],
    }
]

point_schema = Schema(point_struct)
nested_point_schema = Schema(nested_point_struct)
defaults_schema = Schema(defaults_struct)


def is_valid(t: Any) -> bool:
    try:
        point_schema.validate(t)
        return True
    except SchemaError as s:
        set_error_message("Error in YAML source: " + str(s))
    return False


cv_delta_schema = Schema(cv_delta_struct)
cvt_schema = Schema(cvt_entry_struct)
cvar_schema = Schema(cvar_entry_struct)
prep_schema = Schema({"code": str})
function_schema = Schema(function_entry_struct)
macro_schema = Schema(macro_entry_struct)
props_schema = Schema(properties_struct)
names_schema = Schema(names_struct)


def is_cv_delta_valid(c: dict) -> bool:
    try:
        cv_delta_schema.validate(c)
        return True
    except SchemaError as s:
        set_error_message("Illegal value in Control Value Delta: " + str(s))
    return False


def is_cvt_valid(t: dict) -> bool:
    try:
        k = t.keys()
        for kk in k:
            cvt_schema.validate(t[kk])
        return True
    except SchemaError as s:
        set_error_message("Error in Control Value Table: " + str(s))
    return False


def is_cvar_valid(t: dict) -> bool:
    try:
        cvar_schema.validate(t)
        return True
    except SchemaError as s:
        set_error_message("Error in cvar: " + str(s))
    return False


def is_prep_valid(t: dict) -> bool:
    try:
        prep_schema.validate(t)
        return True
    except SchemaError as s:
        set_error_message("Error in prep: " + str(s))
    return False


def are_functions_valid(t: dict) -> bool:
    try:
        for k in t.keys():
            function_schema.validate(t[k])
        return True
    except SchemaError as s:
        set_error_message("Error in functions: " + str(s))
    return False


def are_macros_valid(t: dict) -> bool:
    try:
        for k in t.keys():
            macro_schema.validate(t[k])
        return True
    except SchemaError as s:
        set_error_message("Error in macros: " + str(s))
    return False


def are_defaults_valid(t: dict) -> bool:
    try:
        defaults_schema.validate(t)
        return True
    except SchemaError as s:
        set_error_message("Error in defaults: " + str(s))
    return False


def are_names_valid(t: dict) -> bool:
    try:
        names_schema.validate(t)
        return True
    except SchemaError as s:
        set_error_message("Error in point names: " + str(s))
    return False


def are_properties_valid(t: dict) -> bool:
    try:
        props_schema.validate(t)
        return True
    except SchemaError as s:
        set_error_message("Error in glyph properties: " + str(s))
    return False


def always_valid(t) -> bool:
    return True
