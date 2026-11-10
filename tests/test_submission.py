"""Run with: python -m unittest discover -s tests -v (standard library only)."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

from number_check import check_summary
from main import build_summaries
from reconcile import DataError, reconcile


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"
        shutil.copytree(ROOT / "data", self.data)

    def test_real_orders_conserve_money_without_double_counting(self):
        result = reconcile(self.data)
        cities = {r["city"]: r for r in result.cities}
        self.assertEqual(result.stats["finance_rows"], 11)
        self.assertEqual(result.stats["unique_orders"], 10)
        self.assertEqual(result.stats["matched"], 9)
        self.assertEqual(result.stats["finance_only"], 1)
        self.assertEqual(result.stats["feishu_only"], 1)
        self.assertEqual({c: r["known_total_cny"] for c, r in cities.items()}, {
            "Xiamen": "115500.00", "Johor Bahru": "42200.00",
            "Qingdao": "32400.00", "Hangzhou": "11500.00", "Nanjing": "8900.00",
        })
        self.assertEqual(sum(Decimal(r["known_total_cny"]) for r in result.stores), Decimal("210500"))
        self.assertEqual(sum(Decimal(r["known_total_cny"]) for r in result.cities), Decimal("210500"))
        self.assertEqual(cities["Hangzhou"]["missing_amount_count"], 1)
        self.assertEqual(cities["Hangzhou"]["is_complete"], "false")
        self.assertEqual(cities["Nanjing"]["finance_only_count"], 1)
        self.assertEqual(cities["Nanjing"]["feishu_only_count"], 1)
        self.assertEqual(cities["Nanjing"]["is_complete"], "false")
        self.assertEqual(cities["Xiamen"]["is_complete"], "true")
        self.assertIn("Deep cleaning service", result.issues_md)
        self.assertIn("O25-010", result.issues_md)

    def test_conflicting_duplicate_order_is_rejected(self):
        path = self.data / "finance_export.csv"
        rows = read_csv(path)
        duplicate = dict(rows[0], **{"金额 amount_cny": "33,000"})
        write_csv(path, rows + [duplicate])
        with self.assertRaisesRegex(DataError, "Conflicting order"):
            reconcile(self.data)

    def test_distinct_orders_cannot_share_a_join_key(self):
        path = self.data / "finance_export.csv"
        rows = read_csv(path)
        write_csv(path, rows + [dict(rows[0], **{"订单编号 order_no": "EXTRA"})])
        with self.assertRaisesRegex(DataError, "Ambiguous finance key"):
            reconcile(self.data)

    def test_duplicate_feishu_key_is_rejected(self):
        path = self.data / "feishu_base.csv"
        rows = read_csv(path)
        write_csv(path, rows + [rows[0]])
        with self.assertRaisesRegex(DataError, "Ambiguous Feishu key"):
            reconcile(self.data)

    def test_conflicting_store_cities_are_rejected(self):
        path = self.data / "feishu_base.csv"
        rows = read_csv(path)
        rows[3]["城市 city"] = "Another city"
        write_csv(path, rows)
        with self.assertRaisesRegex(DataError, "Conflicting cities"):
            reconcile(self.data)

    def test_unmapped_store_stays_visible_in_unknown_city(self):
        path = self.data / "finance_export.csv"
        rows = read_csv(path)
        rows[0]["门店 store"] = "Unmapped branch"
        write_csv(path, rows)
        result = reconcile(self.data)
        unknown = next(r for r in result.cities if r["city"] == "UNKNOWN")
        self.assertEqual(unknown["known_total_cny"], "32000.00")
        self.assertEqual(unknown["is_complete"], "false")
        self.assertIn("Unmapped branch", result.issues_md)

    def test_zero_is_known_and_feishu_only_store_is_incomplete(self):
        path = self.data / "finance_export.csv"
        rows = read_csv(path)
        rows[5]["金额 amount_cny"] = "0"
        write_csv(path, rows)
        path = self.data / "feishu_base.csv"
        rows = read_csv(path)
        rows.append({"采购项目 item": "New service", "门店 store": "New branch",
                     "城市 city": "New city", "状态 status": "Done"})
        write_csv(path, rows)
        cities = {r["city"]: r for r in reconcile(self.data).cities}
        self.assertEqual(cities["Hangzhou"]["missing_amount_count"], 0)
        self.assertEqual(cities["Hangzhou"]["is_complete"], "true")
        self.assertEqual(cities["New city"]["feishu_only_count"], 1)
        self.assertEqual(cities["New city"]["is_complete"], "false")

    def test_malformed_money_and_missing_headers_fail(self):
        path = self.data / "finance_export.csv"
        rows = read_csv(path)
        rows[0]["金额 amount_cny"] = "32,00"
        write_csv(path, rows)
        with self.assertRaisesRegex(DataError, "Invalid amount"):
            reconcile(self.data)
        path.write_text("wrong,header\na,b\n", encoding="utf-8")
        with self.assertRaisesRegex(DataError, "headers"):
            reconcile(self.data)


class NumericCheckTests(unittest.TestCase):
    def test_chinese_digit_sequences_do_not_collapse_to_last_digit(self):
        self.assertTrue(check_summary("二〇二七 people", "2027 people")["check_passed"])
        self.assertFalse(check_summary("二〇二七 people", "7 people")["check_passed"])

    def test_equivalent_formats(self):
        examples = [
            ("5,000 L at MYR 4.20; 3.6% fat and 3.2 g per 100 mL.",
             "5000 L at MYR 4.2; 3.6 percent fat and 3.2 g per 100 mL."),
            ("two counters and twenty-five cups", "2 counters and 25 cups"),
            ("一家店，35 克以下", "one store, below 35 grams"),
            ("Deliver at 9 am on 1 Feb 2027", "Deliver at 09:00 on February 1, 2027"),
            ("28 Oct at 14:30", "October 28 at 14:30"),
            ("2027 年 3 月前", "before March 2027"),
            ("45 平方米; 6 m2", "45 square metres; 6 m²"),
            ("first store", "1st store"),
        ]
        for source, summary in examples:
            with self.subTest(source=source):
                result = check_summary(source, summary)
                self.assertTrue(result["check_passed"], result["unmatched"])
                self.assertGreater(len(result["summary_tokens"]), 0)

    def test_unsupported_numbers_are_flagged(self):
        examples = [
            ("500 cups", "50 cups", "50"),
            ("8 trays of 12 cups", "96 cups", "96"),
            ("220 万元", "RMB 2.2 million", "2.2 million"),
            ("1.2 million", "1.2", "1.2"),
            ("5% of cups", "5 cups", "5"),
            ("14:30", "14:00", "14:00"),
            ("before March 2027", "before April 2027", "April 2027"),
            ("5 cups", "5000 cups", "5000"),
            ("1000 cups", "1e3 cups", "1e3"),
        ]
        for source, summary, unsupported in examples:
            with self.subTest(summary=summary):
                result = check_summary(source, summary)
                self.assertFalse(result["check_passed"])
                self.assertIn(unsupported, [t["raw"] for t in result["unmatched"]])

    def test_numeric_presence_does_not_validate_scenario(self):
        result = check_summary(
            "First day: 5 cups. Later celebration: 50 cups, date unknown.",
            "First day: 50 cups. Later celebration: 5 cups.",
        )
        self.assertTrue(result["check_passed"])

    def test_numeric_format_property_over_many_values(self):
        for value in range(1000, 1200):
            with self.subTest(value=value):
                result = check_summary(f"{value:,} cups", f"{value}.00 cups")
                self.assertTrue(result["check_passed"])
                self.assertEqual(len(result["summary_tokens"]), 1)


class CliTests(unittest.TestCase):
    def test_client_and_received_fields_cannot_supply_numeric_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            shutil.copytree(ROOT / "data", data)
            rows = read_csv(data / "enquiries.csv")
            rows[3]["client"] = "Factory 777"
            write_csv(data / "enquiries.csv", rows)
            rows = read_csv(data / "model_summaries.csv")
            rows[3]["summary"] = "The customer requests 777 cups. Delivery is requested."
            write_csv(data / "model_summaries.csv", rows)
            review_path = data / "numeric_reviews.json"
            reviews = json.loads(review_path.read_text(encoding="utf-8"))
            del reviews["EQ-04"]
            review_path.write_text(json.dumps(reviews), encoding="utf-8")
            results, _ = build_summaries(data)
            row = next(row for row in results if row["enquiry_id"] == "EQ-04")
            self.assertEqual(row["check_passed"], "false")
            self.assertIn("777", row["notes"])
            self.assertIn("manual classification required", row["notes"])

    def test_changed_summary_invalidates_old_manual_review(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            shutil.copytree(ROOT / "data", data)
            rows = read_csv(data / "model_summaries.csv")
            rows[6]["summary"] = "It needs 50 cups initially. It needs 5 cups later."
            write_csv(data / "model_summaries.csv", rows)
            with self.assertRaisesRegex(DataError, "Stale manual review for EQ-07"):
                build_summaries(data)

    def test_clean_run_is_reproducible_and_has_all_twelve_enquiries(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "result"
            command = [sys.executable, str(ROOT / "main.py"), "--output-dir", str(out)]
            first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual({p.name for p in out.iterdir()}, {
                "totals_by_store.csv", "totals_by_city.csv", "issues.md",
                "summaries.csv", "number_audit.json",
            })
            before = {p.name: p.read_bytes() for p in out.iterdir()}
            second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()})
            rows = read_csv(out / "summaries.csv")
            self.assertEqual(len(rows), 12)
            self.assertEqual({r["enquiry_id"] for r in rows}, {f"EQ-{i:02}" for i in range(1, 13)})
            by_id = {r["enquiry_id"]: r for r in rows}
            self.assertEqual(by_id["EQ-03"]["check_passed"], "false")
            self.assertIn("conversion", by_id["EQ-03"]["notes"])
            self.assertEqual(by_id["EQ-06"]["check_passed"], "false")
            self.assertIn("derived", by_id["EQ-06"]["notes"])
            self.assertEqual(by_id["EQ-07"]["check_passed"], "true")
            self.assertEqual(json.loads((out / "number_audit.json").read_text(encoding="utf-8"))["EQ-06"]["unmatched"][0]["raw"], "96")
            self.assertTrue((out / "summaries.csv").read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_invalid_input_does_not_publish_results(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            out = Path(directory) / "result"
            shutil.copytree(ROOT / "data", data)
            rows = read_csv(data / "finance_export.csv")
            write_csv(data / "finance_export.csv", rows + [dict(rows[0], **{"金额 amount_cny": "1"})])
            result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--data-dir", str(data),
                                     "--output-dir", str(out)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Conflicting order", result.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
