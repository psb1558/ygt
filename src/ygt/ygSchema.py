from schema import Or, Optional, Schema, SchemaError
from .ygModel import unicode_categories
import re

standard_error = "YAML source is not valid"

standard_okay = "Valid"

_error_message = standard_okay

def set_error_message(t):
    global _error_message
    if t == "error":
        _error_message = standard_error
    elif t:
        _error_message = t
    else:
        _error_message = "Valid"

def error_message():
    if _error_message == standard_okay:
        return None
    return _error_message

def is_point_valid_1(pt):

    set_error_message(standard_okay)

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

def is_point_valid_2(pt):

    set_error_message(standard_okay)

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

def validate_points(pt):

    set_error_message(standard_okay)

    try:
        for p in pt:
            nested_point_schema.validate(p)
        return True
    except Exception as e:
        set_error_message("point " + str(pt) + " is not valid.")
    return False

def is_round_valid(r):
    if type(r) is bool:
        return True
    return r in ["to-grid", "to-half-grid", "to-double-grid", "down-to-grid", "up-to-grid"]

nested_point_struct = {
    "ptid":               is_point_valid_2,
    Optional("ref"):      is_point_valid_2,
    Optional("dist"):     str,
    Optional("pos"):      str,
    Optional("round"):    is_round_valid,
    "rel": Or("stem",
              "blackspace",
              "whitespace",
              "grayspace",
              "shift",
              "align",
              "interpolate"),
    Optional("points"): validate_points
    }

point_struct = {
    "points": [
        {
            "ptid":               is_point_valid_1,
            Optional("ref"):      is_point_valid_2,
            Optional("dist"):     str,
            Optional("pos"):      str,
            Optional("round"):    is_round_valid,
            Optional("function"): Or(str, dict),
            Optional("macro"):    Or(str, dict),
            Optional("rel"):      Or("stem",
                                     "blackspace",
                                     "whitespace",
                                     "grayspace",
                                     "shift",
                                     "align",
                                     "interpolate"),
            Optional("points"):   validate_points
        }
    ]
}

cv_ppem_struct = {
    "ppem": int,
    "cv": str
}

cv_same_as_struct = {
    Optional("above"): cv_ppem_struct,
    Optional("below"): cv_ppem_struct
}

cvt_entry_struct = {
    "val": int,
    "type": Or("pos", "dist"),
    "axis": Or("y", "x"),
    Optional("col"): Or("black", "white", "gray"),
    Optional("suffix"): str,
    Optional("cat"): Or("Lu", "Ll", "Lt", "LC", "Lm", "Lo", "L", "Mn", "Mc",
                        "Me", "M", "Nd", "Nl", "No", "N", "Pc", "Pd", "Ps",
                        "Pe", "Pi", "Pf", "Po", "P", "Sm", "Sc", "Sk", "So",
                        "S", "Zs", "Zl", "Zp", "Z", "Cc", "Cf", "Cs", "Co",
                        "Cn", "C"),
    Optional("same-as"): cv_same_as_struct
}

function_entry_struct = {
    Optional("stack-safe"): bool,
    Optional("primitive"):  bool,
    Optional(str): {
        "type":              Or("point", "pos", "dist", "int", "float"),
        Optional("subtype"): Or("target", "ref"),
        Optional("val"):     Or(str, int, float)
    },
    "code": str
}

macro_entry_struct = {
    str: {
        "type":              Or("point", "pos", "dist", "int", "float"),
        Optional("subtype"): Or("target", "ref"),
        Optional("val"):     Or(str, int, float)
    },
    "code": str
}

hint_types = ["blackspace", "whitespace", "grayspace", "anchor", "shift", "align", "interpolate"]

defaults_struct = {
    Optional("use-truetype-defaults"): bool,
    Optional("init-graphics"): bool,
    Optional("assume-always-y"): bool,
    Optional("cleartype"): bool,
    Optional("round"): hint_types,
    Optional("no-round"): hint_types
}

properties_struct = {
    Optional("category"): Or("Lu", "Ll", "Lt", "LC", "Lm", "Lo", "L", "Mn", "Mc",
                             "Me", "M", "Nd", "Nl", "No", "N", "Pc", "Pd", "Ps",
                             "Pe", "Pi", "Pf", "Po", "P", "Sm", "Sc", "Sk", "So",
                             "S", "Zs", "Zl", "Zp", "Z", "Cc", "Cf", "Cs", "Co",
                             "Cn", "C"),
    Optional("xoffset"): int,
    Optional("yoffset"): int,
    Optional("assume-y"): bool,
    Optional("init-graphics"): bool,
    Optional("compact"): bool
}

names_struct = {
    str: is_point_valid_2
}

def tag_checker(s):
    return bool(re.match("^[A-Za-z]{4}$", s))

def name_checker(s):
    return bool(re.match("^[a-zA-Z][0-9A-Za-z-_]*$", s))

cvar_entry_struct = [
    {
        "regions": [
            {
                "tag":  tag_checker,
                "bot":  float,
                "peak": float,
                "top":  float
            }
        ],
        "vals": [
            {
                "nm":  name_checker,
                "val": int
            }
        ]
    }
]

point_schema = Schema(point_struct)
nested_point_schema = Schema(nested_point_struct)
defaults_schema = Schema(defaults_struct)

def is_valid(t):
    try:
        point_schema.validate(t)
        set_error_message(standard_okay)
        return True
    except SchemaError as s:
        set_error_message(standard_error)
    return False

cvt_schema =      Schema(cvt_entry_struct)
cvar_schema =     Schema(cvar_entry_struct)
prep_schema =     Schema({ "code": str })
function_schema = Schema(function_entry_struct)
macro_schema =    Schema(macro_entry_struct)
props_schema =    Schema(properties_struct)
names_schema =    Schema(names_struct)

def is_cvt_valid(t):
    try:
        k = t.keys()
        for kk in k:
            cvt_schema.validate(t[kk])
        set_error_message(standard_okay)
        return True
    except SchemaError as s:
        # print("Schema Error")
        # print(s)
        set_error_message(standard_error)
    return False

def is_cvar_valid(t):
    try:
        cvar_schema.validate(t)
        return True
    except SchemaError as s:
        print("Error in is_cvar_valid:")
        print(s)
    return False

def is_prep_valid(t):
    try:
        prep_schema.validate(t)
        return True
    except SchemaError as s:
        print("Error in is_prep_valid:")
        print(s)
    return False

def are_functions_valid(t):
    try:
        for k in t.keys():
            function_schema.validate(t[k])
        return True
    except SchemaError as s:
        print("Error in are_functions_valid:")
        print(s)
    return False

def are_macros_valid(t):
    try:
        for k in t.keys():
            macro_schema.validate(t[k])
        return True
    except SchemaError as s:
        print("Error in are_macros_valid:")
        print(s)
    return False

def are_defaults_valid(t):
    try:
        defaults_schema.validate(t)
        return True
    except SchemaError as s:
        print("Error in are_defaults_valid:")
        print(s)
    return False

def are_names_valid(t):
    try:
        names_schema.validate(t)
        return True
    except SchemaError as s:
        print("Error in are_names_valid:")
        print(s)

def are_properties_valid(t):
    try:
        props_schema.validate(t)
        return True
    except SchemaError as s:
        print("Error in are_properties_valid:")
        print(s)

def always_valid(t):
    return True