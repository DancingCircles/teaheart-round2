# Teaheart procurement and numeric-output checks

## Run

Python 3.10+; standard library only. From this directory:

```sh
python main.py
python -m unittest discover -s tests -v
```

Optional: `python main.py --output-dir results`. Rerunning regenerates the
three result CSVs, [issues](issues.md) and [numeric audit](number_audit.json).
CSV files use UTF-8 BOM. Saved summaries are checked offline; no model API,
network or credentials are needed.

## Decisions and results

Identical orders are deduplicated. An explicit store alias and unique store/item
keys link the systems; conflicts stop generation. All statuses are included.
Financial amounts are CNY, including overseas stores.

Known subtotals sum to CNY 210,500. Hangzhou has an unknown brewing-machine
amount; Nanjing has separate unmatched scooters and cleaning records. Both are
incomplete. Blank money is not zero; Feishu-only items are counted separately.
See [store totals](totals_by_store.csv) and [city totals](totals_by_city.csv).

Twelve saved, two-sentence English summaries are checked against subject/body
only. EQ-03's 2.2 million is a valid conversion; EQ-06's 96 and EQ-12's approximate
100 are derived. All three remain flagged under the strict expression rule.
[Summary results](summaries.csv) explain them; [check rules](CHECKER.md) describe
the supported grammar.

## AI, time and limitations

Codex assisted with code, summaries, review and tests. Its initial Chinese-number
parser reduced a digit sequence to its last digit; a regression test verified
the fix. See [AI usage](AI_USAGE.md) and [validation](VALIDATION.md).

Initial implementation: approximately 15 minutes, excluding prior planning.
Subsequent review and documentation work were not fully timed; total time is
unknown. No planned implementation items remain; source-data questions remain open.

Numeric presence cannot prove correct entities, currencies, units, date roles,
negation, omissions or meaning. Unsupported expressions may escape extraction.
Assistant review is not independent human review.
