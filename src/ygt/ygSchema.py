from schema import Or, Optional, Schema, SchemaError
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
    print("Invalid in is_point_valid_1")
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
    print("Invalid in is_point_valid_2")
    set_error_message("point " + str(pt) + " is not valid")
    return False

def validate_points(pt):

    set_error_message(standard_okay)

    try:
        for p in pt:
            nested_point_schema.validate(p)
        return True
    except Exception as e:
        print("Invalid in validate_points:")
        print(e)
        set_error_message("point " + str(pt) + " is not valid.")
    return False

nested_point_struct = {
    "ptid":               is_point_valid_2,
    Optional("ref"):      is_point_valid_2,
    Optional("dist"):     str,
    Optional("pos"):      str,
    Optional("round"):    bool,
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
            Optional("round"):    bool,
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

point_schema = Schema(point_struct)
nested_point_schema = Schema(nested_point_struct)

def is_valid(t):

    try:
        point_schema.validate(t)
        set_error_message(standard_okay)
        # print("is_valid = True")
        return True
    except SchemaError as s:
        print("Invalid in is_valid:")
        print(s)
        set_error_message(standard_error)
    #print("is_valid = False")
    return False
