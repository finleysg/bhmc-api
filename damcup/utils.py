import math
from decimal import Decimal


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(Decimal(n)*multiplier + Decimal(0.5)) / multiplier


def is_points(sheet):
    if "points" in sheet.name.lower() and "holes" not in sheet.name.lower():
        return True
    return False


def get_point_rows(sheet):
    for row_index in range(sheet.nrows):
        value = sheet.cell(row_index, 0).value
        if value != "" and row_index > 0:
            yield row_index