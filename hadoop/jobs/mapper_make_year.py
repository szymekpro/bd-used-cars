import os
import re
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import MAX_YEAR, MIN_YEAR, field, number, text_stdout, valid_rows

out = text_stdout()
for row, price in valid_rows():
    make = field(row, "make_name")
    year = number(field(row, "year"))
    if make and year is not None and MIN_YEAR <= year <= MAX_YEAR:
        make = re.sub(r"\s+", " ", make)
        out.write("%s|%d\t%s\n" % (make, year, price))
out.flush()
