"""Numeric-expression presence checks, deliberately not semantic validation.

Supported grammar and limitations are documented in CHECKER.md.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re


ONES = dict(zip("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(), range(20)))
TENS = dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10)))
ORDINALS = dict(zip("first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth".split(), range(1, 13)))
CHINESE_DIGITS = dict(zip("零一二三四五六七八九", range(10))) | {"〇": 0, "两": 2}
MONTHS = {name.lower(): index for index, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
MONTHS.update({name[:3]: value for name, value in list(MONTHS.items())})
MONTH = "(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + ")"
UNIT_WORD = "(?:" + "|".join(list(ONES)[1:10]) + ")"
SMALL = "(?:" + "|".join(ONES) + ")"
TENS_WORD = "(?:" + "|".join(TENS) + ")"
BASE_WORD = rf"(?:{TENS_WORD}(?:[- ]{UNIT_WORD})?|{SMALL})"
CARDINAL = rf"(?:{UNIT_WORD}\s+hundred(?:\s+(?:and\s+)?{BASE_WORD})?|{BASE_WORD})"
DIGIT = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
CHINESE = r"[零〇一二两三四五六七八九十百]+"
VALUE = rf"(?:{DIGIT}|{CARDINAL}|{CHINESE})"
SCALE = r"(?:million|billion|thousand|k|万|千|亿)"
NUMBER = rf"{VALUE}(?:\s*(?:%|percent\b|{SCALE}))?"
ORDINAL = r"(?:\d+(?:st|nd|rd|th)|" + "|".join(ORDINALS) + ")"
DAY = r"\d{1,2}(?:st|nd|rd|th)?"
# Match month/year before month/day to avoid splitting March 2027.
DATE = (rf"(?:\d{{4}}[-/]\d{{1,2}}[-/]\d{{1,2}}|"
        rf"\d{{4}}\s*年\s*\d{{1,2}}\s*月(?:\s*\d{{1,2}}\s*[日号])?|"
        rf"{DAY}\s+{MONTH}(?:\s+\d{{4}})?|"
        rf"{MONTH}\s+\d{{4}}|{MONTH}\s+{DAY}(?:,?\s+\d{{4}})?)")
TIME = r"(?:\d{1,2}:\d{2}(?:\s*[ap]m)?|\d{1,2}\s*[ap]m)"
AREA = rf"{VALUE}\s*(?:m2|m²|square\s+met(?:res?|ers?)|平方米)"
TOKEN = re.compile(
    rf"(?<![A-Za-z0-9_.,])(?:(?P<date>{DATE})|(?P<time>{TIME})|"
    rf"(?P<area>{AREA})|(?P<ordinal>{ORDINAL})|"
    rf"(?P<cnpercent>百分之{VALUE})|(?P<number>{NUMBER}))(?![A-Za-z0-9_])", re.IGNORECASE)


def decimal_text(value):
    number = Decimal(str(value).replace(",", ""))
    return "0" if number == 0 else format(number.normalize(), "f")


def basic_value(value):
    value = value.lower().strip()
    if re.fullmatch(DIGIT, value):
        return decimal_text(value)
    if re.fullmatch(CHINESE, value):
        if all(character in CHINESE_DIGITS for character in value):
            return str(int("".join(str(CHINESE_DIGITS[character]) for character in value)))
        total, digit = 0, 0
        for character in value:
            if character in CHINESE_DIGITS:
                digit = CHINESE_DIGITS[character]
            else:
                total += (digit or 1) * {"十": 10, "百": 100}[character]
                digit = 0
        return str(total + digit)
    total = 0
    for word in value.replace("-", " ").split():
        if word == "and":
            continue
        if word == "hundred":
            total *= 100
        elif word in ONES:
            total += ONES[word]
        else:
            total += TENS[word]
    return str(total)


def date_key(raw):
    if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", raw):
        year, month, day = map(int, re.split(r"[-/]", raw))
    elif "年" in raw:
        parts = list(map(int, re.findall(r"\d+", raw)))
        year, month = parts[:2]
        if len(parts) == 2:
            date(year, month, 1)
            return ("month_date", f"{year:04}-{month:02}")
        day = parts[2]
    else:
        words = re.findall(r"[a-z]+|\d+", raw.lower())
        month_word = next(word for word in words if word in MONTHS)
        month = MONTHS[month_word]
        numbers = [int(word) for word in words if word.isdigit()]
        if len(numbers) == 1 and numbers[0] >= 1000:
            year = numbers[0]
            date(year, month, 1)
            return ("month_date", f"{year:04}-{month:02}")
        day = numbers[0]
        if len(numbers) == 1:
            date(2000, month, day)  # Leap year validates a partial date without inventing a year.
            return ("partial_date", f"{month:02}-{day:02}")
        year = numbers[1]
    return ("date", date(year, month, day).isoformat())


def normalize(kind, raw):
    value = raw.lower().strip()
    if kind == "date":
        return date_key(value)
    if kind == "time":
        parts = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)?", value)
        hour, minute = int(parts[1]), int(parts[2] or 0)
        suffix = parts[3]
        if minute > 59 or (suffix and not 1 <= hour <= 12) or (not suffix and hour > 23):
            raise ValueError("Invalid time")
        if suffix:
            hour = hour % 12 + (12 if suffix == "pm" else 0)
        return ("time", f"{hour:02}:{minute:02}")
    if kind == "area":
        return ("area_m2", basic_value(re.sub(r"\s*(?:m2|m²|square\s+met(?:res?|ers?)|平方米)$", "", value)))
    if kind == "ordinal":
        return ("ordinal", str(ORDINALS[value]) if value in ORDINALS else str(int(re.sub(r"\D", "", value))))
    if kind == "cnpercent":
        return ("percent", basic_value(value[3:]))
    suffix = re.search(rf"\s*(%|percent|{SCALE})$", value)
    if suffix:
        number, unit = basic_value(value[:suffix.start()]), suffix[1]
        if unit in {"%", "percent"}:
            return ("percent", number)
        scale = {"k": "thousand", "千": "thousand", "万": "ten_thousand", "亿": "hundred_million"}.get(unit, unit)
        return ("scaled", number, scale)
    return ("number", basic_value(value))


@dataclass(frozen=True)
class NumberToken:
    raw: str
    start: int
    end: int
    key: tuple | None

    def as_dict(self):
        return {"raw": self.raw, "start": self.start, "end": self.end,
                "key": list(self.key) if self.key is not None else None}


def extract_numbers(text):
    tokens = []
    covered = set()
    for match in TOKEN.finditer(text):
        try:
            key = normalize(match.lastgroup, match[0])
        except (ValueError, KeyError):
            key = None
        tokens.append(NumberToken(match[0], match.start(), match.end(), key))
        covered.update(range(match.start(), match.end()))
    # Fail closed for numeral-like syntax outside the supported grammar (e.g. 1e3).
    for match in re.finditer(r"\S+", text):
        if any(character.isdigit() and index not in covered
               for index, character in enumerate(text[match.start():match.end()], match.start())):
            tokens = [token for token in tokens if token.end <= match.start() or token.start >= match.end()]
            tokens.append(NumberToken(match[0], match.start(), match.end(), None))
    return sorted(tokens, key=lambda token: token.start)


def check_summary(source, summary):
    source_tokens = extract_numbers(source)
    summary_tokens = extract_numbers(summary)
    evidence_by_key = {}
    for token in source_tokens:
        if token.key is not None:
            evidence_by_key.setdefault(token.key, []).append(token.as_dict())
    checks = []
    unmatched = []
    for token in summary_tokens:
        evidence = evidence_by_key.get(token.key, []) if token.key is not None else []
        item = {**token.as_dict(), "supported": bool(evidence), "evidence": evidence}
        checks.append(item)
        if not evidence:
            unmatched.append(token.as_dict())
    return {"check_passed": not unmatched, "source_tokens": [token.as_dict() for token in source_tokens],
            "summary_tokens": checks, "unmatched": unmatched}
