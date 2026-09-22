# REDDIT APIFY DATA VALIDATION

**Prepared for:** PainMed-PA SLD engineering + product
**Experiment date:** 2026-09-21 · **Total cost:** **$0.67** (3 actor runs)
**Purpose:** determine whether a current Apify Reddit Actor returns the fields our
canonical schema requires, and whether the content is relevant to our problem
statement.

> **Scope boundary, stated once and not revisited.** This is a technical
> data-validation experiment. Successful retrieval through Apify says nothing
> about whether PainMed-PA is permitted to use Reddit data commercially. That
> question is answered separately in `REDDIT-SOURCE-INVESTIGATION.md` and remains
> open. Nothing below should be read as establishing permission.

**Headline result, so it is not buried:** the Actor is technically excellent —
**every field our schema needs is available or derivable, and comment threads
reconstruct perfectly**. The content returned by *unrestricted keyword search*
is not. **0 of 27 inspected posts contained first-person practice-side RCM
problem evidence.** That is a query-strategy finding, not a source finding, and
§"30-Post Data Quality Results" explains why and what to do instead.

---

## Actor Used

| Item | Value |
|---|---|
| Actor name | Reddit Scraper - All in One (`reddit-scraper-pro`) |
| Owner | `harshmaur` |
| Actor URL | https://apify.com/harshmaur/reddit-scraper-pro |
| Actor ID | `3XedXIRBcjfKrnsDJ` |
| Build used | `0.0.511`, finished **2026-09-21T00:25:09Z** (actively maintained) |
| Created | 2024-08-24 |
| Usage | 1,934,824 runs · 3,233 users |
| Pricing model | `PAY_PER_EVENT`, effective 2026-08-29 |
| Cost per result | **$0.0015** (FREE tier) → $0.0012 at GOLD+ |
| Actor start | $0.01 per run |
| Optional AI events | `analyzed_item` $0.0005, `custom_label` $0.0001 — **not used** |

**Capability confirmation (verified by running, not by reading docs):**

| Capability | Confirmed? | Evidence |
|---|---|---|
| Searches Reddit | **Yes** | R1 returned 252 posts across 10 keywords |
| Keyword search | **Yes** | `searchTerms` array; each keyword runs as a separate search |
| Subreddit-restricted search | Yes (input schema `withinCommunity`) | **Not exercised** — `withinCommunity` takes only ONE subreddit per run |
| Full subreddit scrape | Yes (`subredditUrls`) | Not exercised in this experiment |
| Retrieve posts | **Yes** | 252 posts, 75 fields |
| Retrieve comments | **Yes** | 160 comments, 38 fields, depths 0–5 |
| Historical / date filtering | **Yes, precisely** | R3: 20/20 posts inside a 2024-01-01 → 2024-06-30 window |
| Returns raw Reddit information | **Yes** | Flat JSON, storable verbatim; includes Reddit fullnames (`t3_`, `t1_`, `t2_`, `t5_`) |
| Pagination | **Handled internally** | No cursor exposed; you set `maxPostsCount` and the Actor paginates |

### Why this Actor for this experiment

1. **It is the only current Reddit Actor with a documented comment schema.**
   Comments are the untested half of our hypothesis — our existing 320-item
   sample in `data/raw/` is 100% posts, zero comments.
2. **It returns `authorId` as a Reddit `t2_` fullname on posts.** The Actor used
   in Phase 1 (`trudax/reddit-scraper-lite`) returns only `username`. Reddit's
   deletion rules key on the `t2_` id, so without it there is no stable key to
   purge by.
3. **It supports true date-range windows** (`postedAfter` / `postedBefore`),
   which the official Reddit API does not — the official search endpoint offers
   only `hour|day|week|month|year|all`.
4. **It is 2.7× cheaper per result** than the Phase 1 actor ($0.0015 vs $0.004).
5. **It is current.** Built the same day as this experiment. By contrast
   `trudax/reddit-scraper` (the full version) now carries `isDeprecated: true`.

---

## Test Configuration

Reproducible via `problem-intelligence/reddit/apify_field_validation.py`.
Credential: existing `APIFY_TOKEN` from `linkedin/.env` (never printed or copied).

| Run | Purpose | Run ID | Items | Cost |
|---|---|---|---|---|
| **R1** | keyword search, posts only | `AB1bRqTeKBdogYOK0` | 252 | $0.388 |
| **R2** | comments for 4 posts from R1 | `htadtsvfrbd0rrUv4` | 164 (160 comments + 4 posts) | $0.266 |
| **R3** | historical date window | `HreCdd6fa6y0hX2xi` | 20 | $0.0175 |

### R1 input (verbatim)

```json
{
  "searchTerms": [
    "\"prior authorization\" pain management",
    "\"pain management\" claim denial",
    "\"pain clinic\" billing",
    "\"pain management\" reimbursement",
    "\"epidural steroid injection\" denied",
    "\"radiofrequency ablation\" prior authorization",
    "\"pain management\" credentialing",
    "\"interventional pain\" billing",
    "64483 denial",
    "\"pain management\" insurance verification"
  ],
  "searchPosts": true,
  "searchComments": false,
  "searchSort": "relevance",
  "searchTime": "all",
  "crawlCommentsPerPost": false,
  "maxPostsCount": 36,
  "includeNSFW": false,
  "proxy": { "useApifyProxy": true, "apifyProxyGroups": ["RESIDENTIAL"] }
}
```

### R2 input (verbatim)

```json
{
  "startUrls": [
    {"url": "https://www.reddit.com/r/anesthesiology/comments/1uvmbsy/ohio_has_opted_out_of_supervision_for_crnas/"},
    {"url": "https://www.reddit.com/r/medicine/comments/135slm5/what_do_you_think_of_people_who_advocate/"},
    {"url": "https://www.reddit.com/r/medicine/comments/1s9smzp/had_a_peer_reviewer_refuse_to_provider_name/"},
    {"url": "https://www.reddit.com/r/PainManagement/comments/1jlb0qt/methadone_for_pain/"}
  ],
  "searchTerms": [],
  "crawlCommentsPerPost": true,
  "maxCommentsPerPost": 40,
  "maxPostsCount": 4,
  "fastMode": false,
  "includeNSFW": false,
  "proxy": { "useApifyProxy": true, "apifyProxyGroups": ["RESIDENTIAL"] }
}
```

### R3 input (verbatim)

```json
{
  "searchTerms": [
    "\"prior authorization\" pain management",
    "\"pain management\" claim denial"
  ],
  "searchPosts": true,
  "searchComments": false,
  "postedAfter": "2024-01-01",
  "postedBefore": "2024-06-30",
  "crawlCommentsPerPost": false,
  "maxPostsCount": 15,
  "includeNSFW": false,
  "proxy": { "useApifyProxy": true, "apifyProxyGroups": ["RESIDENTIAL"] }
}
```

### ⚠ First limitation, found immediately

**`maxPostsCount` is applied PER SEARCH TERM, not as a total.** We requested 36
and received **252** — 10 keywords × up to 36 each. Cost was 7× the estimate.

At scale this matters: a 20-keyword run with `maxPostsCount: 100` returns up to
2,000 results (~$3.00), not 100 (~$0.15). **Budget by
`keywords × maxPostsCount`, and cap runs with Apify's per-run charge limit.**
(The two niche keywords returned only 2 and 1 posts, so it is a ceiling, not a
quota.)

---

## Actual Output Fields

Read from the real dataset, not from documentation.

### Posts — 75 fields (74 on every item; `images` on 44/252)

```
ageHours              archived              authorFlairText       authorId
authorName            authorPremium         bannedBy              body
bodyHtml              bodyLength            commentToScoreRatio   commentsCount
commentsPerHour       communityId           communityName         contentUrl
crawledAt             createdAt             dataType              distinguished
domain                edited                editedAt              engagementTotal
flair                 galleryCount          galleryData           galleryImages
gilded                hasMedia              hidden                id
images                isGallery             isHighEngagement      isOriginalContent
isRobotIndexable      isSelf                isVideo               locked
media                 mediaAssets           mediaMetadata         mediaType
modReasonTitle        numCrossposts         numDuplicates         outboundUrlHost
over18                parsedAuthorId        parsedCommunityId     parsedCommunityName
parsedId              pinned                postType              postUrl
removalReason         removedBy             removedByCategory     score
scoreHidden           scorePerHour          searchTerm            secureMedia
spoiler               stickied              subredditSubscribers  thumbnail
title                 titleLength           totalAwardsReceived   upVotes
upvoteRatio           urlOverriddenByDest   videoUrl              wordCount
```

**Representative post record** (`t3_1virjqk`, abridged — values real):

```json
{
  "dataType": "post",
  "id": "t3_1virjqk",
  "parsedId": "1virjqk",
  "title": "I got Intracept 24 hours ago: A log of my experience",
  "body": "Background: I herniated the disc at L5-S1 seventeen years ago...",
  "postUrl": "https://www.reddit.com/r/backpain/comments/1virjqk/i_got_intracept_24_hours_ago_a_log_of_my/",
  "contentUrl": "https://www.reddit.com/r/backpain/comments/1virjqk/...",
  "authorName": "Turbulent-Dirt7164",
  "authorId": "t2_1qnb878utq",
  "parsedAuthorId": "1qnb878utq",
  "authorFlairText": null,
  "communityName": "r/backpain",
  "parsedCommunityName": "backpain",
  "communityId": "t5_2rdud",
  "subredditSubscribers": 83660,
  "createdAt": "2026-08-08T09:30:25.000Z",
  "crawledAt": "2026-09-21T02:59:00.441Z",
  "edited": true,
  "editedAt": "2026-08-14T09:43:51.000Z",
  "score": 4, "upVotes": 4, "upvoteRatio": 1,
  "commentsCount": 8, "engagementTotal": 12, "totalAwardsReceived": 0,
  "mediaType": "text", "postType": "text", "isSelf": true, "hasMedia": false,
  "removedByCategory": null, "isRobotIndexable": true, "over18": false,
  "searchTerm": "\"radiofrequency ablation\" prior authorization",
  "wordCount": 1555, "bodyLength": 8846
}
```

### Comments — 38 fields (all present on all 160)

```
ageHours              authorFlairText       authorFullname        authorId
authorName            authorPremium         body                  bodyHtml
bodyLength            collapsed             collapsedReason       commentCreatedAt
commentUpVotes        controversiality      crawledAt             dataType
depth                 distinguished         edited                editedAt
gilded                id                    isSubmitter           parentId
parentKind            parsedAuthorId        parsedParentId        parsedPostId
parsedSubredditId     postId                score                 scoreHidden
scorePerHour          stickied              subredditId           subredditName
totalAwardsReceived   url                   wordCount
```

**Representative comment record** (`oxcc0bb`, abridged — values real):

```json
{
  "dataType": "comment",
  "id": "oxcc0bb",
  "url": "https://www.reddit.com/r/anesthesiology/comments/1uvmbsy/.../oxcc0bb/",
  "body": "I am more worried about pay cuts to physicians...",
  "postId": "t3_1uvmbsy",
  "parsedPostId": "1uvmbsy",
  "parentId": "t1_oxc8luz",
  "parsedParentId": "oxc8luz",
  "parentKind": "comment",
  "depth": 1,
  "isSubmitter": true,
  "authorName": "dfsyl442",
  "authorId": "t1_oxcc0bb",          // ← SEE TRAP BELOW
  "authorFullname": "t2_5birzmk7",   // ← this is the real author id
  "authorFlairText": null,
  "subredditName": "anesthesiology",
  "subredditId": "t5_2uoic",
  "commentCreatedAt": "2026-07-13T20:13:46.000Z",
  "crawledAt": "2026-09-21T03:01:04.621Z",
  "score": 81, "commentUpVotes": 81, "controversiality": 0,
  "edited": false, "editedAt": null, "collapsed": false
}
```

### ⚠ Three discrepancies between the Actor's README and its real output

| # | README says | Actual output | Impact |
|---|---|---|---|
| 1 | `authorId` = "Author fullname" | **On comments, `authorId` = `t1_` + the comment's own id** — verified `authorId == "t1_" + id` for **160/160** comments. The real author id is in `authorFullname` (`t2_`, present on 147/160; `null` on the 13 `[deleted]` authors). | **High.** Mapping `authorId` naively would store the comment id as the author id on every comment, silently breaking author-level deletion compliance. |
| 2 | Comments carry `postTitle` and `postCommentsCount` "when the parent post was also fetched" | **Absent on 160/160**, even though all 4 parent posts *were* fetched in the same run. | Medium. Join to the post record yourself on `postId`. |
| 3 | "41 fields" for comments, "75" for posts | Comments: **38**. Posts: 74 universal + `images` on 44/252 = 75 max. | Low, but confirms the README is not a contract. |

**Field-name differences between the two shapes** — a normaliser must handle these:

| Concept | Post field | Comment field |
|---|---|---|
| Created timestamp | `createdAt` | **`commentCreatedAt`** |
| Permalink | `postUrl` | **`url`** |
| Community | `communityName` (`r/x`), `parsedCommunityName` | **`subredditName`** (bare, no `r/`) |
| Title | `title` | **absent** |
| Author id | `authorId` (`t2_`) | **`authorFullname`** (`t2_`) |

---

## Canonical Schema Mapping

### A. Source-provided fields

| Our Field | Returned? | Actual Actor Field | Direct / Derived / Unavailable | Example | Useful? | Notes |
|---|---|---|---|---|---|---|
| `source` | **No** | — | **Derived** (collector constant) | `"reddit"` | Yes | Actor never emits a platform name. Set it yourself. |
| `source_item_id` | **Yes** | `id` (+ `parsedId`) | **Direct** | `t3_1virjqk` / `oxcc0bb` | Yes | Posts prefixed `t3_`; **comments are NOT prefixed** (`oxcc0bb`, not `t1_oxcc0bb`). Normalise before using as a key. |
| `url` | **Yes** | `postUrl` (posts) · `url` (comments) | **Direct** | `https://www.reddit.com/r/backpain/comments/1virjqk/...` | Yes | **Do not use `contentUrl`** — on 39/252 posts it is the *external* link, not the Reddit permalink. |
| `title` | **Yes** (posts only) | `title` | **Direct** | `"Pain Management insurance prior authorizations"` | Yes | Absent on comments. Also `titleLength`. |
| `text` | **Yes** | `body` (+ `bodyHtml`) | **Direct** | markdown text | Yes | **8/252 posts had empty bodies** (link/image posts). `wordCount`, `bodyLength` provided free. |
| `author_id` | **Yes (posts) / Yes-with-fix (comments)** | posts `authorId` (`t2_`, 252/252) · comments **`authorFullname`** | **Direct, mapping required** | `t2_1qnb878utq` | Yes | See discrepancy #1. `null` for 13/160 deleted-author comments. |
| `author_name` | **Yes** | `authorName` | **Direct** | `Turbulent-Dirt7164` | Yes | `[deleted]` appears (13/160 comments; 0/252 posts). |
| `author_profile_url` | **No** | — | **Derivable** | `https://www.reddit.com/user/{authorName}` | Marginal | Trivial to construct. Subject to the same deletion duty as the username. |
| `author_role` | **Partially** | `authorFlairText` | **Partly direct, mostly derived** | `"Anesthesiologist"`, `"MD"`, `"RN"`, `"CA-3"` | **Yes — better than expected** | Populated on **37/252 posts (14.7%)** and **84/160 comments (52.5%)**. In clinician subs it is a clean role label. **In patient subs the same field carries self-declared diagnoses** (`"Lupus/Cauda Equina/7+ disc bulges"`, `"hEDS"`) — see Organization/Author section. |
| `organization_name` | **No** | — | **Derived (NLP)** | — | Rarely | Not a Reddit field. See Organization/Author section. |
| `organization_url` | **No** | — | **Derived** | — | Rarely | — |
| `location` | **No** | — | **Derived (NLP)** | `"[PA]"`, `"Wisconsin"`, `"Location: Florida"` in post text | Sometimes | Volunteered in text in several sampled posts; never a structured field. |
| `created_at` | **Yes** | `createdAt` / `commentCreatedAt` | **Direct** | `2026-08-08T09:30:25.000Z` | Yes | ISO-8601 UTC, **not** Unix epoch. Differs from the official Reddit API (`created_utc`). |
| `collected_at` | **Yes** | `crawledAt` | **Direct** | `2026-09-21T02:59:00.441Z` | Yes | The Actor supplies it; you don't have to stamp it. Present on posts and comments. |
| `engagement` | **Yes, richly** | `score`, `upVotes`, `upvoteRatio`, `commentsCount`, `totalAwardsReceived`, `gilded`, `numCrossposts` | **Direct** | `score=4, upvoteRatio=1, commentsCount=8` | Yes | Actor-computed extras: `engagementTotal`, `scorePerHour`, `commentsPerHour`, `commentToScoreRatio`, `isHighEngagement`, `ageHours`. These are **the Actor's derivations, not Reddit's** — recompute if you need auditability. |
| `parent_id` / `conversation_id` | **Yes (comments)** | `parentId`, `parentKind`, `postId`, `depth` | **Direct** | `parentId="t1_oxc8luz"`, `postId="t3_1uvmbsy"`, `depth=1` | Yes | Posts have no parent — correct, not missing. |
| `media_type` | **Yes** | `mediaType` (+ `postType`, `isSelf`, `isVideo`, `isGallery`, `hasMedia`, `domain`) | **Direct** | observed: `text` 213, `image` 18, `gallery` 12, `link` 6, `video` 3 | Yes | `mediaType` is the cleanest single value; `postType` is noisier (`text` and `self` both appear). |
| `raw_data` | **Yes** | whole item | **Direct** | flat JSON object | Yes | Every item is a flat JSON object — storable verbatim. Inherits the deletion obligations from the terms investigation. |
| `source_metadata` | **Yes, extensive** | `communityName`, `communityId`, `subredditSubscribers`, `flair`, `over18`, `locked`, `archived`, `stickied`, `pinned`, `distinguished`, `edited`, `editedAt`, `removedByCategory`, `isRobotIndexable`, `searchTerm` | **Direct** | `subredditSubscribers=83660` | Yes | See "bonus fields" below. |

**Bonus fields not in our schema that we should capture:**

| Field | Why it earns a column |
|---|---|
| `searchTerm` | **Query provenance.** Tells you which keyword surfaced an item — essential for measuring query precision. Present on all search-sourced posts; absent on `startUrls`-sourced items. |
| `removedByCategory` + `isRobotIndexable` | **Deletion-compliance signal.** `removedByCategory` was `null` on all 252 (no removed content in this pull), but it is the mechanism for tombstoning. |
| `subredditSubscribers` | Community size at crawl time — needed to normalise engagement across communities. |
| `edited` / `editedAt` | Detects revision. `t3_1virjqk` was created 2026-08-08 and edited 2026-08-14. |
| `isSubmitter` (comments) | **Is this the OP replying?** Directly useful for `first_person` classification. |
| `depth` (comments) | Thread position; useful for weighting evidence. |

### B. Enriched fields

| Field | Source-provided? | Verdict |
|---|---|---|
| `organization_name` | No | **Derived (NLP)** — and see Organization/Author section for the yield reality |
| `organization_url` | No | **Derived** |
| `location` | No | **Derived (NLP)** from text |
| `author_role` | **Partially** — `authorFlairText` | **Hybrid.** Use flair where present (14.7% posts / 52.5% comments), NLP otherwise |
| `procedure_tags` | No | **Derived (NLP)** — CPT codes and procedure names appear in text |
| `payer_tags` | No | **Derived (NLP)** — `BCBS federal`, `Medicare` appear in text |
| `denial_reason_tags` | No | **Derived (NLP)** |

### C. Intelligence fields — all DERIVED, none source-provided

`rcm_relevant` · `problem_evidence` · `first_person` · `problem_category` ·
`pain_management_relevant` · `seeking_level` · `evidence_quote` ·
`classification_reason` · `classification_version`

The Actor returns **none** of these and is not expected to. One partial input:
`isSubmitter` on comments is a genuine source signal for `first_person`.

---

## Comment / Thread Test

**Result: full thread reconstruction is possible. No gaps.**

| Metric | Result |
|---|---|
| Comments retrieved | 160 (`maxCommentsPerPost: 40` × 4 posts — respected exactly) |
| Depth distribution | `0`: 54 · `1`: 45 · `2`: 35 · `3`: 19 · `4`: 6 · `5`: 1 |
| Top-level (`parentKind == "post"`) | 54 |
| Replies (`parentKind == "comment"`) | 106 |
| **Replies whose parent comment was missing from the sample** | **0** |
| Every comment has a resolvable `postId` | **Yes (160/160)** |
| `postId` values matching a returned post record | **4 of 4** |

Required fields, all present on 160/160:

| Needed | Actor field | Present |
|---|---|---|
| comment ID | `id` | ✅ (unprefixed) |
| text | `body`, `bodyHtml` | ✅ |
| author | `authorName` | ✅ (`[deleted]` on 13) |
| author id | `authorFullname` | ✅ 147/160 (`null` for deleted) |
| timestamp | `commentCreatedAt` | ✅ |
| score | `score`, `commentUpVotes` | ✅ |
| parent comment ID | `parentId` / `parsedParentId` | ✅ |
| parent post ID | `postId` / `parsedPostId` | ✅ |
| permalink | `url` | ✅ |
| thread/post ID | `postId` | ✅ |

Reconstruction is a single pass — build `{id: comment}`, then attach each
comment to `parsedParentId` when `parentKind == "comment"` and to the post when
`parentKind == "post"`:

```
Post t3_1uvmbsy
 ├── depth 0 comment  (parentKind="post")
 │    ├── depth 1 reply  (parentId="t1_<parent>")
 │    │    └── depth 2 reply
 │    └── depth 1 reply
 └── depth 0 comment
```

**What is missing:** nothing structural. Two caveats:

1. **Truncation is by count, not by tree.** `maxCommentsPerPost: 40` on a post
   with 442 comments returns the first 40 in Reddit's default order. Those 40
   happened to be internally consistent (0 orphans), but that is not guaranteed
   at other limits — a deep reply could arrive without its parent. **Validate
   `parsedParentId` resolution on every ingest and drop or flag orphans.**
2. **`postTitle` / `postCommentsCount` are absent** despite the README. Join on
   `postId` yourself.

**Content note:** 15/160 comments (9.4%) contained RCM/reimbursement language.
The substantive ones were real professional discussion —
*"Some Insurance companies are reimbursing independent CRNAs 85 cents in the
dollar"* — but about scope-of-practice economics, not practice RCM operations.
Comment *mechanics* are proven; comment *value for our use case* is not yet,
because the parent posts were selected by comment volume rather than by RCM
relevance.

---

## 30-Post Data Quality Results

**Sample:** the first 3 posts per search term, in returned (relevance) order,
across all 10 keywords = **27 posts** (two niche keywords returned only 2 and 1
results). Reproducible id list saved to
`problem-intelligence/reddit/data/raw/validation/sample30_ids.json`.

### Classification

| Class | Count | % |
|---|---|---|
| **A** — clearly relevant to pain-management RCM | **1** | 3.7% |
| **B** — healthcare/insurance, not clearly pain-management practice RCM | **9** | 33.3% |
| **C** — not relevant | **10** | 37.0% |
| **D** — spam / low quality / duplicate | **7** | 25.9% |
| **E** — first-person *practice-side* operational problem evidence | **0** | **0.0%** |

### The single A

`t3_1v19e6s` · r/anesthesiology · 2026-07-20 · score 32 · 20 comments

> "The 50% same-day E/M and procedure cut probably will not affect routine OR
> anesthesia... **It could be a big deal for interventional pain practices that
> bill an E/M visit and procedure on the same day.**"

Genuinely practice-side, genuinely pain-relevant, cites CMS and H.R. 6160. But
it is **policy commentary**, not a problem the author's practice is currently
experiencing — the same Phase 2 / Deliverable A distinction the roadmap already
draws about the LinkedIn sample.

### Why E = 0 — the finding that should change the collection strategy

**Unrestricted keyword search selects for patients, not practices.** Across all
252 R1 posts:

| Community type | Posts | % |
|---|---|---|
| Clinician / professional subreddits | 17 | **6.7%** |
| Patient / condition subreddits | 54 | 21.4% |
| Other / unrelated | 181 | 71.8% |
| **Distinct subreddits** | **157** | — |

157 distinct subreddits for 252 posts is extreme fragmentation. The top
communities were r/ChronicPain (26), r/backpain (8), r/WorkersComp (7),
r/VAClaims (7) — all patient- or claimant-side. Clear off-topic noise included
r/TLRY (a cannabis stock ticker), r/MoneyDiariesACTIVE, r/HRMJobs, r/DWPhelp
(UK benefits), r/AIO and r/Damnthatsinteresting.

**Compare with Phase 1's community-anchored approach**, which pulled recent
posts from r/CodingandBilling and r/MedicalCoding and measured **36.7% problem
evidence, 20/22 first-person**. Same source, same domain, opposite result.

> **Conclusion: anchor on professional communities and filter by keyword.
> Do not search Reddit globally by keyword.** Global keyword search is how you
> find patients discussing their own denials; community anchoring is how you
> find billers discussing their practice's.

### The spam trap this experiment exposed

Two posts in the sample read exactly like practice-side voices:

> "**As a medical biller**, I frequently deal with the complexities of billing
> for interventional pain management procedures like nerve blocks, epidural
> injections, and spinal cord stimulators..." (`t3_1nxce6h`)

> "**As someone working in medical billing for pain management practices**,
> I've seen firsthand how denials can significantly affect cash flow..."
> (`t3_1o0qtk3`)

Both are from the same account — **`transcuremarketing`** (`t2_lcqmsl5k`) — an
RCM vendor posting lead-generation content into r/ChronicPain, a *patient*
subreddit. Scores of 0 and 1.

**This is a competitor's marketing, and it is the highest-precision match our
best queries returned.** Any naive classifier keying on "as a medical biller"
would have scored both as prime evidence. Mitigations, all cheap:

- Blocklist authors whose posts are dominated by promotional content.
- Treat a professional-voice post in a *patient* subreddit as a strong spam prior.
- Weight by `score` and `commentsCount` — genuine problem posts attract replies.

### Duplicates

| Metric | Result |
|---|---|
| Exact-ID duplicates within R1 | **0** (252 unique ids from 252 items) |
| Posts surfaced by more than one query | **0** (the Actor dedupes across keywords within a run) |
| **Near-duplicate clusters** (same body, different post ids) | **9 clusters, 22 items = 8.7% of the pull** |

Cross-posting is the mechanism. Worked examples:

- `BillerSince2021` posted an identical job-seeker ad to **5** subreddits
  (`r/VirtualAssistantPH`, `r/JobsPhilippines`, `r/VAjobsPH`, `r/remoteworking`,
  own profile) — 5 distinct `t3_` ids, one piece of content.
- `FunctUp` cross-posted the same essay to **4** subreddits.
- Patient posts routinely appear in pairs (`r/ChronicPain` + `r/backpain`,
  `r/DiagnoseMe` + `r/AskDocs`).

**`(source, source_item_id)` is necessary but not sufficient.** Add a normalised
body hash. Without it, a cross-posted item inflates every trend count by its
crosspost factor.

### Stability

`t3_1cuxw6d` appeared in both R1 and R3, collected ~20 minutes apart:

| Field | R1 | R3 | Stable? |
|---|---|---|---|
| `id` | `t3_1cuxw6d` | `t3_1cuxw6d` | ✅ |
| `postUrl` | identical | identical | ✅ |
| `createdAt` | identical | identical | ✅ |
| `score` | 430 | 432 | ❌ — live counter, as expected |

Identifiers and timestamps are stable; engagement is a snapshot. Store
engagement with `crawledAt` and treat it as time-series, never as a fixed
attribute.

### Historical test (R3)

| Question | Answer |
|---|---|
| Does `postedAfter` / `postedBefore` work? | **Yes, precisely.** 20/20 returned posts fell inside 2024-01-01 → 2024-06-30. **Zero** out-of-window leakage. Actual span returned: 2024-02-02 → 2024-06-30. |
| Today / last 7 / last 30 days? | Yes — R1 returned 130 posts from 2026 and `searchTime` accepts `hour|day|week|month|year|all`. |
| Older content? | **Yes.** R1 returned posts from **2013, 2015, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024** with `searchTime: "all"`. Distribution: 2026: 130 · 2025: 73 · 2024: 13 · 2023: 9 · ≤2022: 27. |
| Is coverage complete? | **Unknown — and we cannot claim it is.** We did not establish ground truth for how many matching posts exist in that window. The Actor's own input documentation states: *"Reddit caps each listing at ~1,000 posts, so a window behind a very high-volume query may be only partly reachable."* |
| Does sorting work? | `searchSort: "relevance"` returned plausibly relevance-ordered results. Other sorts untested. Note `postedAfter` **overrides** sort — the Actor's docs state it forces `sort=new` and ignores `searchTime`. |

**Honest summary:** date filtering is accurate and historical reach extends at
least to 2013. **Completeness is unproven.** Treat the Actor as able to *sample*
history, not to *exhaust* it, until a ground-truth test is run.

---

## Missing Fields

| Field | Status | Workaround |
|---|---|---|
| `source` | Never returned | Collector constant |
| `author_profile_url` | Never returned | Construct from `authorName` |
| `organization_name` / `organization_url` / `location` | Never returned | NLP over text; low yield (see below) |
| `postTitle` / `postCommentsCount` on comments | **Documented but absent** | Join on `postId` |
| A prefixed comment id | Comments return `id` unprefixed | Prepend `t1_` yourself |
| A cursor for pagination | Not exposed | Actor paginates internally; you control volume with `maxPostsCount` |
| Correct `authorId` on comments | **Present but wrong** | Use `authorFullname` |

---

## Derived Fields

| Field | Derivation | Feasibility on this data |
|---|---|---|
| `source` | constant | Trivial |
| `author_profile_url` | `https://www.reddit.com/user/{authorName}` | Trivial |
| `author_role` | `authorFlairText` where present, else NLP over text | **Good.** Flair on 52.5% of comments in clinician subs, and clean (`MD`, `Anesthesiologist`, `RN`, `CA-3`, `Emergency Medicine Physician`). Phase 1 separately measured 56.7% role-identifiable from text. |
| `location` | NLP over text | Occasional — `"[PA]"`, `"Location: Florida"`, `"Wisconsin WC"` appeared in sampled titles/bodies |
| `procedure_tags` | NLP + CPT dictionary | Good where present — sampled posts named Intracept, radiofrequency ablation, epidural injections, spinal cord stimulators, nerve blocks |
| `payer_tags` | NLP + payer dictionary | Good — `BCBS federal`, `Medicare`, `workers' comp` carriers appeared |
| `denial_reason_tags` | NLP | Moderate — patient posts describe denials narratively ("did not feel that this procedure was beneficial"), rarely by CARC code |
| `organization_name` / `organization_url` | NLP | **Very low yield.** See next section |

---

## Intelligence Fields

**These are OUR classifications. Reddit and the Actor supply none of them.**
Three worked examples using real retrieved posts.

### Example 1 — `t3_1v19e6s` · r/anesthesiology · 2026-07-20

> **SOURCE (Actor):** `title` = "What does the proposed 2027 Medicare rule mean
> for anesthesiology?" · `score` = 32 · `commentsCount` = 20 ·
> `postUrl` = `https://www.reddit.com/r/anesthesiology/comments/1v19e6s/...`
>
> **Excerpt:** *"The 50% same-day E/M and procedure cut... could be a big deal
> for interventional pain practices that bill an E/M visit and procedure on the
> same day."*

```
rcm_relevant             = true
problem_evidence         = false      # anticipated policy impact, not a live problem
first_person             = false      # "many practices", not "my practice"
problem_category         = "Reimbursement & Underpayment"
procedure_tags           = ["E/M same-day with procedure"]
payer_tags               = ["Medicare"]
denial_reason_tags       = []
pain_management_relevant = true       # explicitly names interventional pain practices
seeking_level            = "L0"       # describing/discussing, not seeking
evidence_quote           = "It could be a big deal for interventional pain practices
                            that bill an E/M visit and procedure on the same day."
classification_reason    = "Clinician-authored analysis of CY2027 MPFS proposed rule,
                            explicitly scoping the same-day E/M+procedure reduction to
                            interventional pain practices. Forward-looking, so no
                            problem_evidence."
classification_version   = "v0-manual-2026-09-21"
```

### Example 2 — `t3_cecrqb` · r/HealthInsurance · 2019-07-17

> **SOURCE:** `title` = "Disputing Insurance claim denial" · `score` = 2 ·
> `commentsCount` = 7
>
> **Excerpt:** *"I recently visited a pain clinic, where a radiofrequency
> ablation was done... I got a notice, after the fact, that my insurance did not
> feel that this procedure was beneficial, and therefore, would not cover it,
> leaving me with close to a $1000 bill."*

```
rcm_relevant             = true
problem_evidence         = true
first_person             = true       # but PATIENT-side, not practice-side
author_perspective       = "patient"  # ← field our schema currently lacks
problem_category         = "Denials & Appeals"
procedure_tags           = ["radiofrequency ablation"]
payer_tags               = ["BCBS Federal"]
denial_reason_tags       = ["not medically beneficial / medical necessity"]
pain_management_relevant = true
seeking_level            = "L2"
evidence_quote           = "my insurance did not feel that this procedure was
                            beneficial, and therefore, would not cover it"
classification_reason    = "Concrete RFA denial on medical-necessity grounds with a
                            named payer, from the PATIENT. Evidence that the denial
                            pattern exists; NOT evidence about a practice's operations."
classification_version   = "v0-manual-2026-09-21"
```

**This example is why the schema needs an `author_perspective` field.** Without
it, patient denial posts and practice denial posts collapse into the same
`problem_evidence = true` bucket, and the CEO dashboard will report patient
complaints as practice problems. **Strongly recommend adding
`author_perspective ∈ {practice_staff, clinician, patient, vendor, unknown}`
before Phase 2 freezes the taxonomy.**

### Example 3 — `t3_1s52isg` · r/PainManagement · 2026-03-27

> **Excerpt:** *"all the insurance companies are requiring prior authorizations
> for everything to do with pain medications... some doctors offices have
> started charging for submitting a PA."*

```
rcm_relevant             = true
problem_evidence         = true
first_person             = true
author_perspective       = "patient"
problem_category         = "Authorization & Pre-Certification"
procedure_tags           = []
payer_tags               = []         # "all the insurance companies" — not specific
denial_reason_tags       = []
pain_management_relevant = true
seeking_level            = "L0"
evidence_quote           = "some doctors offices have started charging for
                            submitting a PA"
classification_reason    = "Patient-observed market signal: rising PA burden in pain
                            management, and practices monetising PA submission. A
                            second-hand observation ABOUT practice behaviour, useful
                            as corroboration, not as practice problem evidence."
classification_version   = "v0-manual-2026-09-21"
```

---

## Technical Limitations

| # | Limitation | Severity | Mitigation |
|---|---|---|---|
| 1 | **`maxPostsCount` applies per search term, not per run.** Requested 36, got 252. | **High (cost)** | Budget as `keywords × maxPostsCount`; set an Apify per-run charge limit. |
| 2 | **`authorId` on comments is the comment's own fullname**, not the author's (160/160). | **High (correctness)** | Map `authorFullname` for comments. |
| 3 | `postTitle` / `postCommentsCount` documented but absent on comments. | Medium | Join on `postId`. |
| 4 | **Field names differ between posts and comments** (`createdAt` vs `commentCreatedAt`, `postUrl` vs `url`, `communityName` vs `subredditName`). | Medium | Normalisation layer keyed on `dataType`. |
| 5 | `contentUrl` is the *external* link on 39/252 posts. | Medium | Always use `postUrl` for evidence links. |
| 6 | **`withinCommunity` accepts only ONE subreddit.** | Medium | One run per subreddit, or build search `startUrls`. |
| 7 | Comment truncation is by count, not by tree. | Medium | Validate `parsedParentId` resolution on ingest; flag orphans. |
| 8 | No pagination cursor exposed. | Low | Actor handles it; volume controlled by `maxPostsCount`. |
| 9 | Engagement fields (`engagementTotal`, `scorePerHour`) are **Actor-computed**, not Reddit values. | Low | Recompute from `score` / `commentsCount` / `ageHours` if auditability matters. |
| 10 | **Requires `RESIDENTIAL` proxies by default.** | Low technically, **high as a signal** | The maintainer's own 2026-08-29 note says *"Reddit changes now require costly residential proxies."* Evidence of active enforcement — see the closing section. |
| 11 | Historical **completeness** unproven; ~1,000-post listing cap acknowledged by the Actor's own docs. | Medium | Treat as sampling, not exhaustion. |
| 12 | Actor README overstates field counts (38 actual vs 41 claimed for comments). | Low | Trust output, not docs. |

---

## What We Can Build From This Data

1. **A complete canonical `posts` record.** Every Group-A field is available or
   trivially derivable. Nothing in our source schema is blocked.
2. **Full comment threads with correct parentage.** 0 orphans out of 106
   replies, depths 0–5. Post → comment → reply reconstruction is a single pass.
3. **Evidence links that open for the CEO.** `postUrl` and comment `url` are
   canonical Reddit permalinks, verified stable across runs.
4. **Time-series trend analysis.** ISO-8601 UTC timestamps, precise date
   windowing, and historical reach to at least 2013.
5. **Deletion-compliance machinery.** `authorId` (`t2_`), `removedByCategory`,
   `isRobotIndexable`, `crawledAt`, `edited`/`editedAt` give you every hook you
   need — provided you fix the comment `authorId` mapping.
6. **Role segmentation without inference**, partly from `authorFlairText`
   (52.5% of comments in clinician subs carry a clean role label).
7. **Query-precision measurement**, via `searchTerm` provenance.
8. **Daily collection.** Runs completed in ~80s (R1), ~20s (R2), ~15s (R3). A
   daily community-anchored collector is well within reach at a few dollars a
   month.

## What We Cannot Reliably Build From This Data

1. **A practice-problem feed from global keyword search.** 0/27 first-person
   practice-side problem evidence; 6.7% of 252 posts from professional
   communities. The method, not the source, is what failed.
2. **Named-prospect identification.** See below — 0/27.
3. **Any claim of complete historical coverage.** Untested against ground truth.
4. **Trend counts without near-duplicate handling.** 8.7% of the pull were
   cross-posted duplicates with distinct ids.
5. **A patient/practice distinction using the current schema.** `problem_evidence`
   alone conflates them. Needs `author_perspective`.
6. **A spam-resistant classifier without an author-level signal.** The two
   highest-precision "practice voice" matches were one vendor's marketing.

---

## Organization / Author Information

**Question asked:** does the Reddit source itself provide enough *public*
information to populate organization/role/location when a user *voluntarily*
identifies themselves?

**Answer: role — partially yes. Organization — effectively no.**

| Field | Structured Actor field? | Volunteered in text? | Verdict |
|---|---|---|---|
| `author_role` | **Yes, partially** — `authorFlairText` (14.7% posts, 52.5% comments) | Frequently ("I'm in anesthesiology", "As a medical biller") | **Usable.** Best field on this list. |
| `organization_name` | No | **0 of 27** sampled posts named the author's own employer | **Not usable from Reddit.** |
| `organization_url` | No | 0 of 27 | **Not usable.** |
| `location` | No | Occasionally — `"[PA]"`, `"Location: Florida"`, `"Wisconsin WC"` | Marginal; state-level at best. |
| `practice identity` | No | 0 of 27 | **Not usable.** |

This independently reproduces Phase 1's measurement (1/60 = 1.7%, and that one
was an offshore RCM vendor, not a prospect). **Two samples, two methods, same
answer: Reddit does not support Deliverable B.**

**The distinction the brief asks us to hold, applied:**

- ✅ *"I'm in anesthesiology and have been following the reimbursement side"* —
  role volunteered by the author. Store `author_role = "anesthesiologist"`.
- ✅ `authorFlairText = "Anesthesiologist"` — the community verified it. Store it.
- ❌ *"my clinic keeps getting denied"* — **do not infer the clinic.** Leave
  `organization_name = null`.
- ❌ No external lookup was performed against any username in this experiment,
  and none should ever be.

### A privacy finding that needs a design decision

`authorFlairText` is dual-natured. In **clinician** subreddits it is a job title
(`MD`, `Anesthesiologist`, `RN`, `CA-3`, `Emergency Medicine Physician`).
In **patient** subreddits the same field carries **self-declared medical
conditions**:

```
"Lupus/Cauda Equina/ 7+ disc bulges/ torn knee/ADHD/ChronicNausea"
"8 trigeminal neuralgia"
"Spine and lasik surgery damaged, Sjogrens"
"hEDS"
"33F|Dx2019|RRMS|Ocrevus|OH"
```

That last one carries sex, age, diagnosis year, condition, drug and state on one
line. Reddit's Responsible Builder Policy prohibits processing data "to derive
or infer potentially sensitive characteristics about Reddit users (e.g.,
**health**…)".

**Recommendation:** store `authorFlairText` **only** for an allowlist of
professional subreddits, and drop it entirely for patient communities. This is
cheap to implement, costs us nothing we want, and removes the clearest
health-data exposure this experiment surfaced. The same logic argues for
excluding patient subreddits from collection altogether — which the data-quality
finding independently recommends anyway.

---

## Final Technical Verdict

| # | Question | Answer |
|---|---|---|
| 1 | Can we technically retrieve useful Reddit data through Apify? | **Yes.** 436 items, 3 runs, $0.67, all SUCCEEDED. |
| 2 | Does the data contain the minimum fields our system needs? | **Yes.** Every Group-A field is Direct or trivially Derived. |
| 3 | Which required source fields are available? | `source_item_id`, `url`, `title`, `text`, `author_id`, `author_name`, `created_at`, `collected_at`, `engagement`, `parent_id`/`conversation_id`, `media_type`, `raw_data`, `source_metadata` — **13 of 19 direct**; `author_role` partial. |
| 4 | Which important fields are missing? | `source`, `author_profile_url` (both trivially derived); `organization_name`, `organization_url`, `location` (not Reddit fields, and near-zero yield in text). |
| 5 | Which must be derived? | All Group-C intelligence fields; all Group-B enriched fields except the `authorFlairText` portion of `author_role`. |
| 6 | Can comments/threads be captured? | **Yes, completely.** 0 orphan replies out of 106; depths 0–5; every `postId` resolves. |
| 7 | Can we preserve original evidence URLs? | **Yes.** `postUrl` / comment `url` are canonical permalinks, stable across runs. |
| 8 | Can we perform daily collection? | **Yes technically.** Runs took 15–80 s. Cost a few dollars/month at community-anchored volumes. *Authorization is a separate, open question.* |
| 9 | Enough historical data for initial trends? | **Yes for sampling** — reach confirmed to 2013, date windows exact. **Completeness unproven.** |
| 10 | Is the content relevant enough? | **Not via global keyword search: 1/27 class A, 0/27 practice-side problem evidence.** Phase 1's community-anchored method gave 36.7% on the same source. **Change the method, not the source.** |
| 11 | How much noise? | **High on this method.** 62.9% class C+D. 93.3% of 252 posts from non-professional communities. 8.7% near-duplicates. One competitor's marketing was the top "practice voice" match. |
| 12 | What limitations did the Actor introduce? | 12, listed above. Two are High: `maxPostsCount` is per-keyword (7× cost overrun), and comment `authorId` is wrong (breaks deletion compliance silently). |

### Recommended next experiment

Re-run with the **method Phase 1 validated**, now that the Actor is proven:

```json
{
  "subredditUrls": ["CodingandBilling", "MedicalCoding", "Medicalbillingandcoding",
                    "healthIT", "PrivatePracticeDocs", "medicine"],
  "crawlCommentsPerPost": true,
  "maxCommentsPerPost": 30,
  "maxPostsCount": 40,
  "postedAfter": "<T-90 days>",
  "proxy": {"useApifyProxy": true, "apifyProxyGroups": ["RESIDENTIAL"]}
}
```

Then apply the pain-management filter **to the text**, not to the query. This
tests the one question both Phase 1 and this experiment left open: whether
pain-management specificity survives community anchoring, or whether the product
scope must widen to RCM generally.

Budget as `6 subreddits × 40 posts × (1 + 30 comments) ≈ 7,440 results ≈ $11`.

---

## Questions Still Requiring Official Reddit Confirmation

Unchanged by this experiment, and **not** answered by the fact that retrieval
worked:

1. Is an internal, non-redistributed market-intelligence dashboard built by an
   RCM services company classified as **commercial use**? (Reddit's published
   definition says use "by or on behalf of a business" is commercial.)
2. Given Reddit's 2026-08-05 statement that it will "gradually restrict new
   requests," is new commercial Data API access available at all?
3. What **retention period** is permitted? Reddit's guidance is to purge stored
   content within **48 hours**; a trend product needs months.
4. May derived, non-content **aggregate counts** persist beyond that window?
5. Does classifying retrieved content with a **frozen** LLM (inference only, no
   training) fall inside the model-training prohibition?
6. What are the fees and the review timeline?

**And one this experiment newly sharpens.** The Actor requires `RESIDENTIAL`
proxies, and its maintainer states Reddit's recent changes made that necessary.
Reddit's Responsible Builder Policy prohibits circumventing access limits and
masking how or why you access Reddit data. **This experiment demonstrates
technical feasibility and simultaneously demonstrates that the technique works
by routing around Reddit's controls.** Those are both findings, and the second
should be recorded in the decision log rather than left implicit — it is the
reason Apify cannot quietly become the production route.

---

## Reproducibility

```bash
# Requires APIFY_TOKEN in linkedin/.env (existing repo credential)
python problem-intelligence/reddit/apify_field_validation.py r1   # 252 posts,  $0.388
python problem-intelligence/reddit/apify_field_validation.py r2   # 160 comments, $0.266
python problem-intelligence/reddit/apify_field_validation.py r3   # 20 posts,   $0.0175
```

| Artifact | Path |
|---|---|
| Runner + verbatim inputs | `problem-intelligence/reddit/apify_field_validation.py` |
| R1 raw output + run meta | `problem-intelligence/reddit/data/raw/validation/r1_search_posts.json` |
| R2 raw output + run meta | `problem-intelligence/reddit/data/raw/validation/r2_comments.json` |
| R3 raw output + run meta | `problem-intelligence/reddit/data/raw/validation/r3_historical.json` |
| 27-post sample id list | `problem-intelligence/reddit/data/raw/validation/sample30_ids.json` |

Each output file stores the exact `input` payload, Apify `run_id`, `status`,
`stats` and `usageTotalUsd` alongside the untouched items.

**Actor pinned for reproduction:** `harshmaur/reddit-scraper-pro`, actor id
`3XedXIRBcjfKrnsDJ`, build `0.0.511` (2026-09-21). The Actor is actively
developed — later builds may return different fields, so re-verify the schema
before trusting a future run.
