import os
import statistics
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import grouped, text_stdout

out = text_stdout()
for key, values in grouped():
    prices = [float(v) for v in values]
    out.write("%s\t%d\t%.2f\t%.2f\n" % (key, len(prices), statistics.median(prices), sum(prices) / len(prices)))
out.flush()
