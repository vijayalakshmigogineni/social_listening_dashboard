# Facebook source selection: 24 Sep 2026

Groups were judged by reading their actual recent posts against the SLD problem statement, never by name. Patient-voice groups were excluded by decision. Scoring logic and v2 weights were not changed.

**Spend:** $0.00 in this task. The Apify account was already over its $5 monthly limit ($5.74) because of parallel runs on the same token at 08:07-08:11 UTC (group search + group probes, ~$2.80). Those runs' stored results were downloaded free and used as the evidence here; no new actor run was possible.

## Rubric

A post matches if it shows at least one of: payer behavior/change; denial/reimbursement problem or emerging pattern; procedure/device trend; CMS/payer policy or coverage change; operational pain point / RCM opportunity; provider/practice market or operational trend.

Group rule: >=3 matching posts in the probed sample and matches >=~30% of substantive posts; names are never evidence.

## Groups considered

| Group | URL | Verdict | Evidence / reason |
|---|---|---|---|
| PM&R and Interventional Pain Management Coding and Billing | https://www.facebook.com/groups/290657479460430 | **accept** | 19 of 43 substantive posts (44%) are payer/denial/procedure signals from practice-side billers; the noise is auto welcome posts, not jobs or vendors |
| Medical Billing & Coding | https://www.facebook.com/groups/205515509641624 | **reject** | 1/15 match (Aetna denied 92507 as non-covered); rest hiring posts, links, image-only |
| Medical billing/RCM and Coding Facebook Group | https://www.facebook.com/groups/3026751500879145 | **reject** | 0/15: coding-course links, India hiring posts, image-only |
| Medical Billing & Coding Services : USA | https://www.facebook.com/groups/508076976000846 | **reject** | 0/15: vendor ads (underpayment services), BPO spam, interview-prep PDF, image-only |
| Medical Billing & Coding Services | https://www.facebook.com/groups/425049717601373 | **reject** | 0/15: coding-certification course links, image-only |
| Medical Billing Work | https://www.facebook.com/groups/506966970453053 | **reject** | 0/15: AR-caller hiring, BPO spam, PPO lead sales |
| MEDICAL BILLING & AR | https://www.facebook.com/groups/1770711423156593 | **reject** | 0/15: hiring drives, coding courses, job seekers |
| Providers looking for a medical billing company in the US | https://www.facebook.com/groups/694861209638046 | **reject** | 0/15: RCM vendor promotion, BPO spam |
| Medical Director Network | https://www.facebook.com/groups/3453935871529998 | **reject** | 0/15: med-spa medical-director listings, telehealth ads |
| Private practice physicians | https://www.facebook.com/groups/496827464316905 | **reject** | 0/15: vendor/compliance ads, job board, off-topic (skincare, group invites) |
|  | https://www.facebook.com/groups/153075608691474 | **not_probed** | Candidate (web search: 'Pros and cons of outsourced billing for small specialty...'); Apify monthly limit exhausted before it could be probed |
|  | https://www.facebook.com/groups/2832083760354364 | **not_probed** | Candidate (web search: 'best approach for payer contract negotiations...'); Apify monthly limit exhausted before it could be probed |
|  | https://www.facebook.com/groups/667837087205621 | **not_probed** | Candidate (web search: 'credentialing software recommended for physician...'); Apify monthly limit exhausted before it could be probed |
|  | https://www.facebook.com/groups/541137026613054 | **not_probed** | Candidate (Home Health PDGM Billing: web search + group search); Apify monthly limit exhausted before it could be probed |
|  | https://www.facebook.com/groups/892459929806231 | **not_probed** | Candidate (Mental Health Billing Support: group search); Apify monthly limit exhausted before it could be probed |
|  | https://www.facebook.com/groups/405137378221444 | **not_probed** | Candidate (Medical Practice Managers Increasing Revenue through CCM: group search); Apify monthly limit exhausted before it could be probed |
|  | https://www.facebook.com/groups/6335103055 | **not_probed** | Candidate (DOCTORS, MEDICINE & PRACTICE MANAGEMENT: group search); Apify monthly limit exhausted before it could be probed |
|  | https://www.facebook.com/groups/266108444522 | **not_probed** | Candidate (Washington Ambulatory Surgery Center Association: group search); Apify monthly limit exhausted before it could be probed |
|  | https://www.facebook.com/groups/4425387990835085 | **reject** | VA disability claims (veterans), not provider RCM: prior research posts |
|  | https://www.facebook.com/groups/3805049843060582 | **reject** | Medical Billing jobs in Pakistan: prior research posts |
|  | https://www.facebook.com/groups/431822400195488 | **reject** | vendor promo + internship seekers: prior research posts |
|  | https://www.facebook.com/groups/368427913735844 | **reject** | Entry-Level Medical Coders, career/school questions: prior research posts |
|  | https://www.facebook.com/groups/3993496944259606 | **reject** | The Coding Corner, career questions: prior research posts |
|  | https://www.facebook.com/groups/341015404031050 | **reject** | Spinal Cord Stimulator: Ask a Patient, patient voice (excluded by decision) |
|  | https://www.facebook.com/groups/lifeafterbacksurgery | **reject** | patient voice (excluded by decision) |
|  | https://www.facebook.com/groups/1409194587419208 | **reject** | medical_claims_tasks: Arabic-language education/promo, removed |
|  | https://www.facebook.com/groups/350382725467096 | **reject** | usa_medical_billing: spam, removed |
|  | https://www.facebook.com/groups/1071047149038089 | **reject** | nemt_claims_denials_remittances: private/empty, removed |

Also surfaced by group search but not probed, names clearly out of scope for provider RCM: ambulance sales/services groups (incl. Spanish-language), pharma medical-representative job groups, dental practice managers UK, surgery-for-students, travel surgery jobs, Korean/Philippine hospital groups.

## Selected group

**PM&R and Interventional Pain Management Coding and Billing**: https://www.facebook.com/groups/290657479460430

Sample: 150 most recent posts (13 Jun - 21 Sep 2026): 107 automatic welcome posts, 43 substantive, 19 matches. The noise is welcome posts, not jobs or vendors; the substantive posts are practice-side billers asking about live payer problems.

## New posts collected (15)

All from the selected group, all rubric matches. Scores are production `sld-analysis-v1/-v2`.

| # | Post URL | Date | SLD match (categories) | Evidence | v1 | v2 | v2 band |
|---:|---|---|---|---|---:|---:|---|
| 1 | https://www.facebook.com/groups/290657479460430/permalink/1607488961110602/ | 2026-09-02 | yes (payer_policy, operational) | Auth specialist says procedures >30 days after last encounter get medical-necessity denials; practice booking 45-60 days out | 17.7 | 69.0 | Act |
| 2 | https://www.facebook.com/groups/290657479460430/permalink/1595219802337518/ | 2026-08-18 | yes (denial, procedure) | Medicare denying facet injections 64493/64494 as 'questionable service' despite dx on Medicare guidelines | 17.0 | 23.6 | Watch |
| 3 | https://www.facebook.com/groups/290657479460430/permalink/1588819176310914/ | 2026-08-13 | yes (payer_behavior, denial, procedure) | Medicare/Medicare Advantage denying 62330/62331 on dx M48.062 and demanding mod 52 for bilateral | 26.8 | 77.0 | Act |
| 4 | https://www.facebook.com/groups/290657479460430/permalink/1590625826130249/ | 2026-08-13 | yes (reimbursement, payer_policy) | 99214 + G2211 billed, only G2211 paid | 0.0 | 8.8 | Discard |
| 5 | https://www.facebook.com/groups/290657479460430/permalink/1583130446879787/ | 2026-08-05 | yes (payer_behavior, payer_policy, procedure) | Humana Medicare prior auth via Cohere portal forces a listed code for unlisted 64999 ganglion impar block | 20.4 | 23.6 | Watch |
| 6 | https://www.facebook.com/groups/290657479460430/permalink/1572734961252669/ | 2026-07-24 | yes (payer_behavior, denial, procedure) | Thoracic RFA denied after Optum integrity medical-records review for 'wrong CPT' (64633/64634) | 21.2 | 29.1 | Watch |
| 7 | https://www.facebook.com/groups/290657479460430/permalink/1554278133098352/ | 2026-07-07 | yes (payer_behavior, denial) | Medicare MAC WPS denying ketamine infusions billed J3490 | 16.7 | 77.0 | Act |
| 8 | https://www.facebook.com/groups/290657479460430/permalink/1558963709296461/ | 2026-07-07 | yes (payer_behavior, reimbursement) | Devoted Health not paying office visits billed with IM injections / trigger point injections | 0.0 | 0.2 | Discard |
| 9 | https://www.facebook.com/groups/290657479460430/permalink/1548395837019915/ | 2026-06-25 | yes (payer_behavior, denial, procedure) | Aetna RFA denials for medical necessity, possibly tied to sedation | 18.5 | 2.7 | Discard |
| 10 | https://www.facebook.com/groups/290657479460430/permalink/1544200957439403/ | 2026-06-19 | yes (denial, emerging_pattern) | EMGs suddenly all denying for medical necessity | 13.3 | 2.0 | Discard |
| 11 | https://www.facebook.com/groups/290657479460430/permalink/1541843994341766/ | 2026-06-18 | yes (payer_behavior, reimbursement, procedure) | Medicare inconsistently bundling anesthesia with RFA | 18.3 | 26.9 | Watch |
| 12 | https://www.facebook.com/groups/290657479460430/permalink/1541541657705333/ | 2026-06-16 | yes (payer_change, operational) | Medicare claims keep rejecting after last month's eligibility change; EHR (eCW) fixes failing | 16.8 | 39.0 | Engage |
| 13 | https://www.facebook.com/groups/290657479460430/permalink/1531960658663433/ | 2026-06-16 | yes (coverage, procedure, rcm_opportunity) | Intrathecal pump refills with compounded meds (Anazeo) not covered; billing company can't explain | 13.7 | 2.9 | Discard |
| 14 | https://www.facebook.com/groups/290657479460430/permalink/1548281367031362/ | 2026-06-24 | yes (payer_policy, operational) | Auth denied for the procedure actually performed; practice billed the originally authorized code | 20.7 | 59.0 | Act |
| 15 | https://www.facebook.com/groups/290657479460430/permalink/1594120902447408/ | 2026-08-17 | yes (market_trend, operational) | Practice moving pain procedures from ASC to an in-office procedure suite (California) | 0.0 | 0.8 | Discard |

## Previously stored posts from the same group

Already in the DB before this task (not re-collected). With them, the DB holds 19 posts that match the problem statement, plus 1 partial.

| Post id | Verdict | v2 |
|---|---|---:|
| 1622055466320618 | match: Iovera cryoablation, which insurers pay and under what code (new-procedure coverage) | 2.9 |
| 1620918836434281 | match: qEEG reimbursement, Medicare fee schedule, recoupments/no-pays | 14.8 |
| 1619623016563863 | match: 64492 denials for third-level facet (TON) | 23.6 |
| 1618635949995903 | match: multiple claims denying for incorrect procedure code; appeals upheld | 59.0 |
| 1618694206656744 | partial: cupping 97140 vs unlisted, new service-line coding question | 11.6 |

The group's remaining stored posts (14) are automatic welcome posts collected earlier; they score Discard.

## Substantive posts not selected

| Post id | Why not |
|---|---|
| 1559645415894957 | UDS medical-necessity responsibility debate (lab vs provider): policy-adjacent, no payer/denial event |
| 1535368488322650 | Code choice for ganglion impar (64999/64451/64520): coding ambiguity, no payer event |
| 1553666149826217 | T12/L1 RFA code selection: coding education question |
| 1550014090191423 | Mod 59 on MBB + trigger points: coding education question |
| (others) | 9 job/biller-seeking or admin posts, 10 generic coding-education questions |

## Observations (no changes made)

- Quality target not padded: 15 new matching posts, not 20. Together with the 4 matching posts already stored from this group, the DB holds 19 high-quality Facebook posts.
- v2 under-scores several strong posts. Short posts like 'Rfa denials aetna... Denial medical necessit' (2.7) and 'EMGs... all denying medical necessity?' (2.0) have no word from v2's billing-vocabulary list (claim, billing, code, CPT...), so the off-domain factor (x0.10) applies despite a named payer and a denial. 'Devoted Health' is not in the payer list and Step 1 found no RCM keyword, so that post scored 0.2. These are measurement gaps to fix with human labels, not reasons to drop the posts.
- Only one group qualified. Candidates found by web search (outsourced billing, payer contracting, credentialing, home-health PDGM billing) could not be probed after the Apify limit was hit; they are the first to probe when the cycle resets on 15 Oct 2026.
