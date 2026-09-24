# Facebook deep research: where RCM problems are discussed

24 Sep 2026 · new Apify token · actual Apify spend **$3.13** (cap $3.50) · Playwright screening free

**Question:** which public Facebook groups carry posts where practice-side people (billers, coders,
office/practice managers, RCM staff) discuss real problems — denials, prior auth, payer behavior,
coding disputes, credentialing, AR, operational pain — so that scraping them fills the SLD with
worthwhile content?

**Rule used:** a group counts only if its **recent posts** show those problems. Names and
descriptions were never accepted as evidence. Patient-voice groups excluded (existing decision).

## Method

| Step | Tool | Result |
|---|---|---|
| 1. Problem-phrased post search | Apify `scraper_one/facebook-posts-search`, 24 queries | 200 posts; 34 inside groups → leads. 15 queries returned nothing (the actor fails on most phrasings). |
| 2. Group directory search | Apify `easyapi/facebook-groups-search-scraper`, 4 queries (+3 from an earlier run) | 47 groups with visibility, member count, posts/day |
| 3. Web search | WebSearch | ~15 group/post URLs (therapy, credentialing, chiropractic, AR recovery…) |
| 4. Post-level probe | Apify `apify/facebook-groups-scraper`, 12 recent posts per group | **26 groups probed, ~300 posts read** (plus 150 PM&R posts from earlier today) |
| 5. Group page screening | Playwright (logged out) | public/private, members, About, latest post preview — 10 groups |

Playwright could not be used for discovery: Facebook search requires login, DuckDuckGo blocks
headless browsers, and Bing ignores `site:` for automated sessions. It was used for free screening.

## Recommended groups (ranked)

| # | Group | Members | Evidence from actual posts | Verdict |
|---:|---|---:|---|---|
| 1 | [PM&R and Interventional Pain Management Coding and Billing](https://www.facebook.com/groups/290657479460430) | 1.5K public | 19 of 43 substantive posts match: Aetna RFA denials, WPS ketamine denials, Humana/Cohere auth, Optum RFA audit, Medicare facet/ESI denials. Noise = auto welcome posts (107/150). | **Scrape** — best fit for pain/spine SLD |
| 2 | [Rural Health Clinics Information Exchange](https://www.facebook.com/groups/1503414633296362) | 8.3K public | 4 of 4 substantive posts match: [Medicaid secondary denials "modifier inappropriate"](https://www.facebook.com/groups/1503414633296362/permalink/3999733846997749/), [nursing-home services on UB claims](https://www.facebook.com/groups/1503414633296362/permalink/3999534007017733/) (13 comments), [two tax IDs, same patient](https://www.facebook.com/groups/1503414633296362/permalink/3999518053685995/), [IL D-SNP plans vs RHC AIR payment](https://www.facebook.com/groups/1503414633296362/permalink/3993053087665825/). Rest image-only/admin. | **Scrape** |
| 3 | [eCW users forum](https://www.facebook.com/groups/153075608691474) | 11.6K public | ~6 of 12 match: [losing money vs Medicare fee schedule](https://www.facebook.com/groups/153075608691474/permalink/1994867434512273/), [copays not collected vs eligibility](https://www.facebook.com/groups/153075608691474/permalink/1994758627856487/), [prior auth for imaging (RHC)](https://www.facebook.com/groups/153075608691474/permalink/1994817091183974/), [referral workflow breakdown](https://www.facebook.com/groups/153075608691474/permalink/1994799644519052/), [Devoted MA recouping payments](https://www.facebook.com/groups/153075608691474/permalink/1994837881181895/). Rest EHR how-to. | **Scrape** — operational pain, practice staff |
| 4 | [Home Health PDGM Billing](https://www.facebook.com/groups/541137026613054) | 6.5K public | ~5 of 12 match: [competing NOA filed, Palmetto dispute](https://www.facebook.com/groups/541137026613054/permalink/2129717094421698/) (12 comments), [payer change after eligibility backdating](https://www.facebook.com/groups/541137026613054/permalink/2129086897818051/), [MAC NOA lookup](https://www.facebook.com/groups/541137026613054/permalink/2129718871088187/), new Medicaid billing setup, clearinghouse comparison (Inovalon vs Waystar). ~5 vendor ads. | **Scrape** — home-health segment |
| 5 | [Dental Office Managers](https://www.facebook.com/groups/1594069521337374) | 92.2K public | Real payer behavior: [MetLife unreachable → going OON in 2027](https://www.facebook.com/groups/1594069521337374/permalink/2347956882615297/) (24 comments), Aetna SRP claims, Aetna/Guardian fee schedule after going OON, [billing/verification overload](https://www.facebook.com/groups/1594069521337374/permalink/2347998109277841/). Most posts are office ops/HR. | **Conditional** — only if dental RCM is in scope |

**Watch list (not enough signal yet):**
[Credentialing and Provider Enrollment Mentor](https://www.facebook.com/groups/667837087205621) (16.6K) —
[CAQH login change](https://www.facebook.com/groups/667837087205621/permalink/2018816255441024/),
[credentialing rates](https://www.facebook.com/groups/667837087205621/permalink/2018922172097099/) (19 comments), but
vendor-heavy; [Mental Health Billing Support](https://www.facebook.com/groups/892459929806231) (909) — one strong
[Medicaid-IL secondary denial thread](https://www.facebook.com/groups/892459929806231/permalink/1105867641798791/),
rest image-only/vendor.

**Private, likely high value, cannot be scraped without membership:**
Billing, Coding, and Tech Questions for Optometry (16.7K, ~7 posts/day),
Home Health Care Agency Professionals Network (27.8K), Home Health Billing and Consulting Network (696).
Joining with a real account is the only way to evaluate or collect these; public-content scraping excludes them.

## Rejected after reading their posts

| Group | Members | What the posts actually are |
|---|---:|---|
| Medical Billing & Coding Services (425049717601373) | 14K | coding-course links, image-only |
| Medical Billing & Coding (205515509641624) | 20K | hiring posts; 1 Aetna denial post in 15 |
| Medical Billing & Coding Services : USA (508076976000846) | 7.1K | vendor ads, BPO spam |
| Medical billing/RCM and Coding FB Group (3026751500879145) | — | coding courses, India hiring |
| The Medical Billing and Coding Facebook Group (41571027412) | 64K | job openings, exam-prep ads, image-only |
| Revenue Cycle Management Medical Billing (553528670079750) | — | AR-caller hiring, vendor ads |
| Medical Billing Work / MEDICAL BILLING & AR | 3.1K / — | hiring drives, PPO lead sales |
| Providers looking for a medical billing company (694861209638046) | 7.8K | RCM vendor promotion |
| Medical Billing & Credentialing Help for Providers (1192041616270325) | 3.5K | job posts, BPO spam, fundraiser |
| Providers with Medical billing and coding issues (2442249056164644) | 1.3K | vendor referrals, inactive |
| NPs in Private Practice Credentialing and Billing (3236340703349555) | 485 | one vendor posting RCM marketing daily |
| Urgent Care Billing Specialist (1566359524390709) | 456 | vendor ads, off-topic |
| Dme posting (1123047789852358) | — | PPO lead sales, virtual-card offers, BPO hiring |
| Medical and Healthcare VA community (1234383310708351) | — | Filipino BPO job chatter (1 good 59→XE post via search) |
| Entry-Level Medical Coders (368427913735844) | — | CPC exam/career questions |
| Medical Director Network / Private practice physicians | — | med-spa director listings, vendor ads |
| PPBSG, CCM practice managers | — | practice-startup/vendor ads; CCM group inactive since 2024 |
| Mental Health & Private Practice Owners (1622691768952692) | 4.4K | clinical referrals, hiring |
| Telehealth Counseling Tips, LMHC Central, Indiana Social Workers | — | clinical/career content |
| Aetna Medicare Advantage Members (1609888809770903) | — | members + Medicare-agent ads (patient voice) |
| Chiropractic Billing Group, Massage Insurance Billing, WA ASC Association | — | not retrievable (no public posts) |
| Job/vendor groups from directory search (US Medical Billing Latest Jobs, Doctors Looking For Medical Billers, Medical Billers Seeking Clients…) | — | names are job/vendor boards; not probed |

Patient groups surfaced by problem search (spine surgery, Intracept, SCS, UHC MA complaints)
carry genuine payer-denial signals but are excluded under the practice-side-only rule.

## What this means for the collector

- **Scrape 4 groups** (PM&R, RHC Information Exchange, eCW users forum, Home Health PDGM
  Billing); add Dental Office Managers only if dental is in scope.
- Expect **~40–50% useful posts** in these groups; the rest is welcome/admin posts, image-only
  posts and a few vendor ads. Dropping auto "welcome our new members" posts at collection time
  (PM&R) would remove most of that group's noise.
- The best signal is often in **comments** (e.g. "We do for knees: 0441T per nerve…").
  `apify/facebook-comments-scraper` works on group posts and is the next lever.
- Billing-named mega-groups (14K–64K members) are the worst sources: jobs, courses and vendor
  spam dominate. Group size and name are not predictors of value.

## Raw evidence on disk

`discovery/` (post search), `group_search/`, `probes/` (group posts), `pw_group_screen.json`
(Playwright), `spend.json` (estimated ledger; actual Apify usage $3.13).
