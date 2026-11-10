# Procurement reconciliation issues

## Coverage and accounting policy

Finance: 11 rows, 10 unique orders. Feishu: 10 rows. Matched: 9; finance-only: 1; Feishu-only: 1.

Known financial subtotal: **CNY 210,500.00**. This is not a verified complete procurement total.

All statuses are included: Done and In progress are operational labels, not payment or eligibility evidence. All money uses the finance amount_cny field, including overseas stores; no currency conversion. Feishu has no order identifier, so the documented store/item key is an assumption, validated for uniqueness before joining.

Both summary files retain known subtotals. missing_amount_count counts blank finance amounts only; Feishu-only items have separate counts. is_complete is false for missing money, either kind of unmatched item, unknown cities or other open exceptions. A true value means complete under these checks, not independently certified.

## Evidence and handling

| State | Evidence | Handling / amount impact |
| --- | --- | --- |
| Resolved | O25-001: 'Teaheart Zhongshan Road Store' | Explicit alias to 'Zhongshan Rd 中山路店'; no fuzzy matching. |
| Resolved | O25-001: amount '32,000' | Parsed as Decimal 32000.00 CNY; no exchange-rate conversion. |
| Resolved | O25-001: date '2025/01/15' | Parsed as 2025-01-15; dates are not join keys. |
| Resolved | O25-002: amount '30,200' | Parsed as Decimal 30200.00 CNY; no exchange-rate conversion. |
| Resolved | O25-002: date '2025/02/03' | Parsed as 2025-02-03; dates are not join keys. |
| Resolved | O25-003: amount '17,400' | Parsed as Decimal 17400.00 CNY; no exchange-rate conversion. |
| Resolved | O25-003: date '2025/02/20' | Parsed as 2025-02-20; dates are not join keys. |
| Resolved | O25-004: 'Teaheart Zhongshan Road Store' | Explicit alias to 'Zhongshan Rd 中山路店'; no fuzzy matching. |
| Resolved | O25-004: amount '56,000' | Parsed as Decimal 56000.00 CNY; no exchange-rate conversion. |
| Resolved | O25-004: date '2025/03/11' | Parsed as 2025-03-11; dates are not join keys. |
| Resolved | finance row 6: 门店 store = 'Teaheart Zhongshan Road Store ' | Trimmed outer whitespace; meaning and amount unchanged. |
| Resolved | O25-005: 'Teaheart Zhongshan Road Store' | Explicit alias to 'Zhongshan Rd 中山路店'; no fuzzy matching. |
| Resolved | O25-005: amount '27,500' | Parsed as Decimal 27500.00 CNY; no exchange-rate conversion. |
| Open | O25-006: Teaheart Wulin 武林店, Tea brewing machines 煮茶机; amount is blank | Unknown, not zero. Excluded from known subtotal; missing_amount_count +1. |
| Resolved | O25-006: date '2025/04/18' | Parsed as 2025-04-18; dates are not join keys. |
| Resolved | O25-007: amount '12,000' | Parsed as Decimal 12000.00 CNY; no exchange-rate conversion. |
| Resolved | O25-007: date '2025/05/06' | Parsed as 2025-05-06; dates are not join keys. |
| Resolved | O25-008: amount '15,000' | Parsed as Decimal 15000.00 CNY; no exchange-rate conversion. |
| Resolved | O25-008: date '2025/06/12' | Parsed as 2025-06-12; dates are not join keys. |
| Resolved | finance row 10: repeated O25-004 | Removed one identical copy; excluded CNY 56,000 from double counting. |
| Resolved | O25-009: amount '11,500' | Parsed as Decimal 11500.00 CNY; no exchange-rate conversion. |
| Resolved | O25-009: date '2025/07/01' | Parsed as 2025-07-01; dates are not join keys. |
| Resolved | O25-010: amount '8,900' | Parsed as Decimal 8900.00 CNY; no exchange-rate conversion. |
| Resolved | O25-010: date '2025/08/22' | Parsed as 2025-08-22; dates are not join keys. |
| Open | Feishu-only Teaheart Xinjiekou 新街口店, Deep cleaning service 深度清洁服务; status Done | No financial amount supplied; retained as an unmatched item. No amount invented; not included in missing_amount_count (finance blanks only). |
| Open | O25-010: finance-only Teaheart Xinjiekou 新街口店, Delivery scooters 外卖车 | Retained amount 8900 CNY; city comes only from the same store's consistent Feishu mapping. No same-store item substitution. |

## Outstanding uncertainty

The brewing-machine amount is unknown. Nanjing's delivery scooters and deep cleaning are different items; their common store does not prove they are the same purchase. No completion-date or payment-date conclusions can be drawn.

## One question for Operations

Do both exports cover the same complete procurement population, and which authoritative, order-ID-linked register can we use to reconcile them?

Why: a shared register can establish whether unmatched items are omissions, timing differences or separate purchases, and provide a traceable source for the missing amount. The present exports alone cannot settle those questions.
