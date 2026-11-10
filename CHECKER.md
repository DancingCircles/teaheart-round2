# Number-check contract

`check_summary(source, summary)` extracts expressions from each text and requires
every summary expression to have an equal normalized expression in the source.
The CLI constructs the source from **subject + newline + body only**. Client,
received date, other enquiries, model knowledge and review notes cannot supply
evidence. `number_audit.json` records the raw expression, normalized key, matching
source spans and unmatched expressions for every enquiry. Offsets are zero-based
Python Unicode code-point positions, with an exclusive end.

## Supported formats

- Signed integers and decimals, with optional well-formed thousands separators.
  `5,000` equals `5000`; `4.20` equals `4.2`. Matches are whole expressions,
  never substrings (`50` does not match `500`).
- English cardinal words from zero through nine hundred and ninety-nine,
  including forms such as `twenty-five` and `one hundred and two`.
- Chinese digit strings and simple tens/hundreds, including `一`, `三十五`,
  `一百二十三` and `二〇二七`. This is a small explicit grammar, not a general
  Chinese language parser.
- English ordinals first through twelfth, and digit ordinals such as `1st`.
  Ordinals have a separate key from cardinal quantities.
- `%`, `percent` and `百分之` expressions keep their percentage type; `5%`
  cannot be supported by an ordinary `5` alone.
- Magnitudes `k`, `thousand`, `million`, `billion`, `千`, `万`, `亿` retain
  their scale. Equivalent labels such as `k`/`thousand`/`千` can match, but
  multiplying by the scale is **not** an automatic pass. Thus `220 万` and
  `2.2 million` are deliberately different expressions, even though their
  financial values are equal.
- Times such as `9 am`, `09:00`, `14:30` and `2:30 pm` use an explicit
  24-hour clock key. A plain `9` cannot support a time expression.
- Numeric full dates (`2027-02-01`, `2027/02/01`), day/month names with optional
  year (`1 Feb 2027`, `February 1, 2027`, `28 Oct`), month/year (`March 2027`)
  and Arabic-digit Chinese dates (`2027 年 3 月`) keep their date structure.
  Partial dates remain partial; no year is inferred from the received date.
- Square metres written as `m2`, `m²`, `square metres`, `square meters` or
  `平方米` use the same area key. The exponent is part of the unit, not a
  separate order quantity. This changes spelling, not physical magnitude.
- Uncovered digit-bearing words, unsupported scientific notation or invalid
  parsed dates/times are flagged as unsupported syntax, never used as matches.

## Pass/fail and assistant review

All extracted expressions must match for `check_passed=true`. A summary with no
numeric expressions passes vacuously, with an explicit note. Source occurrences
can support repeated summary occurrences; this is presence, not a count audit.

`data/model_summaries.csv` contains the fixed model outputs. Assistant review
notes in `data/numeric_reviews.json` were produced by the same Codex assistant,
not by an independent person or a second model. Each review is bound to SHA-256
hashes of the exact source and summary; changes invalidate old notes. These notes
explain flagged values but **cannot override** computed pass/fail.

To change a summary, edit the saved CSV, review it against its subject/body and
update the review hashes and explanations. Alternatively remove that ID's review
entry while experimenting: checks still run, but notes explicitly say review is
pending. Do not use a pending review as evidence of semantic correctness.

The supplied run flags:

| Enquiry | Expression | Review judgement |
| --- | --- | --- |
| EQ-03 | `2.2 million` | Conversion of `220 万元`; financially correct, not a direct expression match. |
| EQ-06 | `96` | Derived from `8 * 12`; arithmetic is valid but 96 is not stated. |
| EQ-12 | `100` | Approximately `2,000 * 5%` per day; approximate and derived. |

These transparent, valid additions remain flagged under the chosen strict rule;
none is represented as a fabricated source quotation. Invented unsupported
numbers are exercised in tests, not inserted into the submitted business summaries.

## Limits

An equal number may belong to the wrong subject, date, order or unit. Except for
the explicit percentage/time/date/area/scale types above, this checker does not
bind currencies or units to quantities. It does not assess omissions, negation,
business plausibility, uncertain claims or a full sentence's meaning. For example,
swapping the initial 5 cups with the later 50 cups in EQ-07 can still pass.

Unsupported quantitative words such as `a dozen`, implicit durations such as
`annual`, arbitrary worded numbers and other languages may escape extraction.
This is an explicit grammar sufficient for the supplied examples, not a guarantee
that every possible numerical statement can be recognized. Sentence count and
semantic fidelity were reviewed separately for all twelve saved summaries.

## Failure behavior

Malformed inputs, ambiguous procurement joins and stale review snapshots exit
with code 2 before writing new results. Previous outputs, if any, are not evidence
of a successful failed rerun. Validation/serialization precedes publishing; each
file is replaced through a temporary file. Replacement of the whole output set is
not transactional: an operating-system write failure can leave a partial set and
requires a successful rerun. Numeric flags are normal review results, so a valid
run with flags exits with code 0.

The legacy JSON key `manual_review` and internal stale-review error names are
retained for compatibility; they refer to assistant review, not human review.
