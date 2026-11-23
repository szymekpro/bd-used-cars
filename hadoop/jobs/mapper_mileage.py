import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import field, mileage_bin, number, text_stdout, valid_rows

out = text_stdout()
for row, price in valid_rows():
    label = mileage_bin(number(field(row, "mileage")))
    if label is None:
        continue
    accidents = (field(row, "has_accidents") or "unknown").lower()
    out.write("%s|%s\t%s\n" % (label, accidents, price))
out.flush()
