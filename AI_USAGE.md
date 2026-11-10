# AI use and verification record

## Tool and provenance

Codex, using the current conversation model, assisted with document/data
inspection, design, Python code, the twelve summaries, review notes and tests.
No separate model API, model-provider SDK, internet source or paid service was
used to generate this submission. The provided data are fictional. Saved summaries
are in `data/model_summaries.csv`; rerunning the program checks them offline.

The review notes are the same assistant's review, not an independent human audit.
The applicant should read the code, confirm the decisions and update this account
of assistance if making further edits. Do not represent this as unaided work.

## Summary-generation instructions followed

Write exactly two English sentences for each enquiry for an English-reading
operations manager. Preserve quantities, currencies, conditions, dates,
uncertainty and the scope of each claim. Distinguish an initial order from a later
order and all-stall sales from the proposed store's sales. Do not invent a price,
date or industry benchmark. Explicitly label arithmetic as derived. Save the
generated text so the number check is reproducible without invoking a model.

The saved summaries contain a valid quantity-scale conversion in EQ-03 and
explicit arithmetic in EQ-06/EQ-12. The code deliberately flags these under the
strict source-expression policy. Their explanations do not force a pass.

## A genuine AI mistake and its correction

The first Chinese-number parser accumulated tens/hundreds but overwrote the
current digit for a unit-free sequence. It therefore normalized `二〇二七` to
`7`, rather than `2027`. This defect was discovered during code review after the
initial fourteen tests passed; it does not occur in the supplied raw enquiries,
whose multi-digit quantities use Arabic digits.

A regression test was added before the fix. The observed failing run was:

```text
python -m unittest discover -s tests -v
FAIL: test_chinese_digit_sequences_do_not_collapse_to_last_digit
AssertionError: False is not true
Ran 17 tests
FAILED (failures=1)
```

The parser now joins unit-free digit sequences explicitly. The same test asserts
both that `2027` matches and that `7` does not. The final complete test run, including
that regression, is recorded in [VALIDATION.md](VALIDATION.md). This is a real implementation
error, not an intentionally introduced hallucination or a claim about model
quality in general.

## Checks and residual judgement

The assistant compared the original exports, kept identical-order deduplication
separate from store/item joining, reviewed all twelve summaries and inspected
the expression-level audit. Automated tests verify deterministic reruns, sums,
unmatched records, conflict rejection, input scope and stale review detection.
An executable counterexample proves numeric presence does not validate semantics.

See [CHECKER.md](CHECKER.md) for supported grammar, deliberate strict failures and limitations.
Initial implementation: approximately 15 minutes, excluding prior planning.
This is the applicant's estimate; the historical automated-session timing in
[VALIDATION.md](VALIDATION.md) is not a complete measure of applicant time. Subsequent review and documentation work were not fully timed; the
total time spent is unknown. Later work clarified review labels, added document
links and Git ignore rules, and regenerated and rechecked the outputs. At the end of initial preparation, no work had been sent to HR and no Git
commit/push had been performed. Publishing the repository is a separate,
subsequently authorized step.
