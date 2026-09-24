# X (Twitter) source discovery for SLD — 24 Sep 2026

Goal: find public X accounts and discussions where providers, practice owners
and billing people discuss **real** reimbursement / payer / denial / prior-auth
problems, validate them on the content of their posts (not names, bios or
hashtags), collect ~20 posts with Apify, and score them with the unchanged SLD
pipeline.

Source discovery and SLD scoring were kept separate: research decided which
accounts to collect from; the pipeline scored every collected post on its own.

## 1. Search strategy

**Web search (site:x.com / site:twitter.com).** Tried first and abandoned for
discovery: X pages are almost unindexed. `site:x.com` payer/denial queries
returned zero X results; general queries returned news coverage of physicians
on X (KFF Health News, AMA). Useful only for two leads (@ssaeed94,
@EStallmanMD — neither appeared in X-native results with recurring content).

**X-native search via Apify** (`tweetapi/twitter-x-search-scraper`, the actor
already used in `testing/latest_testing/test-x-post.py`). 18 problem-oriented
queries, `Top` mode, 50 posts each, all with `lang:en -filter:retweets`
(script: `backend/scripts/x_discover.py`, raw: `discovery/`). Queries combined
payer names + problem verbs + practice-side context, never bare "RCM" terms:

| Key | Query idea |
|---|---|
| uhc_denials, aetna_cigna_humana_denials | payer × denied/denying × claims × practice/"our office"/billing |
| pa_my_patient_p2p, p2p_denied_procedure, medical_necessity | "prior auth"/"peer to peer" × "my patient" × denied |
| ma_denials_practice, retro_denial_clawback | Medicare Advantage denials, clawback, recoupment |
| mac_lcd, fee_schedule_cuts | Novitas/Noridian/Palmetto/LCD; PFS/conversion factor |
| downcoding, modifier_coding | downcoding, level 5, E/M, modifier 25/59, CPT |
| pain_procedures | SCS, RFA, ESI, SI joint, kyphoplasty, Intracept, medial branch × denial/coverage |
| not_getting_paid, ar_backlog, payer_portal_hold, pa_staff_burden, medicaid_payment, nsa_idr | payment delay, A/R, portal/hold time, PA staffing, Medicaid, NSA/IDR |

**Validation.** No Playwright MCP server was connected in this session, and
X's login-free syndication timeline endpoint returns an empty shell, so account
inspection used the same actor with `from:<handle>` (`Latest`, 30 posts per
account, raw: `probes/`). Individual posts can also be confirmed without login
via `publish.twitter.com/oembed` (tested, works).

## 2. Candidates discovered

- Discovery: **725 unique posts from 516 authors**; 77 authors appeared 2+ times.
- Every post was read. **~45 authors/threads** showed at least one post with a
  real reimbursement problem and were considered candidates.
- **24** were taken to Phase 2 (30 recent posts each = 720 posts read).
- **9** accepted as ongoing sources; 15 rejected after inspection; the other
  ~21 were rejected at discovery stage (below).

What the query channels actually returned (reading, not keyword counts):

| Channel | What it was mostly | Verdict |
|---|---|---|
| uhc_denials | UHC CEO shooting commentary, $UNH stock posts, politics; a few real practice posts | noisy |
| aetna_cigna_humana_denials | patient bills, satire, investing threads, PBM rants | noisy |
| pa_my_patient_p2p / p2p_denied_procedure | **physicians describing specific PA/P2P denials** — best channel, but mostly one-off posts, and viral aggregator reposts (@WallStreetApes etc.) | good for discovery, not collection |
| ma_denials_practice, fee_schedule_cuts, nsa_idr | policy threads from a small set of independent-physician advocates | policy / market intel |
| mac_lcd | lab/device company press releases on LCD wins, stock tickers | reject |
| pain_procedures | device-maker coverage PR, patient opioid posts; one strong physician (@dougbeall) | one source |
| downcoding | Cigna/Aetna downcoding coverage, society payer-help promos (ASTRO ×6 identical) | market intel |
| modifier_coding | consumer "ask for an itemized bill" viral posts, AMA/CPT copyright fight | mostly noise |
| not_getting_paid, retro_denial_clawback, ar_backlog, payer_portal_hold | unemployment insurance, sports contracts, UK politics, crypto, RCM vendor ads | reject |
| medicaid_payment | Medicaid fraud/immigration politics | reject |

## 3. Rejected candidates and why

**Rejected after inspecting 30 recent posts (Phase 2):**

| Account | Who | Relevant / 30 | Reason |
|---|---|---:|---|
| @DrAmyPsyD | psychologist, private practice | 0 | mental-health blogging; the 2022/2024 payer posts were isolated |
| @SPuro88 | urologist | 0 | clinical banter; P2P stories were one-offs |
| @TruthAgape | therapist | 0 | personal/political; TRICARE non-payment post was isolated |
| @JCLinMD | urologist / coding educator | 0 recent | inactive since Oct 2025; conference photos, self-promotion |
| @sdixitmd | spine surgeon | 0 | politics/culture; spine-implant PA post was isolated |
| @txsportsdoc | orthopaedic surgeon | ~3 | mostly clinical/political; one good -22 modifier post (29827 not paid) — too sparse |
| @realdocspeaks | physician podcaster | ~5 | consumer-level insurance commentary, podcast promo |
| @DutchRojas | healthcare exec / commentator | ~2 | reply chatter, satire |
| @ForestParkPharm | compounding pharmacy | ~0 practice-side | consumer bill/pharmacy stories + product promotion (ivermectin codes) |
| @HEALTHCOSTtruth | TPA owner | ~0 practice-side | employer/self-funded plan side, not provider RCM |
| @CRCook1978 | anesthesiologist, society leader | ~6 | society advocacy, awards, network-adequacy testimony |
| @RenoDrew | family physician | ~4 | mostly sport/politics; one strong Optum MA contract termination post |
| @ShreeHistory | primary-care physician | ~5 | mostly Indian history/language; good PA ping-pong and $2.50 blood-draw posts but buried |
| @drdanchoi | spine surgeon | ~12 | NSA advocacy threads + podcast promotion; overlaps @DrBruggeman/@EdGainesIII — **secondary** |
| @IndeMedAction | independent-physician advocacy org | ~20 | low noise but pure advocacy; its data points are reposted by @DrBruggeman — **secondary** |

**Rejected at discovery stage:**

- **Aggregators / viral reposters** — @WallStreetApes, @WallStreetMav,
  @USADocumented, @MarioNawfal: repost physician videos with political framing;
  the original physicians are the source, not these accounts.
- **AI-generated / media feeds** — @FLDoctorMag, @AxionNeuro ("Created with AI
  assistance", identical posts), @kevinmd (article promotion), @OwenGregorian,
  @Benzinga, @Finsee_main, @Market_Pathways.
- **Vendors** — @GraceAnna5011 / @mbc_services (the pain-management "RCM"
  hashtag post in the old X test was this vendor), @theashezgroup, @KnackGlobal,
  @AgaBilling, @MedisysI, @EyeMedMgmt, @FastPayHealth, @First_Insight,
  @Availity, @SagilityHealth, @tech_mahindra, @notoveai, @DeskGate_App,
  @paulsingh, @3gen_consulting, @RSKRecovery.
- **Device/lab companies** — @4Kscore, @NateraGenetics, @siboneinc,
  @RelievantMed, @bsc_urology, @Hologic, @BSEM_Tech: coverage-win PR.
- **Societies** — @ASTRO_org (same payer-help promo 6×), @ACRheum, @aao_ophth,
  @AmerAcadPainMed, @ASIPP, @MGMA, @texmed: useful policy notices but
  announcement-style and infrequent. Worth a separate "policy feed" if wanted.
- **Celebrity/investor commentary** — @mcuban, @BillAckman: high reach,
  second-hand.
- **One-off physician posts** — @AaronNeinstein, @zaneskii, @babydocwhit,
  @aeshajobanputra, @generalorthomd, @BrianSachs, @ArthritisSTL, @pedalpt,
  @kenny_allen, @JacktheWhiz, @taperfadepomp: genuine direct pain, but a single
  post each (some from 2017–2022). They show that the best X content is
  scattered across many physicians rather than concentrated in a few accounts.

## 4. Selected sources and evidence

Nine accounts, all independent physicians/practice owners except one
reimbursement attorney. None describes itself as "RCM"; all were accepted on
their posts. Collector: `backend/app/collectors/x.py` (`DEFAULT_ACCOUNTS`).

| Account | Stakeholder | Signal type | Relevant / 30 | Noise | Ongoing? | Evidence (examples) |
|---|---|---|---:|---|---|---|
| [@dougbeall](https://x.com/dougbeall) | interventional spine / pain physician | **procedure-device, direct pain** | 5 (plus 8 more in 12 months) | high (course promotion) | **Yes — top priority for a pain practice** | Humana kyphoplasty denial on DEXA [2087548121697952005](https://x.com/dougbeall/status/2087548121697952005); Aetna sacroplasty final denial after P2P [2016549710824165861](https://x.com/dougbeall/status/2016549710824165861); Medicare misreading 22511 [2014350049271042112](https://x.com/dougbeall/status/2014350049271042112); WISeR PA for VCF [2019135035291627714](https://x.com/dougbeall/status/2019135035291627714) |
| [@STzorfas](https://x.com/STzorfas) | private-practice neurologist | direct pain, payer | ~6 | medium-high | Yes (filtered) | MA denies 99489 + G2212 on EOB [2089361047811399729](https://x.com/STzorfas/status/2089361047811399729); MA reprocess + recoup [2079238191018606991](https://x.com/STzorfas/status/2079238191018606991); 4–8 week payment lag [2090221240845758968](https://x.com/STzorfas/status/2090221240845758968) |
| [@DrAlexUrology](https://x.com/DrAlexUrology) | independent urologist (NYC) | direct pain + market intel | ~12 | medium | Yes | MetroPlus PA demanding cortisol test for implant [2101779122162942254](https://x.com/DrAlexUrology/status/2101779122162942254); UHC modifier-25 two appeals denied [2047521786418360735](https://x.com/DrAlexUrology/status/2047521786418360735); "$0 paid, many receipts" [2092762153358905372](https://x.com/DrAlexUrology/status/2092762153358905372) |
| [@josonenine](https://x.com/josonenine) | ASC + two-practice owner | direct pain (underpayment) | ~4 | high (politics) | Yes (filtered) | $0.01 ASC payment on $60k case, appeals denied, IDR won [2101175897092919583](https://x.com/josonenine/status/2101175897092919583) |
| [@JahangirAsgha10](https://x.com/JahangirAsgha10) | independent practice owner | direct pain, AR/cash flow | ~3 recent (more earlier) | high (politics) | Yes (filtered, watch) | office manager 11 h on hold for BCBS SC pre-auth [1888419038788768157](https://x.com/JahangirAsgha10/status/1888419038788768157); 60–120 day revenue lag [2100998230133649915](https://x.com/JahangirAsgha10/status/2100998230133649915) |
| [@EPotterMD](https://x.com/EPotterMD) | independent surgeon / ASC | direct pain, payer | ~10 | medium (advocacy) | Yes | insurer denies facility, steers patient [2101063199327994113](https://x.com/EPotterMD/status/2101063199327994113); OON with BCBS & UHC [2087303931432980834](https://x.com/EPotterMD/status/2087303931432980834) |
| [@DrBruggeman](https://x.com/DrBruggeman) | spine surgeon, practice CEO, IndeMed chair | **market intel / policy** | ~20 | low | Yes | IDR $1/$0 offers [2095627595614425390](https://x.com/DrBruggeman/status/2095627595614425390); 33–50% of claims unpaid [2097801665009103215](https://x.com/DrBruggeman/status/2097801665009103215); WISeR gold-carding, NSA RARC codes, PFS series |
| [@EdGainesIII](https://x.com/EdGainesIII) | reimbursement attorney / coding educator | **market intel / payer policy** | ~15 | low-medium (tennis) | Yes | EM groups litigating downcoding/prepayment review [2099922540521009265](https://x.com/EdGainesIII/status/2099922540521009265); Anthem reimbursement-cut lawsuit [2101986039342432552](https://x.com/EdGainesIII/status/2101986039342432552); MA audit error rates [2099910696997691692](https://x.com/EdGainesIII/status/2099910696997691692) |
| [@amyfaithho](https://x.com/amyfaithho) | emergency physician | policy / market intel | ~8 | medium | Yes (secondary) | 50% same-day E/M + procedure proposal [2077471856102191466](https://x.com/amyfaithho/status/2077471856102191466); UHC PA cut → back-end denials [2052137484406911006](https://x.com/amyfaithho/status/2052137484406911006) |

**Recurring discussion areas** (as opposed to accounts): the No Surprises Act
IDR fight (unpaid awards, $0 offers, QPA vacatur), Medicare Advantage denials
and downcoding, the CY2027 PFS (conversion-factor cut, 50% same-day E/M), CMS
WISeR prior auth for pain procedures (kyphoplasty, sacroplasty), Cigna/Aetna/BCBS
auto-downcoding of level 4–5 E/M, and prior-auth / peer-to-peer denials told by
physicians. The last one is the richest direct-pain vein but is spread thinly
across hundreds of physicians — it would need query-based collection, not an
account list.

## 5. Collection

`backend/scripts/collect_x.py`. Per account: `from:<handle> <PROBLEM_TERMS>
since:2025-09-24 lang:en -filter:retweets`, `Latest`, 15 posts, charge cap
$0.03/run. The query scoping is applied identically to every account; it is a
source definition, not scoring. Retweets and posts under 100 characters are
not collected.

- Returned: 129 posts; 127 collectable.
- 20 chosen from the 127 to prefer direct problem evidence (`selection.json`,
  with the researcher's label per post). Those labels are **not** stored in the
  DB or passed to the pipeline.
- Stored as `source="x"` in `normalized_items` (20 inserted, 0 updated, 0 id
  collisions with other sources). DB backed up first:
  `sld.db.bak-before-x-20260924153706`.
- Preserved per post: full text, author id/name/profile URL, `created_at`,
  post URL, `conversation_id`, `parent_id` (+ replied-to username) for replies,
  quoted-post id, engagement, the verbatim actor record in `raw_data`, and the
  exact search query, actor and account key in `source_metadata`.

Apify spend for the whole exercise (discovery + probes + collection, ~1,640
posts, 51 runs): about **$0.45**; account usage went from $3.28 to $3.74 of the
$5 monthly cap.

## 6. The 20 collected posts and their SLD results

Research columns (signal, problem category, payer) are the researcher's reading, from `selection.json`. SLD columns come from `scripts/run_pipeline.py --source x` (production `sld-analysis-v1` / `-v2`, Ollama llama3.1 fallback). The two were produced independently; nothing from the research columns was given to the pipeline.

| # | Post | Author (stakeholder) | Date | Research: signal | Research: problem category (payer) | SLD Step 1 relevant | Step 2 problem evidence | Stance / seeking | v1 | v2 | v2 band |
|---:|---|---|---|---|---|:-:|:-:|---|---:|---:|---|
| 1 | [2087548121697952005](https://x.com/dougbeall/status/2087548121697952005) | @dougbeall (interventional spine/pain physician) | 2026-08-12 | direct operational pain | procedure/device coverage denial (Humana) | no | no | neutral / — | 0.0 | 1.8 | Discard |
| 2 | [2026403715192611123](https://x.com/dougbeall/status/2026403715192611123) | @dougbeall (interventional spine/pain physician) | 2026-02-24 | direct operational pain | procedure denial, no appeal path (BCBS) | yes | no | neutral / L0 | 8.1 | 24.2 | Watch |
| 3 | [2016549710824165861](https://x.com/dougbeall/status/2016549710824165861) | @dougbeall (interventional spine/pain physician) | 2026-01-28 | direct operational pain | procedure denial after full appeal cycle (Aetna) | yes | yes | neutral / L0 | 10.1 | 24.2 | Watch |
| 4 | [2014350049271042112](https://x.com/dougbeall/status/2014350049271042112) | @dougbeall (interventional spine/pain physician) | 2026-01-22 | direct operational pain | coding / Medicare coverage interpretation (Medicare) | yes | yes | neutral / L0 | 10.4 | 27.5 | Watch |
| 5 | [2019135035291627714](https://x.com/dougbeall/status/2019135035291627714) | @dougbeall (interventional spine/pain physician) | 2026-02-04 | direct operational pain | CMS prior auth (WISeR) for pain procedure (Medicare (WISeR)) | no | no | neutral / — | 0.0 | 0.2 | Discard |
| 6 | [2089361047811399729](https://x.com/STzorfas/status/2089361047811399729) | @STzorfas (private-practice neurologist) | 2026-08-17 | direct operational pain | MA bundling / code denial on EOB (Medicare Advantage) | yes | yes | supplying / — | 17.2 | 27.5 | Watch |
| 7 | [2079238191018606991](https://x.com/STzorfas/status/2079238191018606991) | @STzorfas (private-practice neurologist) | 2026-07-20 | direct operational pain | MA reprocessing / recoupment (Medicare Advantage) | yes | no | supplying / — | 4.5 | 0.2 | Discard |
| 8 | [2090221240845758968](https://x.com/STzorfas/status/2090221240845758968) | @STzorfas (private-practice neurologist) | 2026-08-19 | direct operational pain | payment delay / AR (commercial + administrator plans) | no | no | neutral / — | 0.0 | 1.9 | Discard |
| 9 | [2101175897092919583](https://x.com/josonenine/status/2101175897092919583) | @josonenine (ASC/practice owner) | 2026-09-19 | direct operational pain | underpayment / appeal denied / IDR (commercial (unnamed)) | yes | yes | neutral / L0 | 28.0 | 76.0 | Act |
| 10 | [2100998230133649915](https://x.com/JahangirAsgha10/status/2100998230133649915) | @JahangirAsgha10 (practice owner) | 2026-09-18 | direct operational pain | cash flow / AR lag (insurers generally) | yes | yes | neutral / L0 | 10.5 | 1.9 | Discard |
| 11 | [2089799460394008776](https://x.com/JahangirAsgha10/status/2089799460394008776) | @JahangirAsgha10 (practice owner) | 2026-08-18 | direct operational pain | underpayment / IDR negotiation (insurers generally) | yes | yes | supplying / — | 5.8 | 0.2 | Discard |
| 12 | [2101063199327994113](https://x.com/EPotterMD/status/2101063199327994113) | @EPotterMD (independent surgeon/ASC) | 2026-09-18 | direct operational pain | site-of-care denial / steerage (unnamed commercial) | yes | no | supplying / — | 3.3 | 1.8 | Discard |
| 13 | [2081778182756168013](https://x.com/EPotterMD/status/2081778182756168013) | @EPotterMD (independent surgeon/ASC) | 2026-07-27 | direct operational pain | prior auth timing / benefit reset (unnamed) | yes | no | neutral / L0 | 11.4 | 11.2 | Watch |
| 14 | [2092762153358905372](https://x.com/DrAlexUrology/status/2092762153358905372) | @DrAlexUrology (independent urologist) | 2026-08-26 | direct operational pain | denied payment for delivered care (commercial (Elevance/UHC context)) | yes | yes | neutral / L0 | 26.1 | 24.2 | Watch |
| 15 | [2094967920736489551](https://x.com/DrAlexUrology/status/2094967920736489551) | @DrAlexUrology (independent urologist) | 2026-09-02 | market intelligence | denial rate / appeal recourse (ERISA, DOL) (health plans) | yes | yes | neutral / L0 | 18.0 | 17.6 | Watch |
| 16 | [2099922540521009265](https://x.com/EdGainesIII/status/2099922540521009265) | @EdGainesIII (reimbursement attorney) | 2026-09-15 | market intelligence | downcoding, denials, prepayment review (in-network EM) (health plans) | yes | yes | supplying / — | 23.5 | 17.6 | Watch |
| 17 | [2101986039342432552](https://x.com/EdGainesIII/status/2101986039342432552) | @EdGainesIII (reimbursement attorney) | 2026-09-21 | market intelligence | payer reimbursement-reduction policy / litigation (Anthem/Elevance) | yes | no | neutral / L0 | 14.8 | 1.9 | Discard |
| 18 | [2094839031817228774](https://x.com/DrBruggeman/status/2094839031817228774) | @DrBruggeman (spine surgeon/practice CEO) | 2026-09-01 | market intelligence | IDR offers / underpayment (insurers generally) | yes | no | neutral / L0 | 7.5 | 1.9 | Discard |
| 19 | [2052137484406911006](https://x.com/amyfaithho/status/2052137484406911006) | @amyfaithho (emergency physician) | 2026-05-06 | market intelligence | payer PA policy shift to back-end denials (UnitedHealthcare) | yes | no | seeking / L2 | 11.1 | 26.9 | Watch |
| 20 | [2077471856102191466](https://x.com/amyfaithho/status/2077471856102191466) | @amyfaithho (emergency physician) | 2026-07-15 | policy signal | CMS PFS: 50% same-day E/M + procedure (Medicare) | yes | no | supplying / — | 7.4 | 1.9 | Discard |

### Relevant vs noise

- **Research view.** All 20 selected posts carry a reimbursement/payer
  problem: 14 direct operational pain, 5 market intelligence, 1 policy signal.
  They were picked from a pool that was noisier. Of the 127 collectable posts
  returned by the problem-scoped account queries, about **75 (≈59%)** carried a
  real reimbursement, payer or policy signal. The rest were adjacent
  commentary (consolidation, CPT copyright, drug pricing, private-equity bills)
  or off-topic posts that still matched a problem word ("denied" admission to
  college, "paid" in sports). Without the problem-term scoping, the 720
  timeline posts from Phase 2 ran at roughly 25–30% relevant.
- **Pipeline view.** Step 1 marked **17 of 20** RCM-relevant; Step 2 found
  problem evidence in **9**. v2 bands: **1 Act, 0 Engage, 9 Watch, 10 Discard**
  (mean v2 14.5, mean v1 10.9).
- **Research vs pipeline.** 7 of the 14 direct-pain posts and 3 of the 5
  market-intel posts reached Watch or above. For context, current production
  v2 means are AAPC 24.4 (n=102), Facebook 16.5 (n=50), LinkedIn 10.9 (n=30)
  and Reddit 2.7 (n=35). X sits between Facebook and LinkedIn.

### Observations about how the pipeline read X posts (reported, not changed)

- **Missed direct-pain posts.** Step 1 marked three posts not relevant. The
  Humana kyphoplasty denial
  ([2087548121697952005](https://x.com/dougbeall/status/2087548121697952005))
  spells the payer "HUMATA". The WISeR prior-auth post
  ([2019135035291627714](https://x.com/dougbeall/status/2019135035291627714))
  has no denial vocabulary Step 1 recognises. The 4–8 week payment-delay post
  ([2090221240845758968](https://x.com/STzorfas/status/2090221240845758968))
  describes payment lag without claim/denial terms.
- **Speaker type.** 17 of 20 posts are `unknown` speaker. X records carry no
  author role or organisation, and short posts rarely say "our practice", so
  these physicians did not get the practice-side weighting that Facebook group
  posts often do.
- **Stance and seeking.** Most posts are complaints or statements, not
  questions, so seeking is L0 or none. Under v2 that caps most posts in Watch,
  even vivid denials (Aetna sacroplasty after appeal, P2P and a second appeal:
  v2 24.2). The only Act post is the $0.01 ASC payment
  ([2101175897092919583](https://x.com/josonenine/status/2101175897092919583),
  v2 76.0).
- **Possible tag false positives, worth a look.** The Anthem lawsuit post was
  tagged procedure `SCS`, and the MA recoupment post was tagged `RFA`; neither
  post is about those procedures.

## 7. Limitations

- **Playwright MCP was not available in this session.** Account validation
  used Apify `from:<handle>` pulls (30 recent posts per account), and post
  existence was confirmed with X's public oEmbed endpoint (20/20 public).
  Profiles, bios and full reply threads were not viewed in a browser. Bios
  were never used for acceptance anyway.
- **Web search barely indexes X.** `site:x.com` / `site:twitter.com` returned
  news about X rather than X posts. All real discovery came from X-native
  search through Apify.
- **The actor's `Top` mode spans years.** Discovery pulled posts from
  2017–2026, and many strong physician posts are old one-offs. Collection was
  therefore limited to the last 12 months (`since:2025-09-24`).
- **Apify limits.** The free plan allows 5 concurrent runs (three discovery
  queries had to be re-run), and the monthly cap is $5 ($1.26 left after this
  work). The second token in `.env` (`APIFY_TOKEN1`) did not authenticate.
- **Thread context.** Replies keep `parent_id`, `conversation_id` and the
  replied-to username, but parent posts were not fetched, so a short reply
  (e.g. STzorfas' recoupment reply) is scored without the post it answers.
- **Signal is diffuse.** The strongest X content is first-person denial
  stories from many different physicians, each posting once. An account list
  captures only the few who post about this repeatedly. Adding a scoped query
  channel (e.g. `"peer to peer" denied "my patient"`) is the obvious next
  experiment, but its noise rate on X is high (see section 2).
- **Selection bias.** The 20 posts were hand-selected for problem evidence, so
  their scores describe the best of X, not an unfiltered X stream.

## 8. Scoring logic unchanged

No file under `backend/app/analysis/` was edited. SHA-256 hashes of all 13
analysis modules were taken before the pipeline run
(`analysis_hashes_before.txt`) and after it (`analysis_hashes_after.txt`);
they are identical. The uncommitted changes to `llm_fallback.py`, `pipeline.py`
and `step4_speaker_stance_seeking.py` shown by `git status` were already there
when this work started. The changes made outside the new X files are:
`SOURCES` in `app/schemas/normalized.py` and `frontend/src/components/FilterBar.tsx`
gained `"x"`, which only allows the new source to validate and appear in the
filter.

## Files

- `backend/app/collectors/x.py`: collector (validated accounts, query, normalizer)
- `backend/scripts/collect_x.py`: fetch, select, store (`--from-raw`, `--ids-file`, `--store`)
- `backend/scripts/x_discover.py`, `backend/scripts/x_triage.py`: discovery and probe tooling
- `discovery/`, `probes/`, `collection/`: raw actor output
- `selection.json`: the 20 posts with research labels
- `sld_results.json`: pipeline outputs for the 20 posts
