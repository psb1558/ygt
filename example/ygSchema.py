from schema import Or, Optional, Schema, SchemaError
import re
import yaml

def is_point_valid_1(pt):
    success = False
    print(type(pt))
    if type(pt) is int:
        return True
    if type(pt) is str:
        if re.match("^[\w][\w\d-]*", pt):
            return True
        if re.search("\{[\d\-][\d]{0,3};[\d\-][\d]{0,3}\}", pt):
            return True
    if type(pt) is list:
        for p in pt:
            if not is_point_valid_1(p):
                return False
        return True
    if type(pt) is dict:
        for v in pt.values():
            if not is_point_valid_1(v):
                return False
        return True
    return False

def is_point_valid_2(pt):
    if type(pt) is int:
        return True
    if type(pt) is str:
        if re.match("^[\w][\w\d-]*", pt):
            return True
        if re.search("\{[\d\-][\d]{0,3};[\d\-][\d]{0,3}\}", pt):
            return True
    if type(pt) is list:
        for p in pt:
            if not is_point_valid_1(p):
                return False
        return True
    return False

def validate_points(pt):
    try:
        for p in pt:
            nested_point_schema.validate(p)
        return True
    except Exception as e:
        print(e)
    return False

nested_point_struct = {
    "points": [
        {
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
            Optional("points"): [validate_points]
        }
    ]
}

nested_point_struct_a = {
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
nested_point_schema = Schema(nested_point_struct_a)

sample_yaml_1 = """
points:
- ptid:
    base: 59
    pt-a: 0
    pt-b: 4
    base-sh: 38
  macro: cap-serif
- ptid:
  - 53
  - 44
  - 32
  ref: 4
  rel: shift
  points:
  - ptid: '{10;20}'
    rel: shift
    points:
    - ptid: 0
      rel: align
"""

sample_yaml_2 = """
points:
- ptid: 
  - 88
  - 53
  ref: 124 
  rel: shift
"""

sample_yaml_3 = """
{points: [{ptid:  [88, 53], ref: 124, rel: shift}]}
"""

tester = yaml.safe_load(sample_yaml_1)

point_schema.validate(tester)
