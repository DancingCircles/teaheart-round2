"""Auditable one-to-one procurement reconciliation; no fuzzy joins or imputation."""
import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import re


FINANCE_FIELDS = ["订单编号 order_no", "采购项目 item", "门店 store", "金额 amount_cny", "下单日期 order_date"]
FEISHU_FIELDS = ["采购项目 item", "门店 store", "城市 city", "状态 status"]
STORE_ALIASES = {"Teaheart Zhongshan Road Store": "Zhongshan Rd 中山路店"}
STORE_FIELDS = ["store", "city", "known_total_cny", "missing_amount_count",
                "finance_only_count", "feishu_only_count", "is_complete"]
CITY_FIELDS = STORE_FIELDS[1:]


class DataError(ValueError):
    """Unsafe or malformed input: do not publish new results."""


def read_table(path: Path, fields: list[str]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if (reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames))
                or set(reader.fieldnames) != set(fields)):
            raise DataError(f"Unexpected headers in {path.name}; expected {fields}")
        rows = list(reader)
    if not rows:
        raise DataError(f"No records in {path.name}")
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise DataError(f"Malformed CSV row: {path.name}:{line}")
    return rows


def parse_date(value: str) -> str:
    for pattern in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass
    raise DataError(f"Invalid date: {value!r}")


def parse_amount(value: str) -> Decimal | None:
    if not value:
        return None
    if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?", value):
        raise DataError(f"Invalid amount: {value!r}")
    return Decimal(value.replace(",", ""))


@dataclass
class Reconciliation:
    stores: list[dict]
    cities: list[dict]
    issues_md: str
    stats: dict


def reconcile(data_dir: Path) -> Reconciliation:
    finance = read_table(data_dir / "finance_export.csv", FINANCE_FIELDS)
    feishu = read_table(data_dir / "feishu_base.csv", FEISHU_FIELDS)
    issues = []
    unresolved_stores = set()

    def issue(state, evidence, action):
        issues.append((state, evidence, action))

    def clean(row, location):
        result = {key: value.strip() for key, value in row.items()}
        for key in row:
            if row[key] != result[key]:
                issue("Resolved", f"{location}: {key} = {row[key]!r}", "Trimmed outer whitespace; meaning and amount unchanged.")
        return result

    def canonical_store(value, location):
        store = STORE_ALIASES.get(value, value)
        if value != store:
            issue("Resolved", f"{location}: {value!r}", f"Explicit alias to {store!r}; no fuzzy matching.")
        return store

    # Deduplicate on raw fields before normalization. Any conflicting version is fatal.
    seen_orders = {}
    orders = {}
    for line, raw in enumerate(finance, 2):
        row = clean(raw, f"finance row {line}")
        order_no = row[FINANCE_FIELDS[0]]
        if not order_no:
            raise DataError(f"Missing order number at finance row {line}")
        if order_no in seen_orders:
            if raw != seen_orders[order_no]:
                raise DataError(f"Conflicting order {order_no}; no new outputs written")
            issue("Resolved", f"finance row {line}: repeated {order_no}",
                  "Removed one identical copy; excluded CNY " + (row[FINANCE_FIELDS[3]] or "unknown") + " from double counting.")
            continue
        seen_orders[order_no] = raw
        item = row[FINANCE_FIELDS[1]]
        store = canonical_store(row[FINANCE_FIELDS[2]], order_no)
        if not item or not store:
            raise DataError(f"Missing store/item for {order_no}")
        key = (store, item)
        if key in orders:
            raise DataError(f"Ambiguous finance key {key}: distinct orders; manual review required")
        amount = parse_amount(row[FINANCE_FIELDS[3]])
        date = parse_date(row[FINANCE_FIELDS[4]])
        orders[key] = {"order_no": order_no, "amount": amount}
        if amount is None:
            issue("Open", f"{order_no}: {store}, {item}; amount is blank", "Unknown, not zero. Excluded from known subtotal; missing_amount_count +1.")
        elif "," in row[FINANCE_FIELDS[3]]:
            issue("Resolved", f"{order_no}: amount {row[FINANCE_FIELDS[3]]!r}", f"Parsed as Decimal {amount:.2f} CNY; no exchange-rate conversion.")
        if row[FINANCE_FIELDS[4]] != date:
            issue("Resolved", f"{order_no}: date {row[FINANCE_FIELDS[4]]!r}", f"Parsed as {date}; dates are not join keys.")
        if not date.startswith("2025-"):
            unresolved_stores.add(store)
            issue("Open", f"{order_no}: date {date} outside stated 2025 period", "Retained with a visible period exception; group marked incomplete.")

    operations = {}
    city_by_store = {}
    for line, raw in enumerate(feishu, 2):
        row = clean(raw, f"Feishu row {line}")
        item, store, city, status = (row[field] for field in FEISHU_FIELDS)
        store = canonical_store(store, f"Feishu row {line}")
        if not all((item, store, city, status)):
            raise DataError(f"Missing required Feishu value at row {line}")
        key = (store, item)
        if key in operations:
            raise DataError(f"Ambiguous Feishu key {key}; manual review required")
        if store in city_by_store and city_by_store[store] != city:
            raise DataError(f"Conflicting cities for {store}")
        city_by_store[store] = city
        operations[key] = row
        if status not in {"Done", "In progress"}:
            unresolved_stores.add(store)
            issue("Open", f"Feishu row {line}: status {status!r}", "Retained; status is not an amount filter. Group marked incomplete.")

    by_store = {}
    for store, item in sorted(orders.keys() | operations.keys()):
        if store not in by_store:
            city = city_by_store.get(store, "UNKNOWN")
            by_store[store] = {"store": store, "city": city, "amount": Decimal(0),
                               "missing_amount_count": 0, "finance_only_count": 0, "feishu_only_count": 0}
            if city == "UNKNOWN":
                unresolved_stores.add(store)
                issue("Open", f"{store}: no city mapping in Feishu", "Retained in explicit UNKNOWN city bucket; no geographic inference.")
        group = by_store[store]
        key = (store, item)
        if key in orders:
            order = orders[key]
            if order["amount"] is None:
                group["missing_amount_count"] += 1
            else:
                group["amount"] += order["amount"]
            if key not in operations:
                group["finance_only_count"] += 1
                issue("Open", f"{order['order_no']}: finance-only {store}, {item}",
                      f"Retained amount {order['amount']} CNY; city comes only from the same store's consistent Feishu mapping. No same-store item substitution.")
        else:
            group["feishu_only_count"] += 1
            issue("Open", f"Feishu-only {store}, {item}; status {operations[key][FEISHU_FIELDS[3]]}",
                  "No financial amount supplied; retained as an unmatched item. No amount invented; not included in missing_amount_count (finance blanks only).")

    counters = ("missing_amount_count", "finance_only_count", "feishu_only_count")
    by_city = {}
    stores = []
    for store, group in sorted(by_store.items()):
        complete = store not in unresolved_stores and not any(group[c] for c in counters)
        stores.append({"store": store, "city": group["city"], "known_total_cny": f"{group['amount']:.2f}",
                       **{c: group[c] for c in counters}, "is_complete": str(complete).lower()})
        city = by_city.setdefault(group["city"], {"amount": Decimal(0), **{c: 0 for c in counters}, "complete": True})
        city["amount"] += group["amount"]
        city["complete"] &= complete
        for counter in counters:
            city[counter] += group[counter]
    cities = [{"city": name, "known_total_cny": f"{g['amount']:.2f}",
               **{c: g[c] for c in counters}, "is_complete": str(g["complete"]).lower()}
              for name, g in sorted(by_city.items())]
    stats = {"finance_rows": len(finance), "unique_orders": len(orders), "feishu_rows": len(feishu),
             "matched": len(orders.keys() & operations.keys()),
             "finance_only": len(orders.keys() - operations.keys()),
             "feishu_only": len(operations.keys() - orders.keys())}
    known_total = sum((g["amount"] for g in by_store.values()), Decimal(0))

    def escape(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = ["# Procurement reconciliation issues", "", "## Coverage and accounting policy", "",
             f"Finance: {stats['finance_rows']} rows, {stats['unique_orders']} unique orders. Feishu: {stats['feishu_rows']} rows. "
             f"Matched: {stats['matched']}; finance-only: {stats['finance_only']}; Feishu-only: {stats['feishu_only']}.", "",
             f"Known financial subtotal: **CNY {known_total:,.2f}**. This is not a verified complete procurement total.", "",
             "All statuses are included: Done and In progress are operational labels, not payment or eligibility evidence. "
             "All money uses the finance amount_cny field, including overseas stores; no currency conversion. "
             "Feishu has no order identifier, so the documented store/item key is an assumption, validated for uniqueness before joining.", "",
             "Both summary files retain known subtotals. missing_amount_count counts blank finance amounts only; "
             "Feishu-only items have separate counts. is_complete is false for missing money, either kind of unmatched item, "
             "unknown cities or other open exceptions. A true value means complete under these checks, not independently certified.", "",
             "## Evidence and handling", "", "| State | Evidence | Handling / amount impact |", "| --- | --- | --- |"]
    lines += ["| " + " | ".join(escape(x) for x in row) + " |" for row in issues]
    lines += ["", "## Outstanding uncertainty", "",
              "The brewing-machine amount is unknown. Nanjing's delivery scooters and deep cleaning are different items; "
              "their common store does not prove they are the same purchase. No completion-date or payment-date conclusions can be drawn.", "",
              "## One question for Operations", "",
              "Do both exports cover the same complete procurement population, and which authoritative, order-ID-linked register can we use to reconcile them?", "",
              "Why: a shared register can establish whether unmatched items are omissions, timing differences or separate purchases, "
              "and provide a traceable source for the missing amount. The present exports alone cannot settle those questions.", ""]
    return Reconciliation(stores, cities, "\n".join(lines), stats)
