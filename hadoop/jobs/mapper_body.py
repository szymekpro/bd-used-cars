import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import field, text_stdout, valid_rows

out = text_stdout()
for row, price in valid_rows():
    body = field(row, "body_type")
    if body:
        out.write("%s\t%s\n" % (body, price))
out.flush()
