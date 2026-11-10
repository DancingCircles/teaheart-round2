# Validation record

Observed at 2026-11-10 19:09:30 UTC+08:00. Runtime: Python 3.12.14.
Implementation started at 2026-11-10 18:57:32 UTC+08:00.
The historical automated session through the archive smoke test elapsed
11.97 minutes. This session timing is retained as execution provenance, not as
a complete measure of applicant time. The applicant estimates initial
implementation at approximately 15 minutes, excluding prior planning.
Subsequent review and documentation were not fully timed; total time spent is
unknown. The log below is the original implementation record.

## Commands and observed results

```sh
python -S -B main.py
python -S -B -m unittest discover -s tests -v
```

`-S` disables site-package initialization. No third-party dependency is needed.

```text
Wrote 5 files; 12 summaries; 3 numeric checks flagged.
Flagged summaries are review results, not a program failure.
Reconciliation: {"feishu_only": 1, "feishu_rows": 10, "finance_only": 1, "finance_rows": 11, "matched": 9, "unique_orders": 10}
```

```text
test_changed_summary_invalidates_old_manual_review (test_submission.CliTests.test_changed_summary_invalidates_old_manual_review) ... ok
test_clean_run_is_reproducible_and_has_all_twelve_enquiries (test_submission.CliTests.test_clean_run_is_reproducible_and_has_all_twelve_enquiries) ... ok
test_client_and_received_fields_cannot_supply_numeric_evidence (test_submission.CliTests.test_client_and_received_fields_cannot_supply_numeric_evidence) ... ok
test_invalid_input_does_not_publish_results (test_submission.CliTests.test_invalid_input_does_not_publish_results) ... ok
test_chinese_digit_sequences_do_not_collapse_to_last_digit (test_submission.NumericCheckTests.test_chinese_digit_sequences_do_not_collapse_to_last_digit) ... ok
test_equivalent_formats (test_submission.NumericCheckTests.test_equivalent_formats) ... ok
test_numeric_format_property_over_many_values (test_submission.NumericCheckTests.test_numeric_format_property_over_many_values) ... ok
test_numeric_presence_does_not_validate_scenario (test_submission.NumericCheckTests.test_numeric_presence_does_not_validate_scenario) ... ok
test_unsupported_numbers_are_flagged (test_submission.NumericCheckTests.test_unsupported_numbers_are_flagged) ... ok
test_conflicting_duplicate_order_is_rejected (test_submission.ReconciliationTests.test_conflicting_duplicate_order_is_rejected) ... ok
test_conflicting_store_cities_are_rejected (test_submission.ReconciliationTests.test_conflicting_store_cities_are_rejected) ... ok
test_distinct_orders_cannot_share_a_join_key (test_submission.ReconciliationTests.test_distinct_orders_cannot_share_a_join_key) ... ok
test_duplicate_feishu_key_is_rejected (test_submission.ReconciliationTests.test_duplicate_feishu_key_is_rejected) ... ok
test_malformed_money_and_missing_headers_fail (test_submission.ReconciliationTests.test_malformed_money_and_missing_headers_fail) ... ok
test_real_orders_conserve_money_without_double_counting (test_submission.ReconciliationTests.test_real_orders_conserve_money_without_double_counting) ... ok
test_unmapped_store_stays_visible_in_unknown_city (test_submission.ReconciliationTests.test_unmapped_store_stays_visible_in_unknown_city) ... ok
test_zero_is_known_and_feishu_only_store_is_incomplete (test_submission.ReconciliationTests.test_zero_is_known_and_feishu_only_store_is_incomplete) ... ok

----------------------------------------------------------------------
Ran 17 tests in 0.396s

OK
```

The suite has 17 test methods, including 200 deterministic numeric-format cases
and table-driven accepted/rejected formats. There are no skipped tests, sleeps,
live network calls or mocks. Tests use copied inputs and temporary directories.

## Independent acceptance checks

- Original input copies are byte-identical to the supplied files (SHA-256 below).
- Both aggregate files sum to CNY 210,500.00; the explicit city expectations in
  tests are independent literals, not values computed with the production code.
- Duplicate O25-004 does not add another CNY 56,000.00.
- Hangzhou's blank amount stays unknown; Nanjing's distinct unmatched items remain visible.
- Twelve unique enquiry IDs; each saved summary has two sentences, checked
  structurally and reviewed against its source by the same assistant.
- Nine numeric checks pass; EQ-03, EQ-06 and EQ-12 are flagged with conversion/derived reasons.
- Three result CSVs have UTF-8 BOM; financial outputs keep two decimal places.
- A fresh-directory CLI run is byte-for-byte deterministic on repeated execution.
- ZIP extracted into a clean directory: offline `main.py` succeeded, regenerated
  all five generated files byte-for-byte, and all 17 tests passed again.
- Only explicitly listed deliverables are packed; caches and authoring scripts
  are excluded. Final ZIP CRC/content checks pass.
- Original README: 267 whitespace-delimited words, under the 300-word limit.
  The current README was edited later; see the follow-up validation below.

## Input integrity

| File | SHA-256 |
| --- | --- |
| finance_export.csv | `58859ad69f0e24793d41d52b8784e09edb7209aa6e626639af980e603de4fd76` |
| feishu_base.csv | `c3d4474f2fef2cbb0176b18fd74497111cb88f57e76eecd927ca8f6c077a6620` |
| enquiries.csv | `de0a8c361210fec544134a9f0010c286b0e2eea7d72aa3e7f1e95416b49795a6` |

## Regression evidence and remaining limits

The Chinese digit-sequence regression was observed failing before the fix and
passing afterwards ([AI_USAGE.md](AI_USAGE.md)). Initial missing-module scaffold errors are not
claimed as behavioral TDD evidence for the whole project.

Executable tests prove a semantically swapped 5/50-cup summary can pass a numeric
presence check. Grammar is intentionally bounded; business truth, general language
understanding and independent human review remain outside automated assurance.
No formatter/linter/type-checker dependency was installed. All Python source was
compiled with the standard-library compiler as an additional syntax check.

## Follow-up documentation validation

On 2026-11-10, review labels were clarified as assistant review, document links
were added, and Git ignore rules were introduced. No reconciliation or numeric
matching rules changed. Outputs were regenerated and all 17 tests passed again.
The three reconciliation outputs and all input files remain byte-identical.
All 12 summaries and their check results are unchanged: 9 pass and 3 are flagged.
The current README contains 268 whitespace-delimited words (limit: 300);
relative Markdown links were checked against existing files. Historical ZIP
checks above apply to the original archive, not an updated release archive.
