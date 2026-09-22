# Social Listening Dashboard (SLD) — Research & Implementation Roadmap

**Owner:** Vishnu · **Company:** PainMed-PA · **Version:** 1.0 · **Date:** 2026-09-20

This document replaces all previous scope definitions. Read Part 0 and Part 9 first;
everything in between is reference material you consult when you reach that phase.

---

# PART 0 — THE BUSINESS PROBLEM, IN PLAIN LANGUAGE

## 0.1 What PainMed-PA actually needs

PainMed-PA sells RCM services to pain-management practices. To sell, it needs to know
two things:

1. **What is actually going wrong inside practices like our prospects?**
   Not what analysts say is going wrong. What the people doing the work complain about,
   in their own words, ranked by how often they say it.

2. **Who specifically is in enough pain to be looking for help right now?**

Today, PainMed-PA learns both of these one sales conversation at a time. The SLD is an
attempt to learn them from public evidence, at scale, before the sales conversation.

## 0.2 The single most important thing in this document

**These two goals have wildly different yield rates, and you must not let them be
measured by the same number.**

| | Deliverable A — Problem Intelligence | Deliverable B — Named Prospects |
|---|---|---|
| Question | What do practices struggle with, how often, and is it growing? | Which named practice is asking for help right now? |
| Evidence needed | A post describing a problem | A post describing a problem **+ identifiable org + role + active seeking** |
| Realistic volume | Hundreds of posts/month | **Single digits per month, at best** |
| Where it comes from | Reddit, forums (pseudonymous) | LinkedIn, job postings (identified) |
| Reliability | High. This will work. | Low volume by nature. Never guaranteed. |
| Business value | Service design, marketing copy, positioning, CEO situational awareness | Direct leads |

The trap: the CEO hears "social listening" and expects B. You build a system, it finds
four leads in a month, and the project is judged a failure — even if Deliverable A is
excellent and genuinely valuable.

**Set the expectation before you build.** The primary deliverable is A. B is a
low-volume by-product that rides on the same pipeline for nearly zero extra cost. Say
this out loud in your first status update. Write it on the first slide of the dashboard.

There is a structural reason for the low yield: **the people with the best problem
evidence post anonymously, and the people with identifiable names post marketing.**
That tension is the central design constraint of this entire project. Every source
decision below flows from it.

## 0.3 What we already know from our own data (2026-09-20)

We analysed the existing 95-post LinkedIn sample in `linkedin/data/raw/`:

```
first-person practice framing ("our practice", "our billing team") :  0 / 95
solution-seeking language                                          :  2 / 95  (both thought-leadership)
pain/overload language                                             :  2 / 95
vendor self-promotion                                              :  5 / 95
author role: exec/founder 21 · RCM-vendor/billing pro 11 · manager 5 · clinician 4 · consultant 2 · unclear 52
```

**Zero percent primary-scope yield.** The existing hand-labels agree: nearly every post
is commentary on CMS-0057-F or the UHC prior-auth reduction — i.e. *Phase 2 material,
collected perfectly, for the wrong scope.*

Two competing explanations, and Phase 3 must distinguish them:

- **H1 (query problem):** we searched payer names + "prior authorization" + "denial".
  Those queries select for policy commentary by construction. Different queries
  ("our billing team", "looking for a billing company") might find real practice voices.
- **H2 (platform problem):** LinkedIn's public feed structurally rewards broadcast
  content. Practices do not publicly admit operational failure under their real name
  next to their employer.

My prior is roughly 70/30 in favour of H2, but H1 is cheap to test and must be tested
before we write LinkedIn off. See Phase 3, Test 3.

Also note a data-quality bug to fix on reuse: `authorHeadline` contains follower counts
("997 followers") for ~half the records, so role inference from that field is unreliable
as collected.

## 0.4 The pipeline

Everything below is one pipeline. Memorise this ladder — it is the spine of the data
model, the dashboard, and the evaluation.

```
                    RAW DOCUMENT          everything we fetched
                         |                  (thousands)
                         |  Gate A: domain relevance
                         v
                  RELEVANT DOCUMENT       mentions RCM/billing subject matter
                         |                  (hundreds)
                         |  Gate B+C: experienced, first-person, problem framing
                         v
                   PROBLEM EVIDENCE       someone is describing a real operational problem
                         |                  (dozens)     <-- Deliverable A lives here
                         |
            +------------+------------+
            |                         |
            |  aggregate              |  enrich with role/org/intent
            v                         v
     PROBLEM CLUSTER            PROSPECT CANDIDATE
     (category x payer x        (org + role + seeking >= L2)
      procedure x window)         (a handful)   <-- Deliverable B lives here
            |                         |
            |  passes evidence        |  passes evidence
            |  thresholds             |  thresholds
            v                         v
      OPPORTUNITY  <--- the only things on the CEO dashboard --->  REVIEW QUEUE
```

Three words that must never be used interchangeably:

- **Information found** — a document exists. Says nothing about value.
- **Problem evidence** — a specific person describes a specific operational difficulty.
- **Opportunity** — a *pattern* of problem evidence that clears explicit thresholds.

A single post is never an opportunity. An opportunity is always an aggregate with a
checklist attached.

---

# PART 1 — SOURCE RESEARCH

## 1.1 How to judge a source

Score every candidate on four axes. These four axes determine everything:

| Axis | Question | Why it decides things |
|---|---|---|
| **Authenticity** | Do people describe problems in first person, unguardedly? | No authenticity → no problem evidence → Deliverable A fails |
| **Identity** | Can we tie a post to a named organisation? | No identity → no prospects → Deliverable B impossible |
| **Accessibility** | Official API, clean ToS, historical data? | No access → nothing else matters |
| **Density** | What fraction of the source is on-topic? | Low density → you drown in noise |

**Authenticity and Identity are inversely correlated across every platform.** That is
the whole game.

## 1.2 Source-by-source assessment

### Reddit — **PRIMARY. Best problem evidence available anywhere.**

- **Who uses it:** medical billers, coders, AR specialists, prior-auth coordinators,
  practice managers, some practice owners, some physicians. Overwhelmingly *staff*, not
  owners.
- **Problems that appear:** exactly ours. Denials by payer and code, prior-auth
  workflow, clearinghouse breakage, AR backlog, credentialing delays, "our office is
  drowning", "how do you all handle X", "is our billing company ripping us off". The
  single richest vein of unguarded operational complaint on the public internet.
- **Relevant communities (verify each is active before committing):** `r/CodingandBilling`,
  `r/MedicalCoding`, `r/Medicalbillingandcoding`, `r/healthIT`, `r/medicine`,
  `r/FamilyMedicine`, `r/physicianassistant`. Pain-specific communities are small; expect
  specialty relevance to come from post text, not from the subreddit.
- **Org identifiable:** **Almost never.** Pseudonymous by design. Occasionally a user
  self-describes ("I manage a 4-provider pain clinic in Ohio") — that is specialty and
  size evidence, but not an identity.
- **Solution-seeking:** Yes, constantly, but usually L1–L2 (advice, tools) rather than
  L3 (vendor). L3 does appear: "can anyone recommend a billing company for a small
  practice" is a recurring genre.
- **Fields available:** id, permalink, subreddit, title, selftext, created_utc, score,
  num_comments, upvote_ratio, author (pseudonym), flair, full comment trees. Comments
  are often *more* valuable than posts — that is where people describe their own
  situation in reply to someone else's question.
- **Historical:** Yes, via listing endpoints and search, subject to depth caps. Pushshift
  is no longer generally available; plan for forward collection from day one and treat
  backfill as a bonus.
- **Trends:** Yes — good timestamps, stable community population, reasonable volume.
- **Access — read this carefully:** The Reddit Data API requires OAuth and is free for
  **non-commercial** use at ~100 queries/min. **Commercial use requires a separate,
  manually-reviewed agreement** (reported around $0.24/1,000 calls, 2–4 week review), and
  the terms **prohibit training ML/AI models on user content without rightsholder
  permission**. PainMed-PA is a commercial entity, so do not assume the free tier covers
  you. **Action: apply for Data API access in week 1 with an honest use-case description
  (internal market research, no redistribution, no model training).** In the meantime,
  reading public Reddit pages in a browser is ordinary web browsing and is fine for
  building your labelled dataset by hand.
- **Verdict:** Primary source for Deliverable A. Effectively useless for Deliverable B.
- **Test first:** whether `r/CodingandBilling` + `r/MedicalCoding` produce ≥20 clear
  problem-evidence posts per week, and what fraction carry pain-management specificity.

### Public billing/coding forums (AAPC Discussions, AHIMA, specialty forums) — **SECONDARY.**

- **Who uses it:** certified coders and billers; AAPC reports 300k+ members. More senior
  and more credentialed than Reddit; some practice managers.
- **Problems:** narrow and deep — code-level denial problems, modifier disputes, payer
  policy interpretation. Excellent for the *Documentation* and *Denials* categories,
  weaker for staffing and capacity.
- **Identity:** usernames, sometimes real names and employer in a signature. Slightly
  better than Reddit, still mostly not org-attributable.
- **Fields:** thread title, body, author handle, date, reply count, forum category.
- **Access:** publicly readable and search-indexed, but **no official API**. Would
  require polite, rate-limited fetching of public pages, and you must check `robots.txt`
  and the site terms first. Treat as "needs a written access decision" rather than
  "approved".
- **Verdict:** good second source for corroboration and source-diversity (which your
  opportunity rule requires). Add in Phase 3, not day one.

### LinkedIn — **DEFER. Do not automate yet.**

- **Reality check:** 0/95 primary-scope yield in our own sample (see 0.3).
- **Who uses it:** vendors, consultants, executives, analysts. The RCM corner of
  LinkedIn is a marketing channel, not a support channel.
- **Identity:** the best of any source — name, headline, company, profile URL. This is
  the *only* reason to keep pursuing it.
- **Access:** LinkedIn's User Agreement prohibits automated scraping. Apify and similar
  tools are technical workarounds, **not a permission grant**. Our existing Apify tests
  were valid feasibility experiments; they are not a production decision. Using them at
  commercial scale needs explicit written sign-off from whoever owns legal risk at
  PainMed-PA. Do not make that decision yourself.
- **Verdict:** **manual collection only** for the MVP — a human runs searches and pastes
  results into a sheet. Cap it at ~50–100 posts, used purely as hard-negative and
  identity-positive examples in the gold set. Revisit automation only if Phase 3 Test 3
  falsifies H2.
- **Test first (Test 3):** run 10 *intent-shaped* searches by hand — "our billing team",
  "looking for a billing company", "we're hiring a biller", "our denials", "outsource our
  billing", "our AR is". If ≥5 genuine practice-voice posts appear, H1 wins and LinkedIn
  is worth a proper access conversation. If ≤1, H2 wins and LinkedIn becomes a
  Phase-2-only source.

### Job postings — **PRIMARY for Deliverable B. Most underrated source in this project.**

This is the recommendation I would most like you to take seriously.

A public job posting reading *"Pain Management Clinic seeking Prior Authorization
Coordinator — high volume, 3 providers"* is, structurally, the strongest public prospect
signal that exists:

- It names an **identifiable organisation** (unlike Reddit).
- It is **objective evidence of operational burden** — you do not hire an AR specialist
  because things are going well. No self-reporting bias, no venting, no rhetoric.
- It is **dated, structured, and repeatable**.
- It is **published for public consumption by design** — the cleanest consent posture of
  any source here.
- Role titles map directly onto our problem categories: "prior authorization coordinator"
  → Authorization; "AR follow-up specialist" / "denials specialist" → Denials;
  "credentialing specialist" → Credentialing; "billing manager" → Capacity.

- **Fields:** title, company, location, description, posted date, salary range, category.
- **Trends:** excellent — hiring volume by role title over time is a clean leading
  indicator of where operational strain is concentrated.
- **Access:** Indeed and LinkedIn Jobs are ToS-restricted. **Adzuna** publishes a
  documented self-serve API with a genuinely free tier (~1,000 calls/month) and is the
  right thing to test first. **USAJOBS** has a free API but is federal-only (VA pain
  clinics only — narrow but real). Practice career pages and public ATS boards
  (Greenhouse/Lever/Workable JSON endpoints) are legitimate but fragmented and skew large.
- **Known risk:** **coverage of small independent pain practices may be poor.**
  Aggregators index large employers well and 4-provider clinics badly. This is the one
  thing that could kill the source, so test it explicitly and early.
- **Test first:** Adzuna, search `"prior authorization" OR "medical billing" OR "revenue
  cycle"` filtered to healthcare, 100 postings. Then hand-count: how many are *practices*
  (not hospitals, not staffing agencies, not billing vendors)? If <10%, the source fails
  and you drop it — cleanly, in one afternoon.

### X / Twitter — **DROP for Phase 1.**

Healthcare RCM conversation there is thin, fragmented, and dominated by patient
complaints about their own insurance — a different problem from practice operations.
Post-2023 API pricing is high relative to expected yield. Your existing `x_twitter` test
output is a valid feasibility artefact; park it. Revisit only if another source fails.

### YouTube — **DROP for Phase 1.**

Content is instructional (how-to-bill tutorials), not complaint. The *comment sections*
of billing-tutorial videos do contain real practitioner questions and are a genuine
second-order source via the official Data API — but transcript and comment processing is
a whole extra pipeline. Note it as a Phase 3+ candidate and move on.

### Healthcare trade press (Becker's, Physicians Practice, MGMA, RevCycleIntelligence) — **SECONDARY, Phase 2 role.**

Not problem evidence — it is *context*. A Becker's article does not tell you a practice
has a problem; it tells you an industry-level change happened. Exactly the Phase 2 role.
You already have `test_beckers_rss.py` working; RSS is clean and low-cost. Keep it
collecting quietly in the background so you accumulate history, but keep it out of the
Phase 1 problem pipeline.

### Facebook / private groups — **EXCLUDED.**

The richest practice-manager communities on the internet are closed Facebook groups.
They are behind access controls. **Do not join under false pretences, do not use personal
accounts to extract data, do not scrape.** Out of scope, permanently — and state that
explicitly in your write-up so nobody assumes it was an oversight.

### Payer sites, CMS, Federal Register — **PHASE 2. Already built. Freeze.**

Your UHC / Cigna / Aetna / Humana / CMS / Noridian / Novitas / Federal Register work is
genuinely good and is the backbone of Phase 2. It answers "what changed", not "who is
struggling". Stop extending it. Do not delete it.

## 1.3 Summary table

| Source | Authenticity | Identity | Access | Density | Verdict |
|---|---|---|---|---|---|
| Reddit | **High** | None | API, commercial terms needed | Med-High | **MVP primary** |
| Job postings (Adzuna) | **High (objective)** | **High** | Free API tier | Med | **MVP primary (test coverage)** |
| Billing forums (AAPC etc.) | High | Low | Public, no API, needs decision | High | MVP secondary |
| LinkedIn | **Very low (measured)** | **High** | ToS-restricted | Low | **Manual only, ≤100 posts** |
| Trade press RSS | N/A (context) | N/A | RSS, clean | High | Phase 2, keep collecting |
| X / Twitter | Low | Low | Paid API | Low | Drop |
| YouTube comments | Med | Low | Official API | Low | Phase 3+ |
| Facebook groups | Very high | Med | **Access-controlled** | High | **Excluded — do not attempt** |
| Payer / CMS / FedReg | N/A (context) | N/A | Working already | High | **Phase 2 — freeze** |

## 1.4 The MVP source set — exactly three, plus one manual

1. **Reddit** — 3 subreddits, automated. *Deliverable A engine.*
2. **Adzuna job postings** — one feasibility test, then keep or drop. *Deliverable B engine.*
3. **One public billing forum** — added in Phase 3 only if Reddit alone fails the
   source-diversity requirement in the opportunity rule.
4. **LinkedIn, manual, ≤100 posts** — gold-set material and hard negatives. No automation.

Three sources is deliberately, almost uncomfortably small. It is correct. You cannot
debug relevance rules across ten sources at once, and every source you add multiplies the
labelling work.

## 1.5 The UHC lesson, generalised

Your UHC finding — that one payer publishes across Medical Policies, Reimbursement
Policies, Network News, PA resources, and monthly bulletins, so **one payer ≠ one URL** —
is correct and important. Its general form applies to Phase 1 too:

> **One source ≠ one endpoint. A "source" is a register of channels, each with its own
> access method, update cadence, and content type.**

So Reddit is not one source; it is N subreddits × (posts, comments) × (new, top, search).
Maintain a `sources.yaml` **source register** from day one: one row per *channel*, with
its access method, legal basis, cadence, last successful fetch, and owner. This single
file prevents the UHC class of error from recurring.

---

# PART 2 — DEFINING A "USEFUL PROBLEM DISCUSSION" (V1, RULE-BASED)

You were right to want rules before an LLM. Rules are inspectable, free, deterministic,
give you a baseline to beat, and — given Reddit's no-model-training term — keep you out
of a licensing question entirely. Build the rules. Measure them. *Then* decide whether an
LLM is worth it.

## 2.1 Three gates and an exclusion list

A document becomes **problem evidence** only if it passes A **and** B **and** C and trips
no hard exclusion.

**Gate A — Domain relevance.** Text contains ≥1 term from the RCM lexicon.

> prior auth(orization), preauth, precert, denial/denied, claim, CPT, modifier, ICD,
> A/R, aging, clearinghouse, EOB, ERA, remit, appeal, credentialing, enrollment, NPI,
> LCD/NCD, medical necessity, underpayment, takeback, recoupment, fee schedule,
> eligibility, copay, deductible, RVU, superbill, coding, biller, revenue cycle, RCM

Purpose: cheap, high-recall filter. Miss nothing; precision comes later.

**Gate B — Experienced, not discussed.** This is the gate that does the real work.
Text contains ≥1 **first-person operational marker**:

> our practice / our clinic / our office / our billing (team|dept) / our staff /
> our providers / my practice / my office / I'm the (biller|coder|manager|owner) /
> we're a X-provider / at our clinic / we bill / we submit / we're hiring

**OR** ≥1 **peer-directed question marker**:

> how do (you|others|other practices) handle / has anyone / does anyone /
> anyone else (seeing|getting|having) / what are you (all )?doing about /
> am I the only one

Purpose: separates *"a practice is living this"* from *"a consultant is writing about
this."* This one gate is the difference between your current 0% yield and a working
system.

**Gate C — Problem or seeking.** Text contains ≥1 **pain marker**:

> struggl\*, can't keep up, backlog, drowning, spending (hours|all day), overwhelm\*,
> nightmare, behind on, falling behind, short-staffed, burnt/burned out, keeps getting
> denied, huge increase in, through the roof, no idea why, stuck, sitting in A/R,
> taking (weeks|months), constantly

**OR** ≥1 **seeking marker**:

> looking for, recommend\*, suggestions for, anyone use/using, best (company|vendor|
> service|software) for, worth outsourcing, should we outsource, evaluating,
> we're hiring, thinking of switching

**Hard exclusions — reject regardless of A/B/C:**

| Exclusion | Pattern | Why |
|---|---|---|
| Vendor self-promo | "we provide/offer/specialize", "our solution/platform", "book a demo", "DM me", "link in bio", "contact us" | Supply side, not demand side |
| News share | URL-dominant, <150 chars of own text, no first-person | Information, not problem |
| Definitional | "what is", "what does X mean", "can someone explain" with no first-person | Education, not pain |
| Patient-side | "my insurance", "my claim", "my doctor", "my surgery" without a staff/practice role | Different person, different problem — **and may contain personal health info; exclude and do not retain** |
| Student / career | "studying for CPC", "first job", "salary", "which certification" | Career, not operations |
| Contentless | <40 chars of substantive text | Nothing to classify |

## 2.2 Output of the relevance stage

```
relevance ∈ { irrelevant, context_only, problem_evidence }
```

- `irrelevant` — fails Gate A, or trips a hard exclusion.
- `context_only` — passes A, fails B or C. Real subject matter, nobody experiencing it.
  *(This is where ~95% of your current LinkedIn corpus lands. It is not waste — it feeds
  Phase 2.)*
- `problem_evidence` — passes A, B, and C.

Always store **`rule_hits`**: which patterns fired, with the matched span. Non-negotiable.
It is how you debug false positives, and it is what the dashboard shows the CEO when he
asks "why is this on my screen."

## 2.3 The rules applied to your own examples

| Post | A | B | C | Excl | Result |
|---|---|---|---|---|---|
| "Our practice is spending way too much time chasing prior authorizations." | ✓ prior auth | ✓ our practice | ✓ spending too much time | — | **problem_evidence** |
| "Does anyone know a good solution for managing medical billing for a pain practice?" | ✓ billing | ✓ does anyone | ✓ solution/seeking | — | **problem_evidence** |
| "We're seeing a huge increase in claim denials and can't figure out why." | ✓ denials | ✓ we're seeing | ✓ huge increase | — | **problem_evidence** |
| "Looking for an RCM company that specializes in pain management." | ✓ RCM | ✗ *(no first-person marker)* | ✓ looking for | — | **rule gap → see below** |
| "Our billing staff can't keep up since we added two providers." | ✓ billing | ✓ our billing staff | ✓ can't keep up | — | **problem_evidence** |
| "How are other practices handling appeals and denied claims?" | ✓ appeals | ✓ how are other practices | ✓ seeking | — | **problem_evidence** |
| "We are hiring another medical biller because our team can't keep up." | ✓ biller | ✓ we are hiring | ✓ can't keep up | — | **problem_evidence** |
| "UHC released a new policy." | ✓ policy | ✗ | ✗ | — | **context_only** |
| "What is prior authorization?" | ✓ | ✗ | ✗ | definitional | **irrelevant** |
| "Here is an article about medical billing." | ✓ | ✗ | ✗ | news share | **irrelevant** |
| "Our company provides RCM services." | ✓ | ✓ *(our company)* | ✗ | **vendor self-promo** | **irrelevant** |
| "Insurance is terrible." | ✗ | ✗ | ✓ | — | **irrelevant** (fails Gate A) |

Your example 4 correctly exposes a rule gap on the first pass. Fix: **a strong
service-seeking marker (L3) satisfies Gate B on its own** — "looking for an RCM company"
is self-evidently a practice speaking, even without the word "our". Add that as an
explicit documented exception rather than loosening Gate B generally.

This is exactly how you should work: run the rules against hand-labelled examples, find
the disagreement, make one narrow documented amendment. Never a vague global loosening.

## 2.4 What NOT to build in the relevance stage

- No LLM, no embeddings, no fine-tuning, no sentiment model.
- No confidence scores. A gate either fired or it did not.
- No fuzzy matching or stemming beyond simple prefix wildcards.
- No per-source rule variants. One rulebook, all sources, until proven inadequate.

---

# PART 3 — PROBLEM TAXONOMY

## 3.1 The categories

Your original six were designed for *payer policy* analysis. They are correct for that,
and you should keep them so prior work maps forward — but they structurally cannot
express half of what a struggling practice complains about. Nothing in the original six
can hold *"we can't hire a biller"* or *"our credentialing has been stuck for four
months"*, and those are among the most common real complaints.

Keep the six, add five. Multi-label — a post can be in several.

| # | Category | Example trigger | Status |
|---|---|---|---|
| 1 | Authorization / Utilization Management | prior auth, peer-to-peer, gold card | existing |
| 2 | Denials / Claims Friction | denied, CARC/RARC, rejection, resubmit | existing |
| 3 | Coverage / Policy | not covered, LCD/NCD, plan policy | existing |
| 4 | Documentation / Medical Necessity | notes, medical necessity, chart | existing |
| 5 | Reimbursement / Payment | underpaid, fee schedule, takeback, conversion factor | existing |
| 6 | Procedure / Device Access | RFA, SCS, ESI, kyphoplasty availability | existing |
| 7 | **Credentialing / Payer Enrollment** | credentialing, CAQH, enrollment, roster, NPI | **new** |
| 8 | **Staffing / Capacity** | can't keep up, hiring, turnover, short-staffed | **new** |
| 9 | **Technology / Workflow** | EHR, PM system, clearinghouse, integration, portal | **new** |
| 10 | **Patient Access & Collections** | eligibility, patient balance, statements, copay collection | **new** |
| 11 | **Vendor / Outsourcing Dissatisfaction** | our billing company, switching vendors, they're not working our AR | **new — highest commercial value** |

**Category 11 is the one to watch.** A practice publicly unhappy with its current billing
vendor is the closest thing to a qualified lead that exists in public data. Track it
separately and route every instance to human review regardless of other criteria.

Also carry a `specialty_relevance` flag — pain / ortho / neuro / spine / PM&R / ASC /
anesthesia — derived from text, not from source. A generic denials complaint from a
dermatology office is weaker evidence for PainMed-PA than the same complaint from a pain
clinic, and the dashboard must be able to separate them.

## 3.2 Method

Keyword → category mapping, multi-label, exactly as `process_linkedin.py` already does.
**Refactor the dictionaries out of the Python and into `config/lexicons.yaml`.** They
will change weekly, and they must be editable by a non-programmer without touching code.
This is the single most valuable refactor of your existing work.

## 3.3 What NOT to build

- No topic modelling (LDA / BERTopic). You have a domain taxonomy; discovery is not the
  problem.
- No hierarchy or sub-categories yet. Flat 11. Add depth only when a category exceeds
  ~30% of volume and becomes uninformative.

---

# PART 4 — ROLE, ORGANISATION, AND THE PROSPECT LADDER

## 4.1 Author role — evidence only, never inference

```
author_type ∈ { unknown, patient, clinician, practice_owner, practice_admin,
                billing_staff, rcm_vendor, consultant, media, student }
```

Assign **only** from explicit evidence, and record which:

- `self_stated` — the post says it ("I'm the billing manager at a 3-doc pain clinic")
- `profile` — public bio / flair / headline states it
- `none` → `author_type = unknown`

**Never infer role from topic.** Someone discussing prior auth is not thereby a biller.
Getting this wrong is how you end up with a prospect list full of consultants — precisely
the failure mode visible in the current LinkedIn corpus.

Default to `unknown` aggressively. `unknown` is a perfectly good answer for Deliverable A:
you do not need to know who someone is to count that a problem was described.

## 4.2 Organisation identification

```
org_identifiable ∈ { yes, no }
org_name         : string | null
org_evidence     : verbatim quote or profile URL that establishes it
```

Requires a **verifiable artefact** — a profile employer field, a named practice in the
text, a company URL. Expect `no` for essentially all Reddit content and `yes` for
essentially all job postings. Do not guess from geography, writing style, or anything else.

## 4.3 Solution-seeking ladder

| Level | Name | Evidence | Example |
|---|---|---|---|
| L0 | None | describes a problem, no ask | "Our denials are up this quarter." |
| L1 | Information-seeking | wants to understand | "How do other practices handle appeals?" |
| L2 | Solution-seeking | wants a better way | "Is there a better way to manage prior auths?" |
| L3 | Service / vendor-seeking | wants a provider | "Looking for an RCM company for a pain practice." |
| L4 | Active capacity / procurement | committing resources | "We're hiring another biller." / "We're evaluating vendors." |

L4 is not "further along" than L3 — it is a *different* signal. L3 is explicit demand.
L4 is revealed demand: hiring is a practice solving the problem in-house, which is both
proof of burden and evidence they have not chosen outsourcing. Both are interesting; they
mean different things to a salesperson, so keep them distinct rather than ordering them.

## 4.4 Prospect tiers — descriptive, never predictive

| Tier | Requires | Meaning | Dashboard |
|---|---|---|---|
| T0 | — | not relevant | no |
| T1 | relevance = context_only | industry context | Phase 2 only |
| T2 | problem_evidence | **a problem was described** | **counts toward clusters** |
| T3 | T2 + author_type ∈ {owner, admin, billing_staff, clinician} | a relevant person described it | counts, weighted |
| T4 | T3 + seeking ≥ L2 | a relevant person wants a fix | **review queue** |
| T5 | T4 + org_identifiable = yes + (seeking L3/L4 **or** category 11) | identified org actively seeking | **review queue, top** |

Read the tier names literally. **T5 does not mean "prospect."** It means *"a human should
spend five minutes looking at this."* That is the entire claim, and it is the only claim
the evidence supports. Name the dashboard panel **"Review Queue"**, never "Leads" — the
label alone will prevent a year of misunderstanding.

## 4.5 Avoiding false positives

Five concrete mechanisms:

1. **Require conjunctive evidence, never a score.** T5 needs *all four* facts present. No
   weighted sum, because a sum lets three weak signals manufacture a strong conclusion.
2. **Default `unknown`.** Missing evidence caps the tier. It never averages out.
3. **Exclude the supply side first.** Run vendor / consultant exclusion *before* tiering.
   In RCM social media the supply side outnumbers the demand side by a wide margin;
   missing this is the #1 false-positive source. 5/95 of your LinkedIn posts were overt
   self-promotion and many more were soft-promotional.
4. **Separate patient voice hard.** "I hate prior authorization" from a patient is T0,
   full stop. It fails Gate A/B, and patient posts may contain personal health
   information — exclude and do not retain.
5. **Human sign-off is mandatory on T5.** No automated output ever leaves the system as a
   lead. Log the human decision (`accepted` / `rejected` + reason) — that log becomes your
   precision measurement for free.

**Worked contrast, from your brief:**

| | "I hate prior authorization" | "Our billing team is struggling with prior auth and we're looking for outside help" |
|---|---|---|
| Gate A | ✓ | ✓ |
| Gate B | ✗ no first-person operational marker | ✓ "our billing team" |
| Gate C | weak | ✓ "struggling" + "looking for" |
| author_type | unknown | billing / admin (self-stated) |
| seeking | L0 | **L3** |
| org | no | depends on source |
| **Tier** | **T0** | **T4, or T5 if org identifiable** |

---

# PART 5 — CLUSTERS, TRENDS, AND OPPORTUNITIES

## 5.1 Cluster definition

```
cluster_key = (problem_category, payer|null, procedure|null, specialty_relevance)
window      = rolling 90 days
```

Start there. Do not cluster by text similarity or embeddings — the taxonomy is your
clustering, and it is interpretable, which embeddings are not.

## 5.2 Metrics, and why each one exists

| Metric | Why it matters |
|---|---|
| `n_posts` | raw volume. **Weakest metric — easiest to fake, easiest to misread.** |
| `n_unique_authors` | **the important one.** Guards against one loud person or one long thread creating a phantom trend. |
| `n_unique_orgs` | how many distinct organisations. Near 0 on Reddit; meaningful on job postings. |
| `n_sources` / `n_communities` | corroboration. A problem seen in one subreddit may be a community quirk; seen in three places it is an industry pattern. |
| `share_of_relevant` | **`n_posts ÷ total problem_evidence in window`.** See 5.3 — the metric that keeps you honest. |
| `current vs previous window` | direction. Use 45/45 or 90/90. |
| `pct_change` | magnitude — **only reported above a volume floor.** |
| `first_seen` / `last_seen` | is this new, or chronic-and-ongoing? Different business responses. |
| `n_seeking_L2plus` | how much of this volume is people *wanting a fix* vs. venting. Converts a topic into a market. |
| `median_engagement` | resonance. **Never compare across platforms** — a Reddit score and a LinkedIn like are different units. Within-source only. |

## 5.3 The trend trap you will otherwise fall into

**If your collection volume changes, every raw count changes, and none of it means
anything.** You add a subreddit in week 3 → every category "rises" 40%. Your Reddit token
expires for two days → everything "falls".

Three defences, all mandatory:

1. **Always report `share_of_relevant` alongside raw counts.** A category rising from 10%
   to 18% of all problem evidence is a real finding. A category going from 20 to 36 posts
   while your corpus doubled is not.
2. **Volume floor before percentages.** Never display a % change on a base below ~5 posts.
   "+300%" on 1→4 is noise rendered as a headline.
3. **Log collection health per channel per day** — `docs_fetched`, `docs_relevant`,
   `fetch_errors`. Without this you cannot distinguish "problem went away" from "scraper
   broke", and you will hit that exact ambiguity within the first month.

## 5.4 Opportunity rule V1 — a checklist, not a score

An **Opportunity** is a cluster meeting **all** of:

```
[ ] Volume          : >= 5 problem_evidence documents in the 90-day window
[ ] Distinct voices : >= 4 unique authors
[ ] Corroboration   : >= 2 distinct communities/channels
[ ] Demand          : >= 1 document at seeking level L2 or above
[ ] Relevance       : specialty_relevance = pain-adjacent for >= 1 document,
                      OR the category is universal to small practices (2, 5, 7, 8, 11)
[ ] Recency         : >= 1 document in the last 30 days
```

**Display the checklist itself.** A card reading `6/6 criteria met`, with each line ticked
and every claim hyperlinked to its source post, is dramatically more defensible than
`Opportunity Score: 78%`. The CEO can audit it. You can explain it. Nobody has to trust a
number nobody can derive.

**Ranking** (needed, because you will have more cards than screen): sort by
`n_unique_authors` desc, then `n_seeking_L2plus` desc, then recency. State the sort order
on the screen. It is a sort, not a score.

**Never invent confidence percentages.** You have no calibration data, so any percentage
is decoration implying rigour you have not earned. If you later build a labelled
evaluation set large enough to calibrate, revisit.

## 5.5 When does something reach the dashboard?

```
Raw document      → never shown
Relevant document → counts only, in Source Health
Problem evidence  → shown in Evidence drill-down, never on the front page
Problem cluster   → shown in Problem Landscape (the main screen)
Opportunity       → shown as a card (cluster + full checklist passed)
T4/T5 document    → shown in Review Queue
```

**The front page shows clusters and opportunities. Never individual posts.** Individual
posts are always one click down, as evidence for an aggregate claim. This is the
structural answer to your "don't overuse signals" concern: a post can never promote
itself to the front page.

---

# PART 6 — DATA MODEL

## 6.1 Three tables, not one

This is the most important engineering decision in the document.

```
documents      immutable. one row per fetched item. never modified after insert.
annotations    one row per (document, pipeline_version). all derived fields.
clusters       recomputed from scratch on every run. never hand-edited.
```

**Why separate.** You will re-run classification twenty or thirty times as the rules
evolve. If derived fields live in the same row as raw data, every re-run destroys your raw
data, you cannot reproduce last week's numbers, and you cannot compare rule v3 to rule v4.
Your current `classified_rows_*.json` files mix the two and are therefore single-use
artefacts. Splitting them is the main structural upgrade to your existing work.

## 6.2 `documents` — raw and immutable

| Field | Req | Note |
|---|---|---|
| `doc_id` | **yes** | `{source}:{source_id}` |
| `source` | **yes** | reddit / adzuna / linkedin_manual |
| `channel` | **yes** | subreddit, forum board, query name. The UHC lesson. |
| `source_id` | **yes** | native id, for dedup |
| `url` | **yes** | provenance. Every dashboard claim links back to this. |
| `published_at` | **yes** | UTC. Everything time-based dies without it. |
| `fetched_at` | **yes** | distinguishes "no posts" from "no fetch" |
| `text` | **yes** | full text. Title + body concatenated for Reddit. |
| `title` | opt | null for comments |
| `author_handle` | strong | needed for `n_unique_authors` |
| `author_profile_url` | opt | needed for role evidence |
| `parent_id` | opt | comment threading |
| `engagement` | opt | JSON blob, source-specific. Do not normalise across sources. |
| `raw` | **yes** | full original JSON. Cheap now, irreplaceable later. |
| `lang` | opt | filter non-English early |

## 6.3 `annotations` — derived, versioned

| Field | Req | Note |
|---|---|---|
| `doc_id`, `pipeline_version` | **yes** | composite key |
| `relevance` | **yes** | irrelevant / context_only / problem_evidence |
| `problem_categories[]` | **yes** | multi-label, from the 11 |
| `rule_hits[]` | **yes** | **which patterns fired + matched span.** Non-negotiable. |
| `problem_evidence_quote` | **yes for T2+** | **verbatim span, not a paraphrase** |
| `payer`, `procedure` | opt | null is fine and common |
| `specialty_relevance` | opt | pain / ortho / other / unknown |
| `author_type`, `author_type_evidence` | **yes** | default `unknown` |
| `org_identifiable`, `org_name`, `org_evidence` | **yes** | default `no` |
| `seeking_level` | **yes** | L0–L4 |
| `tier` | **yes** | T0–T5, derived |
| `human_review` | opt | pending / accepted / rejected + reason. Your precision metric. |

## 6.4 `clusters` — derived, recomputed

`cluster_key`, `window_start` / `window_end`, all Part 5.2 metrics, `criteria_met` (the
six booleans), `is_opportunity`, `member_doc_ids[]`.

## 6.5 Verdict on your proposed field list

| Your field | Verdict |
|---|---|
| source, source_type, url, author, published_at, text | **keep, required** |
| source_id | **keep** — required for dedup, which you will need immediately |
| organization | keep — but as `org_identifiable` + `org_name` + **`org_evidence`** |
| author_type | keep — but **must carry its evidence field**, else it is a guess |
| engagement | keep, optional, **never cross-source** |
| payer, procedure | keep, optional, frequently null |
| problem_category | keep, **make it an array** |
| problem_description | **drop.** A paraphrase you cannot audit. |
| problem_evidence | **keep, and promote to required for T2+** — as a **verbatim quote**. Your best-designed field. |
| customer_type | **drop.** Collapses role + tier. Use `author_type` + `tier`. |
| solution_seeking | keep, **make it L0–L4**, not boolean |
| potential_prospect | **drop the boolean.** Replace with `tier`. A boolean here is exactly the overclaim you want to avoid. |
| opportunity_reason | **move to `clusters`.** A document is never an opportunity. |
| **missing:** `rule_hits`, `fetched_at`, `channel`, `pipeline_version`, `raw` | **add all five** |

---

# PART 7 — DASHBOARD V1

Four screens. Build them in this order. Build screen 4 first if you only build one.

**1. Problem Landscape** *(home)* — bar chart, 11 categories × problem-evidence count,
90-day window, with Δ vs. previous 90 days and `share_of_relevant` shown next to every
bar. Filters: specialty relevance, payer, date. Answers CEO questions 1–3.

**2. Problem Detail** *(drill-down)* — one cluster: metric row, a sparkline, and **the
verbatim quotes with links**. The quotes are the product. A CEO will believe five real
sentences from five real billers over any chart you can draw. Answers questions 4 and 7.

**3. Review Queue** — T4/T5 documents, newest first, each showing quote, tier, why it
qualified (the rule hits), source link, and Accept/Reject buttons. **Call it Review
Queue.** Answers questions 5 and 6.

**4. Source Health** — per channel per day: fetched, relevant, errors, last success.
Unglamorous, and the difference between a dashboard you can trust and one you cannot.
Without it, every number on screens 1–3 is unfalsifiable.

**Do not build:** real-time updates (daily batch is plenty), user accounts, alerting,
sentiment gauges, word clouds, network graphs, maps, or a chatbot. A static site
regenerated nightly from JSON is entirely sufficient for V1 and will not distract you.

---

# PART 8 — EVALUATION

Without this section the project is an opinion. With it, it is research.

## 8.1 The gold set

**300 documents, stratified — never random.** A random sample of Reddit is ~97%
irrelevant and teaches you nothing about the decisions that matter.

| Stratum | n | Purpose |
|---|---|---|
| Passes all three gates | 120 | measure precision on positives |
| Passes Gate A only | 80 | measure recall — find what the rules miss |
| Random from target channels | 50 | estimate true base rate |
| Deliberate hard negatives | 50 | vendor promo, news shares, patient posts, LinkedIn thought-leadership |

Your 95 LinkedIn posts are a ready-made hard-negative stratum. Relabel them under the new
scheme — an hour of work, and it converts a dead-end artefact into evaluation gold.

**Labelling protocol:** write the label definitions *before* looking at data. Label blind
to model output. Two labellers on 100 overlapping documents → Cohen's κ. Solo? Re-label
50 after a week and measure self-consistency. **If κ < 0.6, your definitions are ambiguous
— fix the definitions, not the model.** Discovering that early saves the project.

## 8.2 Metrics per layer

| Layer | Metric | Target V1 | Which error hurts |
|---|---|---|---|
| Relevance | P / R / F1 | P ≥ 0.70, R ≥ 0.60 | both |
| Problem category | per-class P/R, confusion matrix | macro-F1 ≥ 0.60 | confusion is informative |
| Author type | accuracy on non-`unknown` | ≥ 0.85 | **precision only** — `unknown` is a correct answer |
| Seeking level | exact + off-by-one, MAE | exact ≥ 0.60, ±1 ≥ 0.85 | ordinal |
| Tier / Review Queue | **precision@queue** | **≥ 0.60** | **precision. Only precision.** |
| Trend | back-test vs. a known dated event | direction correct | qualitative |

**Note the asymmetry, and design around it.** For Deliverable A (counting problems),
*recall* matters — miss half the posts and your proportions are still roughly right if the
misses are unbiased. For Deliverable B (the queue), only *precision* matters — a human
reviews every item, so a 40%-junk queue gets abandoned within two weeks, while missing a
lead costs only that lead. **Tune the gates loose for trends, tight for the queue.** In
practice: run one pipeline, apply a stricter threshold at the queue.

Recall for the queue is essentially unmeasurable — you cannot know what the whole internet
contained. Say so in the write-up rather than reporting a made-up figure.

## 8.3 Trend back-test

Pick a dated event you already have Phase 2 evidence for — the UHC prior-auth reduction
effective 2026-10-01 is perfect, and you already hold the documentation. Then ask: did the
Authorization cluster measurably move in the following weeks? If yes, your trend detection
responds to reality. If no, either the window is wrong, volume is too low, or practice
conversation lags policy by more than you assumed — each of which is a real finding worth
writing down.

## 8.4 The acceptance test that actually decides the project

Show the CEO five opportunity cards. For each, ask one question:

> *"Would you do anything differently because of this?"*

**3 of 5 yes = the project works.** No F1 score substitutes for this, and no F1 score
overrides it.

---

# PART 9 — PHASE-BY-PHASE ROADMAP

Estimates assume one person, part-time. Phases 0–5 are sequential. Phases 6–10 iterate
together. **Do not skip Phase 1.**

---

## PHASE 0 — Lock the business objective · *2 days*

- **Goal:** written, signed-off agreement on scope and on what success means.
- **Questions:** Is Deliverable A the primary goal? Does the CEO accept that named
  prospects will be single-digit per month? Who owns the legal/ToS decision?
- **Input:** this document.
- **Output:** a one-page scope memo; a named owner for source-access decisions.
- **Method:** a 30-minute conversation. Present the 0.2 table verbatim.
- **Success:** someone other than you has said "yes, Deliverable A is the goal."
- **NOT yet:** any code at all.

## PHASE 1 — Manual reality check · *1 day* — **THE MOST IMPORTANT PHASE**

- **Goal:** find out whether the signal exists *at all*, before building anything.
- **Questions:** Of 60 hand-collected posts — what % are problem evidence? What % have an
  identifiable role? What % show seeking ≥ L2? What % have an identifiable org? What % are
  pain-management-specific?
- **Input:** a browser and a spreadsheet. Nothing else.
- **Output:** a 60-row sheet: url, date, community, text, and your hand-label under Parts
  2–4. Plus five numbers — the base rates above.
- **Method:** open `r/CodingandBilling` and `r/MedicalCoding`, read the 30 most recent
  posts in each, label every one. Two to three hours.
- **Success:** you have five base rates written down. **There is no wrong answer** — a low
  number is a finding, not a failure, and finding it on day one instead of week six is the
  entire point.
- **Decision gate:** if problem-evidence rate < 10%, change sources before building.
  If T3+ rate < 2%, tell the CEO now that Deliverable B may not be viable.
- **NOT yet:** APIs, scripts, schemas, anything automated.

## PHASE 2 — Freeze the taxonomy · *1 day*

- **Goal:** definitions stable enough to label against consistently.
- **Questions:** Do the 11 categories cover what you saw in Phase 1? What did you have to
  force into "other"?
- **Input:** Phase 1's 60 labelled posts.
- **Output:** `config/lexicons.yaml` — categories, keywords, gate patterns, exclusions.
  Plus a label definition doc with one real example per category **taken from Phase 1**.
- **Method:** reconcile Part 3 against what you actually saw. Add categories you needed;
  delete ones that never fired.
- **Success:** you can re-label 20 Phase-1 posts a week later and agree with yourself ≥80%
  of the time.
- **NOT yet:** sub-categories, hierarchies, synonyms beyond what you observed.

## PHASE 3 — Source feasibility tests · *3 days, timeboxed*

Four independent tests. One day each, maximum. **A test that overruns is a failed test.**

- **Test 1 — Reddit access.** Register an OAuth app; submit the Data API access request
  with an honest commercial use-case description. Meanwhile, pull 100 posts from one
  subreddit to confirm the fields you need exist. *Pass:* you have 100 posts with id, url,
  text, timestamp, author.
- **Test 2 — Adzuna job coverage.** 100 healthcare billing/PA postings. Hand-count how
  many are independent practices vs. hospitals vs. staffing agencies vs. RCM vendors.
  *Pass:* ≥10% are practices. *Fail → drop the source that same day.*
- **Test 3 — LinkedIn H1 vs. H2.** 10 intent-shaped manual searches (Part 1.2). *Pass (H1):*
  ≥5 genuine practice-voice posts → escalate the access question. *Fail (H2):* ≤1 →
  LinkedIn becomes Phase-2-only. **This closes the question your existing data opened.**
- **Test 4 — Forum access.** Read `robots.txt` and terms for AAPC and one other forum.
  Document what is permitted. *Output is a written decision, not code.*
- **Output:** `sources.yaml` — the source register from Part 1.5, one row per channel,
  each marked go / no-go with a reason.
- **NOT yet:** building collectors for anything that has not passed its test.

## PHASE 4 — Build the raw dataset · *3 days*

- **Goal:** a growing, immutable corpus that nothing downstream can corrupt.
- **Questions:** How many documents per day? What fails, and how often?
- **Input:** `sources.yaml`.
- **Output:** `documents` table (Part 6.2), ~1,000–2,000 documents, plus a daily
  collection log.
- **Method:** one collector per source, one schema, append-only, dedup on
  `(source, source_id)`, store `raw` always. Run daily from day one — **time-series data
  you did not collect cannot be recovered later.**
- **Success:** it runs unattended for 5 consecutive days and the log shows what happened
  each day.
- **NOT yet:** classification, backfill heroics, a database server (JSONL or SQLite is
  fine).

## PHASE 5 — Preprocess · *2 days*

- **Goal:** clean, comparable text.
- **Input:** `documents`. **Output:** normalised text + `lang` + dedup flags.
- **Method:** strip markdown/HTML, normalise whitespace and unicode (**fix the cp1252
  encoding issue now**), concatenate title+body, language filter, near-duplicate detection
  via text hash — your LinkedIn corpus showed syndicated content posted verbatim by 4+
  accounts, and that will inflate every count if left alone.
- **Success:** manual review of 20 processed documents shows no mangled text.
- **NOT yet:** stemming, lemmatisation, stopword removal, embeddings. Your rules run on
  raw phrases; destroying phrasing destroys the rules.

## PHASE 6 — Problem detection · *3 days*

- **Goal:** implement Gates A/B/C and the exclusions.
- **Input:** preprocessed `documents`. **Output:** `annotations.relevance` + `rule_hits`.
- **Method:** regex over `lexicons.yaml`. No ML.
- **Success:** ≥70% precision on the Phase-1 hand-labelled 60. Every decision traceable to
  a named rule.
- **Method of improvement:** read the 20 worst false positives. Fix one rule. Re-run.
  Repeat three times, then stop.
- **NOT yet:** an LLM. Get the baseline number first — you cannot justify an LLM without
  a number to beat.

## PHASE 7 — Problem classification · *2 days*

- **Goal:** assign categories, payer, procedure, specialty relevance.
- **Input:** `problem_evidence` documents. **Output:** `problem_categories[]` + enrichment.
- **Method:** the keyword mapping you already have, extended to 11 categories. **Reuse
  `process_linkedin.py`'s `find_matches()` directly** — it is correct.
- **Success:** macro-F1 ≥ 0.60 on the gold set; <15% land in "other".
- **NOT yet:** topic modelling, clustering by embedding.

## PHASE 8 — Solution-seeking detection · *2 days*

- **Goal:** assign L0–L4.
- **Method:** pattern matching, most-specific-wins (check L3/L4 patterns before L1/L2).
- **Success:** exact-match ≥0.60, within-one ≥0.85 on the gold set.
- **NOT yet:** intent classification models.

## PHASE 9 — Role, org, and tiering · *2 days*

- **Goal:** assign `author_type`, `org_identifiable`, and `tier`.
- **Method:** self-statement patterns in text; profile fields where the source provides
  them; **default `unknown`**. Tier is pure derivation from Part 4.4 — no new logic.
- **Success:** ≥0.85 precision on non-`unknown` role assignments. A Review Queue exists
  with a non-zero but small number of items.
- **NOT yet:** entity linking, NPI registry matching, firmographic enrichment. All are
  Phase 12+ and all are how projects die.

## PHASE 10 — Clusters and trends · *3 days*

- **Goal:** aggregate documents into clusters with Part 5.2 metrics.
- **Input:** `annotations`. **Output:** `clusters` table.
- **Method:** group by `cluster_key`, compute metrics, compute 90/90 window deltas,
  **always alongside `share_of_relevant`** and behind the volume floor.
- **Success:** the top 5 clusters match your intuition from reading Phase 1's posts. If
  they do not, investigate — one of the two is wrong and you need to know which.
- **NOT yet:** forecasting, anomaly detection, seasonality decomposition.

## PHASE 11 — Opportunity detection · *1 day*

- **Goal:** apply the Part 5.4 checklist.
- **Output:** opportunity cards, each with six booleans and linked evidence.
- **Success:** 3–10 opportunities. **Fewer than 3 → thresholds too tight. More than 20 →
  too loose.** That range is the calibration target.
- **NOT yet:** scores, percentages, ML ranking.

## PHASE 12 — Manual validation · *3 days*

- **Goal:** build the gold set and measure everything.
- **Input:** Part 8.1 stratified sample. **Output:** 300 labelled documents + a metrics
  report.
- **Method:** label blind. Measure self-consistency. Compute every Part 8.2 metric.
- **Success:** you have real numbers and you know your weakest stage.
- **NOT yet:** tuning to the gold set until you have frozen it. Label first, then tune,
  then never re-label to make numbers look better.

## PHASE 13 — MVP dashboard · *4 days*

- **Goal:** the four screens in Part 7.
- **Method:** nightly batch → JSON → static HTML. Screen 4 first.
- **Success:** the Part 8.4 acceptance test — 3 of 5 cards change what the CEO would do.
- **NOT yet:** everything in the Part 7 "do not build" list.

## PHASE 14 — Phase 2 external intelligence · *later*

- **Goal:** connect payer/CMS policy events to observed practice problems.
- **Method:** your existing collectors, emitting a `policy_events` table with
  `(payer, procedure, effective_date, change_type, url)`. Join to `clusters` on
  `(payer, procedure)` within a time window.
- **The payoff, and why it is worth waiting for:**

  > *Phase 1 alone:* "Authorization complaints from pain practices rose 40% this quarter."
  > *Phase 2 alone:* "UHC changed prior-auth requirements effective Oct 1."
  > **Together:** "UHC's Oct 1 change is landing badly in pain practices — authorization
  > complaints citing UHC rose 40% in the six weeks after, and 6 practices asked publicly
  > how to handle it. Here is the outreach message."

  That last sentence is the actual product. But it is only possible because Phase 1
  established the baseline first. **Phase 2 without Phase 1 is a news reader.**
- **Success:** at least one cluster movement plausibly explained by a dated policy event.
- **NOT yet:** causal claims. Temporal correlation is a hypothesis for a human, not a
  finding.

---

# PART 10 — THE MVP, CONCRETELY

| Item | Decision |
|---|---|
| **Sources** | Reddit (3 subreddits, automated) · Adzuna (1 test) · LinkedIn (≤100, manual) |
| **Volume** | 1,000–2,000 documents; ~200 expected to be problem evidence |
| **Window** | 90 days rolling, daily collection |
| **Storage** | SQLite or JSONL. Three tables (Part 6). No server. |
| **Preprocessing** | strip markup, normalise unicode, dedup, English filter |
| **Categories** | the 11 in Part 3.1 |
| **Intent** | L0–L4 (Part 4.3) |
| **Tiers** | T0–T5 (Part 4.4) |
| **Opportunity** | 6-criterion checklist (Part 5.4) |
| **Dashboard** | 4 static screens (Part 7) |
| **Evaluation** | 300-document stratified gold set (Part 8) |
| **Total** | ~5–6 weeks part-time |

## Kill criteria — decide these now, not in the moment

Write these down before you start, so you are not negotiating with yourself later:

- **Phase 1 problem-evidence rate < 10%** → change sources before building anything.
- **Phase 1 T3+ rate < 2%** → tell the CEO Deliverable B is unlikely, and continue with A.
- **Adzuna practices < 10%** → drop job postings same day.
- **LinkedIn intent searches yield ≤1** → LinkedIn is Phase-2-only, permanently.
- **Any Phase-3 test overruns one day** → it failed. Move on.
- **Phase 12 precision < 0.50 after three rule iterations** → the rules approach is
  insufficient; *that* is the evidence that justifies trying an LLM.

---

# PART 11 — WHAT HAPPENS TO THE EXISTING CODEBASE

Nothing is thrown away. Everything is reassigned.

| Existing | Disposition |
|---|---|
| `test_uhc*.py`, `test_cigna*.py`, `test_aetna*.py`, `humana/`, `test_cms*.py`, `noridian_*`, `novitas_*`, `test_federal_register*.py` | **Phase 14 (external intelligence). Freeze now — do not extend.** Move to `phase2/`. |
| `test_beckers_rss.py` | **Keep running daily.** Cheap, and you will want the history. |
| `linkedin/process_linkedin.py` → `find_matches()` + the PAYERS/PROCEDURES/TOPICS dicts | **The single most reusable asset you have.** Extract the dictionaries to `config/lexicons.yaml`, keep the function, extend to 11 categories. This becomes the Phase 7 classifier. |
| `linkedin/data/raw/linkedin_posts_latest100.json` (95 posts) | **Relabel under the new scheme → hard-negative stratum of the gold set.** High value, one hour of work. |
| `retrieval_output/classify_*.py` | Good reasoning, wrong scope (D/S relative to payer events) and mixes raw with derived. **Read them for the labelling logic, then rewrite against the new three-table model.** |
| `retrieval_output/consolidate.py` | The consistency-check pattern is genuinely good — **port the validation idea into the new pipeline.** |
| Apify LinkedIn/X collectors | **Park.** Valid feasibility evidence, not a production decision. Revisit only after Phase 3 Test 3 and a legal sign-off. |
| `finalized_dashboard_concepts/*.png`, `sld_week1_mentor_presentation.html` | Review against Part 7. Keep any concept that shows clusters and evidence; discard any that shows mention counts. |
| `secrets` | **Move credentials out of the repo into env vars before anything else ships.** |

---

# PART 12 — ETHICS, ACCESS, AND RISK

Write this section into your mentor deliverable. A healthcare-adjacent company building a
prospect list from public posts will be asked these questions, and having the answers
ready is a strength, not an overhead.

1. **Public only.** No personal cookies, no logins, no private groups, no circumvention of
   access controls, ever. If a source requires an account to read, it is out of scope.
2. **Terms before access.** Every channel in `sources.yaml` carries a `legal_basis` field.
   "Technically possible" is never the justification — that distinction is exactly what
   separates the Apify experiments from a production decision.
3. **Provenance always.** Every stored record keeps its URL. Every dashboard claim links
   back to the original. If you cannot link it, you cannot claim it.
4. **No patient data.** Patient posts are excluded at the rule level and not retained.
   They can contain personal health information about the poster, and you have no reason
   to store them.
5. **Re-verify before acting.** Public posts get deleted and edited. Re-check any Review
   Queue item at the moment of outreach, not at the moment of collection.
6. **No model training on scraped content.** Reddit's terms prohibit it without
   rightsholder permission. This is one more reason the rule-based V1 is the right call.
7. **Humans decide.** No automated output ever reaches a prospect. Every T5 passes a
   person first.
8. **Minimise.** Do not store what you do not use. Do not enrich beyond what the public
   post supports.

---

# PART 13 — WHAT TO DO TOMORROW

**Do not open an editor. Open a browser and a spreadsheet.**

1. Create a sheet with these columns:
   `url · date · community · author_handle · text · is_rcm_topic · first_person ·
   problem_or_seeking · author_role · seeking_level · org_identifiable · pain_specialty ·
   tier · notes`

2. Open `r/CodingandBilling`. Read the **30 most recent posts**. One row each.
   Then `r/MedicalCoding`, another 30. **Do not filter. Do not skip boring ones** —
   the boring ones are your base rate, and the base rate is the finding.

3. Compute five numbers:
   - % that are genuine problem evidence
   - % with an identifiable role
   - % at seeking level ≥ L2
   - % with an identifiable organisation
   - % pain-management specific

4. **Send the CEO those five numbers and nothing else.** No architecture, no roadmap, no
   screenshots. Five numbers and ten example quotes, with the Part 0.2 expectation-setting
   table attached.

This takes two to three hours and answers the riskiest question in the entire project
before a single line of production code exists: **does this signal exist, and in what
proportion?**

Every architectural decision in Parts 2–8 is provisional until those five numbers are on
paper. If the problem-evidence rate is 30%, build exactly as specified. If it is 3%, we
rethink sources — and we will have learned that on day one, for the price of an afternoon,
instead of in week six for the price of the project.

**In parallel, two things with lead times — start them tomorrow, then forget about them:**
- Submit the Reddit Data API access request (2–4 week review).
- Ask whoever owns legal risk at PainMed-PA who signs off on source access.

---

*Next step after Phase 1: bring the 60 labelled rows back and we implement Phase 2
(`lexicons.yaml`) and Phase 6 (the gates) against your real data, one phase at a time.*
