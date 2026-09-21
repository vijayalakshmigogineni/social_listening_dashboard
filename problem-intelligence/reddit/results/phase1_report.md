# Phase 1 — Manual Reality Check

**Question:** do public Reddit discussions contain enough genuine RCM/practice
operational problem evidence to justify building the next stage of the SLD?

**Sample:** 60 posts — 30 from r/CodingandBilling, 30 from r/MedicalCoding.
Collected 2026-09-20 via Apify (`trudax/reddit-scraper-lite`), reusing the
existing repository Apify credential. Every post in the recency window was
labelled. Nothing was filtered, and the boring ones were kept, because the
boring ones are the base rate.

---

## The five numbers

| Base rate | Count | % of 60 |
|---|---:|---:|
| Problem evidence | 22 | **36.7%** |
| Solution-seeking (L2+) | 11 | **18.3%** |
| Identifiable role | 34 | **56.7%** |
| Identifiable organisation | 1 | **1.7%** |
| Pain-management relevant | 1 | **1.7%** |

Against the roadmap's decision gates:

- Problem-evidence rate ≥ 10% → **PASS** (36.7%)
- L3+ rate ≥ 2% → **PASS** (3.3%, 2 posts)

Both gates clear, but the second clears on two posts. Treat 3.3% as
"not zero" rather than as a measured rate; the confidence interval on 2/60 is
wide enough that the honest statement is "L3 exists and is rare."

---

## What the numbers mean

**Problem evidence at 36.7% is a strong result.** Better than the roadmap's
10% floor by more than 3×, and well above the "if it is 3%, we rethink
sources" scenario. The evidence is also good evidence, not thin evidence: 20
of the 22 problem-evidence posts are first-person, and several name the payer,
the CPT codes and the duration of the problem. The richest example in the
sample:

> "For the past few months Healthy Blue North Carolina (Medicaid MCO) has been
> denying telehealth services as 'non-covered under the patient's plan' — the
> authorizations department doesn't seem to have any information + when I call
> the eligibili department they give me a nonsense answer about it being an
> auths issue."
> — r/CodingandBilling, [t3_1v9rx5n](https://www.reddit.com/r/CodingandBilling/comments/1v9rx5n/healthy_blue_nc_denying_gt_services/)

That single post carries payer, CPT codes (97153/97155/97156/97151), specialty,
geography, duration, and the fact that two payer channels have already failed.
That is the shape of signal Deliverable A needs.

**Identifiable role at 56.7% is higher than expected** and is the quiet good
news. Reddit users describe their jobs constantly and unprompted — "I've been
an ED coder for 11 years", "I have my CCS and have been an inpatient coder
since 2021", "I'm a newer chiropractor", "I work with claim denials for a
facility providing outpatient ABA services in NC". Role segmentation is
viable on this source without inference.

**Identifiable organisation at 1.7% confirms the roadmap's prediction exactly.**
The roadmap said "almost never"; one post in 60 is almost never. The single hit
is a coder naming their own employer in a post title
([t3_1vbro6x](https://www.reddit.com/r/CodingandBilling/comments/1vbro6x/i_am_a_medical_coder_in_india_i_have_recently/),
"I have recently joined access healthcare trivandrum") — an offshore RCM
vendor, not a prospect.

This is measured strictly: it counts only the organisation the **author** works
for. 24 of 60 posts name *some* organisation, but they are payers being fought
(BCBS, Healthy Blue NC), software being cursed (AdvancedMD, TheraNest, Kipu,
NYM), certifying bodies (AAPC, AHA) and prospective employers (CVS, Carle
Health, Cotiviti). Naming the payer you are fighting is not identifying
yourself. **Deliverable B cannot be built on this source.** That is now
measured rather than assumed.

**Pain-management relevance at 1.7% is the finding that should change a plan.**
One post in 60. It is a good one —

> "I'm a newer chiropractor trying to better understand claim construction and
> diagnosis pointers for personal injury cases … This gives me 13 diagnoses, but
> a CMS-1500 only allows 12 diagnosis codes."
> — r/CodingandBilling, [t3_1vc0fyk](https://www.reddit.com/r/CodingandBilling/comments/1vc0fyk/chiropractic_billing_question/)

— with cervical and lumbar radiculopathy, MVA personal injury, and 97140 manual
therapy. But it is one post, and it is chiropractic rather than interventional
pain medicine. A second post (RTM/CCM coverage verification) is plausibly
musculoskeletal but never says so, so it is labelled `unclear` rather than
counted.

At this rate, a pain-specific filter applied to these two subreddits yields
roughly **1 post per 60**. Volume planning for anything pain-specific has to
start from that number. The roadmap already anticipated this — "expect
specialty relevance to come from post text, not from the subreddit" — and the
data agrees. General RCM problem evidence is abundant; pain-management problem
evidence is not, in these two communities.

---

## Category and seeking-level distribution

**Problem categories** (only the 22 problem-evidence posts carry a category;
the other 38 are `None` by rule):

| Category | Count |
|---|---:|
| Coding & Documentation | 9 |
| Denials & Appeals | 4 |
| Technology & Workflow | 3 |
| Staffing & Capacity | 2 |
| Authorization & Pre-Certification | 1 |
| Reimbursement & Underpayment | 1 |
| Credentialing & Enrollment | 1 |
| Vendor / Outsourcing Dissatisfaction | 1 |
| AR & Collections | 0 |
| Other | 0 |
| None | 38 |

**Seeking levels** (assigned to all 60):

| Level | Count |
|---|---:|
| L0 — describing only | 4 |
| L1 — information/advice | 45 |
| L2 — actively seeking a solution | 9 |
| L3 — seeking a vendor/service | 2 |
| L4 — internal action e.g. hiring | 0 |

- **L2+: 11** (9 of which also carry problem evidence)
- **L3+: 2**
- **L4: 0**
- **Pain-management relevant: 1**
- **PainMed-PA service match: 1** (15 more `unclear` — real operational problems
  in a matched service area, but outside or unknown specialty)

Two observations worth carrying into Phase 2.

**The distribution is overwhelmingly L1.** 45 of 60 posts want a fact, a rule or
advice. This matches the roadmap's expectation ("usually L1–L2 rather than L3")
and it is the central constraint: this source is rich in *problems* and poor in
*purchase intent*. Note also that 2 of the 11 L2+ posts are L2 about a career
problem, not an operational one (an AAPC form blocking a certification, a
stalled job search) — restricted to posts that actually carry RCM problem
evidence, L2+ is **9/60 (15.0%)**.

**Both L3 posts are the same genre, and neither is in pain.** One is a
paramedical tattoo practitioner looking for a billing company —

> "the only companies(2 that I know of) that do this specific type of billing
> don't seem trustworthy and also get a very high percentage. Can anyone advise
> how to find a reputable person or company to do this?"
> — [t3_1v9gwor](https://www.reddit.com/r/CodingandBilling/comments/1v9gwor/medical_tattoo_billingcoding/)

— the other is someone offering to pay for one-on-one Kipu billing training
([t3_1w6pp7t](https://www.reddit.com/r/MedicalCoding/comments/1w6pp7t/residential_treatment_facility_billing/)).
The "can anyone recommend a billing company" genre the roadmap predicted does
appear. It is just rare, and in this sample it appears in behavioural health
and paramedical tattooing rather than pain.

---

## Sample of labelled records

Four records, chosen to show the range rather than the best of it.

**1. Strong first-person problem evidence, L2** — `t3_1v9rx5n`, r/CodingandBilling

| field | value |
|---|---|
| relevant_to_rcm | yes |
| problem_evidence | yes |
| first_person_problem | yes |
| problem_category | Denials & Appeals |
| seeking_level | L2 |
| identifiable_role | yes |
| identifiable_organization | no |
| pain_management_relevant | no |
| painmedpa_service_match | unclear |

Notes: payer named, codes named, duration given, escalation already exhausted.
Role explicit — "I work with claim denials for a facility providing outpatient
ABA services in NC." Facility itself never named.

**2. The one pain-relevant post, L2** — `t3_1vc0fyk`, r/CodingandBilling

| field | value |
|---|---|
| relevant_to_rcm | yes |
| problem_evidence | yes |
| first_person_problem | yes |
| problem_category | Coding & Documentation |
| seeking_level | L2 |
| identifiable_role | yes |
| identifiable_organization | no |
| pain_management_relevant | **yes** |
| painmedpa_service_match | **yes** |

Notes: hard operational constraint — 13 documented diagnoses against 12
CMS-1500 slots. Pain relevance rests on the text alone: cervical and lumbar
radiculopathy, neck/low back/shoulder pain, MVA personal injury.

**3. Relevant but NOT problem evidence, L1** — `t3_1vr3umd`, r/CodingandBilling

| field | value |
|---|---|
| relevant_to_rcm | yes |
| problem_evidence | **no** |
| first_person_problem | no |
| problem_category | None |
| seeking_level | L1 |
| identifiable_role | no |

Notes: the topic is denials, but the problem is not the author's — "I keep
hearing that CO-16 corrected claims eat a lot of time, and I'm trying to
understand why", addressed to "those of you who deal with these daily". Asks
for time-per-claim and tooling. This is discovery research, not operational
evidence. It is also one of a near-identical pair by the same author
(`t3_1vr3ncs`), posted minutes apart under different titles.

**4. Career domain, no RCM problem, L1** — `t3_1wh1a0j`, r/MedicalCoding

| field | value |
|---|---|
| relevant_to_rcm | **no** |
| problem_evidence | no |
| first_person_problem | no |
| problem_category | None |
| seeking_level | L1 |
| identifiable_role | yes |
| identifiable_organization | no |

Notes: deep RCM background — "CPC, multiple Epic revenue cycle certifications,
and nearly 9 years of experience in healthcare revenue cycle" — but the
difficulty is getting hired, not an operational problem. Employer type given
("a hospital system"), never named. This is the single largest category of
non-evidence in the sample.

---

## How the labels were decided

The distinction that drives everything is problem evidence vs. commentary vs.
career. Rules actually applied, recorded so a second labeller can reproduce
them (also documented in `labels_authored.py`):

- **`relevant_to_rcm`** — yes if the post concerns billing/coding/payer/
  credentialing/practice-operations *work*; no if it concerns the *labour
  market* around that work (exams, certification, job hunting, schooling, pay,
  career transitions). **26 of 60 posts are labour-market posts.** They are real
  and often distressing, but they are not operational RCM evidence, and folding
  them in would have roughly doubled the headline rate on false grounds.
- **`problem_evidence`** — requires `relevant_to_rcm = yes`, plus a concrete
  problem someone is actually experiencing. Excluded: industry commentary, pure
  knowledge questions with no blocker, self-promotion, and anticipatory worry.
  Two posts were excluded specifically on the anticipatory rule — a coder
  nervous about a future AI implementation at their facility (`t3_1w5k73w`) and
  a biller nervous about an upcoming RHC learning curve (`t3_1vcazum`). Nothing
  is failing in either.
- **`seeking_level`** — L1 wants a fact, rule or interpretation; L2 wants a
  method, tool, process or workaround for an ongoing problem; L3 wants a vendor
  or service. "Has anyone else seen this?" from someone with an unresolved
  operational problem was read as L2, since the corroboration is instrumental.
- **`identifiable_organization`** — the organisation the **author** works for or
  on behalf of. Third-party payers, vendors and prospective employers are
  recorded in `orgs_mentioned` but do not count. This is the business-relevant
  definition: Deliverable B needs to know *who is asking*, not who they are
  fighting.
- **`painmedpa_service_match`** — `yes` requires a first-person operational
  problem at a provider organisation, in a service area PainMed-PA plausibly
  sells, **and** `pain_management_relevant = yes`. `unclear` covers the same
  operational problem where specialty is unknown or outside pain — 15 posts.

No label was assigned from the subreddit, the author name or the score. Every
record's `notes` field carries the quote or the specific absence the label
rests on.

---

## Limitations and API notes

**Report these alongside the numbers; several affect how far they generalise.**

1. **r/CodingandBilling's window is stale.** Its 30 posts run 2026-07-29 →
   2026-08-17 — the newest is over a month before collection. This was checked
   twice: a wider listing run (53 unique posts) and an independent search-mode
   run with `time=week` both returned 2026-08-17 as the newest post. Whether
   the subreddit went quiet or Reddit's index for it stops there, the actor
   cannot see past it. r/MedicalCoding by contrast runs 2026-08-27 → 2026-09-19,
   current to the day before collection. **So this is "the 30 most recent
   *retrievable* posts", not "the 30 most recent posts."**
2. **The first pass came back short.** r/MedicalCoding returned 25 of 30 on the
   default 40-second scroll budget. A top-up run at 120 seconds brought the
   unique pool to 50; CodingandBilling's to 53. The final 60 are the newest 30
   per subreddit from those pools. All raw runs are retained.
3. **Five posts have empty bodies** — title-only. One (`t3_1ve4rub`, "THOUGHTS
   ON COTIVITI") is genuinely unlabelable beyond `relevant_to_rcm`; with no body
   there is no way to tell whether it is about working at Cotiviti or fighting
   their audits. It was not guessed at.
4. **One duplicated-content pair.** `t3_1vr3umd` and `t3_1vr3ncs` are
   substantially the same post by the same author under different titles,
   minutes apart. Distinct post IDs, so both are legitimately in the sample,
   but a production collector should dedup on near-identical text as well as on
   ID.
5. **One AutoModerator post** (`t3_1w40y68`, monthly discussion thread) is in
   the sample. Counted, not skipped — it is what a naive recency pull returns,
   and that is a finding for collector design.
6. **Comments were not collected.** The roadmap notes comments are often *more*
   valuable than posts, because that is where people describe their own
   situation. This 60-post base rate is a floor for what the source contains.
7. **Fields available.** Every post has id, url, permalink, title, body, author,
   created timestamp, score, upvote ratio and comment count — no missing fields
   except the five empty bodies. `upvote_ratio` was captured as a bonus. Note
   the actor gates score and comment count behind `includeMediaLinks: true`;
   without it those fields are absent.
8. **n = 60.** Every percentage here carries roughly ±6–12 points of sampling
   error. The 36.7% and 56.7% figures are robust to a few relabels; the 1.7%
   and 3.3% figures rest on one and two posts respectively and should be quoted
   as "roughly 1 in 60" rather than as percentages.
9. **Access route.** Collected via a third-party Apify scraper, not the Reddit
   Data API. The roadmap's week-1 action — apply for Data API access with an
   honest commercial use-case description, and confirm who signs off on source
   access — is **not** satisfied by this run and remains open. Reddit's terms
   also prohibit training models on user content without permission. Total
   Apify cost for all four runs: **$0.70**.

---

## What this supports

- **Deliverable A (problem intelligence): supported.** 36.7% problem evidence,
  20 of 22 first-person, 56.7% identifiable role. The signal exists and is
  richer than the roadmap's floor.
- **Deliverable B (lead generation): not supported by this source.** 1.7%
  author-identifiable organisations, and the one hit is an offshore RCM vendor.
  The roadmap's prediction is confirmed rather than merely assumed.
- **Pain-management specificity: the open risk.** 1 in 60. Anything
  pain-specific built on these two subreddits alone will be volume-starved.
  Deciding whether the product is *pain-management RCM intelligence* or
  *RCM intelligence generally* is now the question the data is asking, and it
  should be settled before Phase 2 freezes the taxonomy.

**Suggested next step, for a decision rather than for building:** before
expanding sources, establish whether pain-relevant volume improves in
communities where pain patients and clinicians actually post, or whether
specialty relevance simply has to be relaxed. That is a Phase 3 source-feasibility
question, and Phase 2 (freeze the taxonomy) should run first on the 22
problem-evidence posts already labelled here — the category distribution
already shows `AR & Collections` and `Other` never fired, which is exactly the
kind of thing Phase 2 exists to reconcile.

---

## Files

| File | Contents |
|---|---|
| `data/raw/reddit_60.json` | untouched Apify responses, all 4 runs, 136 items, run metadata and inputs |
| `data/reddit_60_posts.json` | normalised 60-post dataset, no labels |
| `data/labels/reddit_60_labels.json` | the 60 derived label records |
| `results/phase1_base_rates.json` | the numbers |
| `results/phase1_report.md` | this file |
| `fetch_reddit_60.py` | collector (refuses to overwrite without `--force`) |
| `topup_reddit.py` | top-up runs, appends without discarding |
| `build_dataset.py` | dedup + newest-30-per-subreddit selection |
| `labels_authored.py` | hand-authored labels and the labelling rules |
| `score_phase1.py` | validation + base-rate computation |

Reproduce with `python score_phase1.py`. It revalidates all 60 records against
the schema and the internal consistency rules before recomputing.
