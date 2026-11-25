# Synthetic messy-ledger dataset (for the cleaning-agent eval harness)

All data is **synthetic** (fictional companies, generated double-entry ledgers). 8 clients, ~57k journal entries, ~152k ledger lines, ~153k exported data rows.
Every messy file is derived from a balanced clean ledger, and every injected error is logged, so any cleaner can be scored exactly.

## Files
| Path | What it is |
|---|---|
| `messy/*` | What a cleaner receives: one ERP-style export per client (7 CSV, 1 Excel cash book) |
| `standard_chart_of_accounts.csv` | The target taxonomy (62 accounts) + `risk_tier` and `error_cost_weight` (3/2/1) for cost-weighted scoring |
| `truth/clean_ledger_all_clients.csv` | Answer key: one row per ledger line, mapped to a standard account |
| `truth/row_truth_map.csv` | Alignment: each physical row in each messy file -> `line_id` + injected `error_types` |
| `truth/trial_balance_truth.csv` | Per-client TB: `net_full` (everything) and `net_in_export` (excludes lines that never reached the file) |
| `manifest.csv` | Client list, layout, messiness level, row counts |

## Clients
| client_id | Layout | Messiness | Notable traps |
|---|---|---|---|
| harborview_dental | QuickBooks-style, grouped by account (account only in section header) | med | merged labels, renamed accounts, "Uncategorized Expense" |
| brightleaf_organics | Xero-style flat, UK dates, GBP, VAT, FY Apr-Mar | high | label variants, blank accounts, lost rows |
| northgate_construction | Sage-style single signed Amount, client codes x10 | high | repeated headers, monthly subtotals, "Travel & Meals" merge |
| lumen_software | NetSuite-style hierarchical accounts, ISO dates | low | deferred revenue, clean-ish control |
| alder_finch_llp | Xero-style, ISO dates | low | control group |
| rivera_restaurants | QuickBooks grouped | med | merged COGS/travel labels, "Tips Payable" |
| kestrel_logistics | German columns/labels, `1.234,56` numbers, EUR | high | German account names, SKR-style codes, mojibake batches |
| sunrise_property | Hand-kept Excel cash book, 4 quarterly sheets | high | one-sided entries, free-text categories, text dates/amounts |

## Linking a messy row to truth
`row_truth_map`: (`file`, `sheet`, `row_number` = 1-based physical row) -> `line_id`, then join `line_id` to the clean ledger.
`row_kind` = data | title | header | repeat_header | section_header | section_total | subtotal | grand_total | blank | footer.
A cleaner should drop all non-`data` rows. `is_duplicate=1` rows should be removed (the original is kept).

## Error taxonomy (`error_types`, `;`-separated, `:` = subtype)
label_variant (case/typo/abbrev/alt_name/whitespace/suffix/codeprefix) - missing_account - uncategorized_label - legacy_label (account renamed mid-year) -
date_alt_format (`:ambiguous` when day<=12 so D/M vs M/D is undecidable from the cell) - date_excel_serial - missing_date (recoverable from sibling lines of the same doc) - date_no_year / date_text_* (cash book) -
amount_format ($, trailing space, no decimals, (neg)) - credit_as_negative_debit - drcr_suffix - sign_flip - amount_digit_error (the last two unbalance the entry) -
blank_description - whitespace - mojibake - duplicate_exact / duplicate_near (also may sit up to 30 rows away).

## Things to know when scoring
- `truth.in_export=0` lines never appear in the file: `dropped_row` (lost in export), `implied_cashbook_offset` and `opening_balance_not_in_cashbook` (cash book only). Compare cleaned TBs against `net_in_export`; do not expect the cash-book client to tie to a full TB.
- `inherently_ambiguous_label=1`: the client's label maps to more than one standard account (e.g. "Travel & Meals"); the truth follows the transaction's nature, so description is needed.
- sign_flip / amount_digit_error rows keep the *intended* amount in truth. A good cleaner flags them via unbalanced entries (group by document reference).
- Every GL export includes an opening-balance entry on day 1, so the exported TB ties to year-end balances.
