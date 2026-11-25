# Ledger cleaning eval

An evaluation harness and live demo console for AI agents that clean messy accounting data. It answers one question: **how do you know the agent is right?**

Eight synthetic firms export their general ledgers the way their own accounting software would (QuickBooks, Xero, Sage, NetSuite, a German DATEV-style file, a hand-kept Excel cash book). About 153,000 rows carry roughly twenty kinds of injected errors, each logged against an exact answer key. Four stand-in cleaning agents are scored on what matters in review: wrong postings, dollars at risk, calibrated confidence, trial-balance tie-out, and how fast an agent learns a new firm.

**Live demo:** _add your Vercel URL here_

All data is synthetic. The agents are deliberately simple stand-ins; the harness is the point. A real agent plugs in by emitting one prediction per input row.

## The page

`public/index.html` is a single self-contained file: fonts, styles, scripts and all data inlined, no build step and no external requests.

| Section | What it shows |
|---|---|
| 01 Console | Raw export in, graded ledger out. Six pipeline stages, a review queue, label confirmation that moves the whole-file score, and a year replay. Keys: R run, S step, X reset, U undo, Enter confirm |
| 02 Network effect | Accuracy as a function of how many other firms the agent has learned from |
| 03 Scoreboard | Held-out test firms, bootstrap intervals, paired comparisons |
| 04 Failure modes | Accuracy by error type, standard against client vocabulary, where the amounts went |
| 05 Audit trail | Any trial-balance line down to the raw rows, and why it differs from the truth |
| 06 Trust and cost | Calibration, accuracy against automation, reviewer-hour economics with adjustable costs |
| 07 Learning a firm | Memory and audit-sampling policies, value of a reviewer confirming labels |
| 08 Inspector | 516 sampled rows with truth and every cleaner's call |
| 09 Spec | Method, limits, tuning log |

Presenter mode (P) steps through seven scripted scenes with N and B, T toggles talking points, F toggles projector size, 1 to 9 jump to sections.

## Headline results (held-out test firms)

| Cleaner | Account accuracy | What it does |
|---|---|---|
| Hybrid | **94.0%** | dictionary, then high-confidence fuzzy, then ML fallback |
| Fuzzy | 90.2% | string similarity, near-duplicate detection, date and sign repairs |
| Rules | 82.8% | exact synonym lookup after normalising the label |
| ML | 79.9% | text classifier trained on other firms only |

- Injected noise (typos, case, renamed accounts) is mostly handled. Labels a firm invented for itself ("Job Costs - Materials", "Tips Payable") are the real gap: 54% for the hybrid cleaner against 100% on standard names.
- A reviewer confirming 10 unfamiliar labels lifts hybrid accuracy from 94.0% to 99.2%.
- Replaying each firm's year, remembering confirmed labels cuts the review rate from 4.3% in month one to 1.3% in month twelve (15% without memory). It also leaks mistakes for labels that map to more than one account; a 5% audit sample recovers most of that.
- Network effect (leave-one-firm-out): overall accuracy rises from 84.1% to 87.0% and plateaus near four firms; accuracy on client-specific vocabulary rises from 21% to 52% and is still climbing.

Four firms are dev (used to tune cutoffs and thresholds) and four are test (never used for tuning or training). The ML cleaner trains on dev firms only. Intervals are paired bootstrap over documents within firms, so they capture sampling noise, not variation between firms.

## Repository layout

```
src/            generator, parser, cleaners, evaluation, data builders, UI sources and fonts
data/           dataset.zip (regenerate with src/build.py)
results/        results.json, extras.json, network.json, audit.json, demo.json, comparison table
public/         index.html, the page
vercel.json     static deploy config
```

## Reproduce

```bash
pip install -r requirements.txt
python src/build.py            # synthetic ledgers, messy exports, answer key  -> data/
python src/verify.py           # round-trip check of the answer key against every file
python src/run_cleaners.py     # four cleaners; ML trains on dev firms, cutoffs tuned on dev
python src/evaluate.py         # scores on dev / test / all -> results/results.json
python src/extras.py           # bootstrap intervals, threshold curves, cold-start replay, samples
python src/network_effect.py   # network-effect experiment (about 5 minutes; resumable per firm)
python src/audit.py            # trial-balance drill-down data
python src/demo_data.py        # console sample rows and label effects
python src/summarize.py        # results/cleaner_comparison.csv
python src/build_dashboard.py  # public/index.html
```

Everything is seeded; a full re-run reproduces the published numbers exactly. To score a real agent, emit `(file, sheet, row_number, kind_pred, pred_code, conf, date, net, flags)` per input row and point `evaluate.py` at it. Only `build_dashboard.py` is needed to rebuild the page from the committed `results/`.

## Deploy (Vercel)

1. Push this repository to GitHub.
2. In Vercel choose **Add New Project**, import the repository, and deploy. `vercel.json` sets the output directory to `public` and disables build and install commands.

## Design

White paper, black type, one vermilion accent. Square corners, hairline rules, upright type only. Archivo for display and text, IBM Plex Mono for tabular data, both embedded (SIL Open Font License 1.1).

## Limitations

- The injected errors are one author's model of messy data; real files will fail in other ways.
- Vendor names are drawn from shared pools, so cross-firm ML results are probably optimistic.
- Unbalanced-entry detection is near perfect partly because every synthetic entry started balanced.
- The four cleaners were designed while looking at all eight firms; only numeric cutoffs were re-tuned on dev.
- The network-effect experiment is leave-one-firm-out over all other firms and is separate from the dev and test split.
- The review-cost inputs are adjustable assumptions, not measurements.
