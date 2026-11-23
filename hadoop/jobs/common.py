import csv
import io
import re
import sys

csv.field_size_limit(10 ** 7)

HEADER = ["vin", "back_legroom", "bed", "bed_height", "bed_length", "body_type", "cabin", "city", "city_fuel_economy", "combine_fuel_economy", "daysonmarket", "dealer_zip", "description", "engine_cylinders", "engine_displacement", "engine_type", "exterior_color", "fleet", "frame_damaged", "franchise_dealer", "franchise_make", "front_legroom", "fuel_tank_volume", "fuel_type", "has_accidents", "height", "highway_fuel_economy", "horsepower", "interior_color", "isCab", "is_certified", "is_cpo", "is_new", "is_oemcpo", "latitude", "length", "listed_date", "listing_color", "listing_id", "longitude", "main_picture_url", "major_options", "make_name", "maximum_seating", "mileage", "model_name", "owner_count", "power", "price", "salvage", "savings_amount", "seller_rating", "sp_id", "sp_name", "theft_title", "torque", "transmission", "transmission_display", "trimId", "trim_name", "vehicle_damage_category", "wheel_system", "wheel_system_display", "wheelbase", "width", "year"]
COL = {name: i for i, name in enumerate(HEADER)}
NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?")
MIN_PRICE = 1
MAX_PRICE = 1000000
MIN_YEAR = 1980
MAX_YEAR = 2021
MAX_MILEAGE = 500000
MISSING = ("", "--", "nan", "None", "null")
MILEAGE_BINS = [
    (20000, "0-20k"),
    (40000, "20-40k"),
    (60000, "40-60k"),
    (80000, "60-80k"),
    (100000, "80-100k"),
    (150000, "100-150k"),
    (500000, "150-500k"),
]


def counter(name, value):
    sys.stderr.write("reporter:counter:Parser,%s,%d\n" % (name, value))
    sys.stderr.flush()


def text_stdin():
    return io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace", newline="\n")


def text_stdout():
    return io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", newline="\n")


def raw_records(stream):
    buf = []
    quotes = 0
    for line in stream:
        if not buf and line.startswith("vin,"):
            continue
        buf.append(line)
        quotes += line.count('"')
        if quotes % 2 == 0:
            yield "".join(buf)
            buf = []
            quotes = 0
    if buf:
        yield "".join(buf)


def field(row, name):
    value = row[COL[name]].strip()
    return None if value in MISSING else value


def number(value):
    if value is None:
        return None
    match = NUMBER.search(value)
    return float(match.group(0)) if match else None


def valid_rows(stream=None):
    stream = stream or text_stdin()
    stats = {"records": 0, "malformed": 0, "no_id": 0, "bad_price": 0, "valid": 0}
    for text in raw_records(stream):
        stats["records"] += 1
        try:
            row = next(csv.reader(io.StringIO(text)))
        except (csv.Error, StopIteration):
            stats["malformed"] += 1
            continue
        if len(row) != len(HEADER):
            stats["malformed"] += 1
            continue
        if number(field(row, "listing_id")) is None:
            stats["no_id"] += 1
            continue
        price = number(field(row, "price"))
        if price is None or price < MIN_PRICE or price > MAX_PRICE:
            stats["bad_price"] += 1
            continue
        stats["valid"] += 1
        yield row, price
    for name, value in stats.items():
        counter(name, value)


def mileage_bin(mileage):
    if mileage is None or mileage < 0 or mileage > MAX_MILEAGE:
        return None
    for upper, label in MILEAGE_BINS:
        if mileage <= upper:
            return label
    return None


def grouped(stream=None):
    stream = stream or io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace", newline="\n")
    current = None
    values = []
    for line in stream:
        key, _, value = line.rstrip("\n").partition("\t")
        if key != current and current is not None:
            yield current, values
            values = []
        current = key
        values.append(value)
    if current is not None:
        yield current, values
