# REDDIT — DATA SOURCE INVESTIGATION

**Prepared for:** PainMed-PA Social Listening / Practice Problem Intelligence (SLD)
**Investigation date:** 2026-09-21 · **Investigator:** independent verification pass
**Scope:** Reddit only. Apify examined solely as a technical-feasibility comparison.

**How to read the status labels.** Throughout this report three things are kept
separate and never merged:

| Label | Means |
|---|---|
| **Technically possible** | The data can be retrieved by some mechanism. |
| **Officially authorized** | Reddit's current documentation permits *this* access route. |
| **Commercially permitted** | Reddit's current terms permit *PainMed-PA specifically* to do it. |

Every load-bearing claim carries an official source URL and the date that source
itself reports. All pages were fetched on 2026-09-21.

---

## 1. Executive Summary

**Reddit remains the richest available source of RCM problem evidence, and the
route to using it legitimately is narrower in September 2026 than the roadmap
assumed.**

Five findings drive everything else.

1. **PainMed-PA's use is commercial by Reddit's own published definition.**
   Reddit defines commercial purposes as "any use of our services **by a
   business or on behalf of a business** or as part of a monetized product or
   service." An internal sales-and-service-design dashboard built by an RCM
   company falls inside that definition even if nothing is resold. Commercial use
   "requires our permission, and we'll require a contract."
   ([Reddit Help, updated 2026-05-28](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data))

2. **Approval is now required *before* any API access, not only commercial
   access.** The Responsible Builder Policy states: "You must request access and
   get explicit approval before accessing any Reddit data through our API."
   There is no self-serve free tier you can use first and regularize later.
   ([Responsible Builder Policy, edited 2026-06-05](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy))

3. **Reddit announced on 2026-08-05 that it is restricting new API requests.**
   Verbatim: "we will continue supporting limited public API access, but we will
   **gradually restrict new requests** and require third-party apps to transition
   to and operate on Reddit's Developer Platform." PainMed-PA would be a new
   request arriving during that restriction.
   ([Reddit newsroom, 2026-08-05](https://redditinc.com/news/modernizing-reddits-infrastructure-and-moderation-tools))

4. **The unauthenticated `.json` route is closed.** Verified directly from this
   machine on 2026-09-21: `https://www.reddit.com/r/CodingandBilling/new.json`
   returns **HTTP 403** with both a descriptive and a browser user-agent, and
   `https://www.reddit.com/search.json` likewise; `old.reddit.com` returns a 302
   to login. This matches Reddit's own statement that "traffic not using OAuth or
   login credentials will be blocked."
   ([Reddit Data API Wiki, edited 2026-05-11](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki))

5. **Two capabilities the product design probably assumes do not exist in the
   official API.** There is **no comment search** — the search endpoint's `type`
   parameter accepts only `sr`, `link`, `user` — and **no date-range search**,
   only the coarse buckets `hour|day|week|month|year|all`.
   ([Reddit API reference](https://www.reddit.com/dev/api/#GET_search))

**What this means practically.** Reddit is technically excellent and
contractually gated. The gate is a written agreement PainMed-PA does not have
and cannot self-serve. The correct next action is **not** to create production
credentials — it is to submit the Data API enterprise request and obtain a
written answer, while continuing hand-labelling from ordinary browsing.

**One risk the existing roadmap does not name.** The Responsible Builder Policy
now carries a "Zero Tolerance for Privacy Violations" clause prohibiting
processing Reddit data "to derive or infer potentially sensitive characteristics
about Reddit users (e.g., **health**, political affiliation, sexual
orientation)" and prohibiting any attempt to "re-identify, de-anonymize, or
reverse engineer data about Redditors including by matching data with
off-platform identifiers." The planned `org_name` / `org_state` classification
fields and the named-prospect review queue sit directly against that clause.
See §7.4 — this needs a design decision, not merely a footnote.

---

## 2. Official Reddit API

| Item | Current finding | Official source | Status |
|---|---|---|---|
| Does an official API exist for this use case? | Yes — the **Reddit Data API**. It "allows approved developers the ability to access and modify Reddit data programmatically." Note the word *approved*. | [Reddit Help, upd. 2026-05-28](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) | CONFIRMED |
| Authentication mechanism | OAuth 2.0 bearer token. "Clients must authenticate with a registered OAuth token. We can and will freely throttle or block unidentified Data API users." | [Data API Wiki, ed. 2026-05-11](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) | CONFIRMED |
| Reddit account required? | Yes. Registration requires a personal Reddit account — "You'll need a human Reddit account to register." | [developers.reddit.com/app-registration](https://developers.reddit.com/app-registration) | CONFIRMED |
| Credentials issued | `client_id`, `client_secret` (confidential clients only), OAuth bearer token, and a compliant `User-Agent`. Bearer tokens expire after 1 hour. | [OAuth2 wiki](https://github.com/reddit-archive/reddit/wiki/OAuth2) (linked by Reddit; see caveat below) | CONFIRMED |
| Where to register | Two live surfaces: legacy app creation at `reddit.com/prefs/apps` (verified live 2026-09-21, redirects to login) and the newer flow at `developers.reddit.com/app-registration`. | [app-registration](https://developers.reddit.com/app-registration) | CONFIRMED |
| Access requirement, 2026 | **Explicit prior approval for all access.** "You must request access and get explicit approval before accessing any Reddit data through our API." | [Responsible Builder Policy, ed. 2026-06-05](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) | CONFIRMED |
| Commercial use | Permission + contract. Reddit's own examples include "services, research, or data access for fees," "subscription services," and any use "by a business or on behalf of a business." | [Reddit Help, upd. 2026-05-28](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) | CONFIRMED |
| Research use | **Closed to companies.** "The only official and authorized avenue for performing research using Reddit data is through the Reddit For Researchers (RFR) program." RFR requires accredited-university affiliation, institutional email, IRB approval and a faculty sponsor. PainMed-PA is not eligible. | [Reddit Help](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) · [RFR Program, ed. 2026-06-02](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program) | CONFIRMED |
| Social listening / monitoring | Not prohibited as a category. Reddit names "companies that help brands monitor trends associated with their brands" as a class of **data licensee** — i.e. a licensed activity, not a free-tier one. | [Public Content Policy](https://support.reddithelp.com/hc/en-us/articles/26410290525844-Public-Content-Policy) | CONFIRMED |
| AI / ML use | Prohibited without explicit consent. "You may not use content on Reddit as an input for any model training without explicit consent from Reddit. Commercial use of any model trained with Reddit data is prohibited without explicit approval." | [Reddit Help](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) | CONFIRMED |
| Separate agreement for commercial use? | Yes, explicitly. "If you are interested in using the Data APIs for commercial purposes … you will need to enter into a separate agreement with Reddit." | [Data API Terms §3.1, rev. 2026-07-20](https://redditinc.com/policies/data-api-terms) | CONFIRMED |
| Can PainMed-PA use it commercially? | **Only under a signed Reddit agreement.** Reddit states the requirement plainly; whether PainMed-PA obtains one is Reddit's decision and cannot be determined from documentation. | see §7 | REQUIRES VERIFICATION |

> **Caveat on the OAuth2 documentation.** Reddit's own Data API Wiki links the
> OAuth2 guide hosted on `github.com/reddit-archive/reddit`, a repository
> **archived by its owner on 2017-11-09**. Reddit prefixes its wiki with: "Some
> of the information in our legacy API documentation and support resources may be
> out of date. Always consult our Developer Terms and Data API Terms for rules of
> use." Treat OAuth mechanics as indicative and verify empirically; treat the
> terms pages as authoritative.

### 2.1 The 2026 direction of travel — read this before planning

Reddit's official newsroom post of **2026-08-05**, *Modernizing Reddit's
Infrastructure and Moderation Tools*, sets out four goals, two of which bear
directly on this project:

> "To achieve this, we will continue supporting limited public API access, but we
> will gradually restrict new requests and require third-party apps to transition
> to and operate on Reddit's Developer Platform."

> "In order to protect our platform, business, and users from abusive scraping
> and spamming, over time we plan to make changes involving Old Reddit … In the
> short term, we will continue to require users to be logged in to access it."

Alongside this, Reddit is running a **$1 Million App Migration Program**
(2026-03-31 → 2026-12-31) paying $1,000 bounties to move existing Data API apps
onto the Developer Platform ([official terms, created 2026-04-01](https://support.reddithelp.com/hc/en-us/articles/47822311698452-Reddit-Developer-Platform-App-Migration-Program-2026-Terms)).

**What this does and does not say.** It does **not** say the Data API is being
shut off. Several third-party blogs claim "Reddit's API is dead in 2026"; that
claim is **not supported by any official Reddit source** I could locate, and the
newsroom post contradicts it ("continue supporting limited public API access").
What it does say is that *new* requests will be progressively restricted.

Devvit is also not a substitute for our use case: it is a platform for apps that
*run on Reddit* for Reddit's users, not a mechanism for exporting data into an
external CEO dashboard.

**Planning consequence:** the window for obtaining new Data API access is
narrowing. If Reddit access matters to this product, the request should go in
now, and the product should be designed so it does not die on a "no."

---

## 3. Authentication

### 3.1 The mechanics

| Step | Requirement | Current finding | Source |
|---|---|---|---|
| 1. Where to go | App creation surface | `https://www.reddit.com/prefs/apps` (legacy, verified live) or `https://developers.reddit.com/app-registration` | [app-registration](https://developers.reddit.com/app-registration) |
| 2. Account | A **human** Reddit account | "You'll need a human Reddit account to register." Corporate acceptance is contemplated: §1.2 covers accepting "on behalf of your employer or another entity." | [app-registration](https://developers.reddit.com/app-registration) · [Data API Terms §1.2](https://redditinc.com/policies/data-api-terms) |
| 3. App type | One of three | **Web app** (server you control, keeps a secret) · **Installed app** (no secret) · **Script** (your own hardware, your account only). A server-side daily collector is a **web app** or **script**. | [OAuth2 wiki](https://github.com/reddit-archive/reddit/wiki/OAuth2) |
| 4. Information to enter | Name, description, redirect URI, plus identification | "In order to access the Data APIs, you are required to provide identification information (e.g., contact details). This information must be up to date and accurate at all times." | [Data API Terms §1.3](https://redditinc.com/policies/data-api-terms) |
| 5. Credentials generated | `client_id` + `client_secret` | Non-confidential (installed) clients receive no secret. | [OAuth2 wiki](https://github.com/reddit-archive/reddit/wiki/OAuth2) |
| 6. OAuth flow | For read-only collection: **`client_credentials`** (application-only, no user context) | POST `grant_type=client_credentials` to `https://www.reddit.com/api/v1/access_token` with HTTP Basic auth (`client_id` as user, `client_secret` as password). Returns a bearer token valid **1 hour**. | [OAuth2 wiki — Application Only OAuth](https://github.com/reddit-archive/reddit/wiki/OAuth2) |
| 7. Making a request | Bearer token against the OAuth host | `Authorization: bearer <TOKEN>`, sent to **`https://oauth.reddit.com`**, *not* `www.reddit.com`. | [OAuth2 wiki](https://github.com/reddit-archive/reddit/wiki/OAuth2) |
| 8. User-Agent | Mandatory, specific format | `<platform>:<app ID>:<version string> (by /u/<reddit username>)`. Reddit: "Many default User-Agents (like `Python/urllib` or `Java`) are drastically limited." | [Data API Wiki, ed. 2026-05-11](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) |
| 9. Rate-limit headers | Must be monitored | `X-Ratelimit-Used`, `X-Ratelimit-Remaining`, `X-Ratelimit-Reset`. | [Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) |

The read scope needed for this project is the single OAuth scope `read`.

### 3.2 What NOT to do — each of these is a written prohibition

- **Never mask or misrepresent your User-Agent or OAuth identity.** "You will not
  misrepresent or mask either the user agent or OAuth identity when using the
  Data APIs." ([Data API Terms §2.8](https://redditinc.com/policies/data-api-terms)) ·
  "NEVER lie about your User-Agent." ([Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki))
- **Never register more than one app for the same use case.** Explicitly named as
  masking: "registering multiple Apps for a single use case or substantially
  similar or overlapping use cases."
  ([Developer Terms §4.2, rev. 2026-03-24](https://redditinc.com/policies/developer-terms))
- **Never treat `robots.txt` as your permission.** "Our robots.txt is for search
  engines, not Data API users."
  ([Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki))
- **Never exceed or engineer around the rate limit.** Reddit "reserves the right
  to permanently block your access."
  ([Data API Terms §3.2](https://redditinc.com/policies/data-api-terms))
- **Never train or fine-tune a model on the content.**
  ([Data API Terms §2.4](https://redditinc.com/policies/data-api-terms))
- **Never retain data beyond the approved use case.** Listed as a prohibition:
  "use or retain any User Content … beyond your approved use case, and you must
  immediately delete any data not required for it."
  ([Data API Terms §3.2](https://redditinc.com/policies/data-api-terms))
- **Never put ads on a surface displaying Reddit content.** "You cannot display
  Reddit content and run advertisements within your app, website, or other
  services."
  ([Reddit Help](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data))

### 3.3 What must be confirmed BEFORE creating production credentials

Per the brief, no production credentials should be created for PainMed-PA until
these are settled. In priority order:

1. **Does Reddit classify this use as commercial?** On the published definition,
   almost certainly yes. Get it in writing rather than assume either way.
2. **Will Reddit grant access at all**, given the 2026-08-05 statement that new
   requests are being restricted? Not knowable from documentation.
3. **What retention is permitted?** Reddit "strongly recommend[s] routinely
   deleting any stored user data and content within 48 hours." A trend product
   needs multi-month retention. This is the largest technical/contractual
   collision in the whole investigation and must be raised explicitly in the
   request. (§7.3)
4. **Is LLM classification of retrieved content "model training"?** Reddit
   prohibits using content "as an input for any model training." Running a frozen
   model for *inference* is materially different from *training* one, but the
   wording is broad enough that the distinction should be confirmed rather than
   assumed. Our pipeline does inference only — say so explicitly in the request.
5. **Who at PainMed-PA can bind the company?** Data API Terms §1.2 requires the
   accepting person to warrant they have authority to bind the entity. That is a
   named-signatory decision, not an engineering one.
6. **Is the named-prospect review queue compatible with the re-identification
   prohibition?** See §7.4.

Until 1–3 are answered, the defensible position is: keep reading Reddit in an
ordinary browser and hand-label, exactly as Phase 1 did. That is ordinary web
browsing by a human, not Data API access.

---

## 4. Data Fields

**Important methodological caveat.** Reddit's current official documentation
(`reddit.com/dev/api`) documents **endpoints and request parameters**. It does
**not** publish a field-level response schema for `Link` or `Comment` objects.
Any field table therefore rests on observation, not on an official contract, and
Reddit may change response shapes at will (Developer Terms §3.4: "Reddit may
change, suspend, or discontinue any part of Developer Services at any time").

The "Observed" column below records what our own 320-item Apify sample in
`problem-intelligence/reddit/data/raw/` actually returned on 2026-09-20, which is
independent evidence but from a *different access route* than the official API.

| Field | Available? | Notes | Source |
|---|---|---|---|
| `source` | N/A — derived | Our own constant. | — |
| `source_item_id` | **AVAILABLE** | Reddit fullname, `t3_*` for posts, `t1_*` for comments. Observed as `id` in our sample. Stable and unique. | [Listings concept](https://www.reddit.com/dev/api/#listings) |
| `url` (permalink) | **AVAILABLE** | Canonical `reddit.com/r/<sub>/comments/<id>/<slug>/`. Observed. Reddit *requires* you link back: "providing a link back to the User Content on our Services." | [Developer Terms §5.2](https://redditinc.com/policies/developer-terms) |
| `title` | **AVAILABLE** (posts only) | Comments have no title. | observed |
| `text` / `body` | **PARTIALLY AVAILABLE** | `selftext` for text posts; **empty for link posts**. In our 60-post sample, **5 of 60 had empty bodies** (title-only). Removed/deleted content returns `[removed]` / `[deleted]`. | observed; `phase1_report.md` §Limitations |
| `author_id` | **RESTRICTED / PERMISSION DEPENDENT** | `t2_*` is returned by the API, but Reddit requires: "When a user account is deleted, you must delete all related user ID info (e.g., `t2_*`)." Storable only under active deletion propagation. | [Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) |
| `author_name` | **RESTRICTED / PERMISSION DEPENDENT** | Returned, and Reddit's attribution rule actually *requires* you "cite the applicable User's username." But on account deletion you "must also delete all references to the author-identifying information (i.e., the author ID, name, profile URL, avatar image URL, user flair…)." | [Developer Terms §5.2](https://redditinc.com/policies/developer-terms) · [Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) |
| `author_profile_url` | **DERIVED** (and restricted) | `reddit.com/user/<name>`; same deletion obligation. | as above |
| `subreddit` | **AVAILABLE** | Name and `t5_*` id. Observed as `communityName` / `parsedCommunityName`. | observed |
| Community information | **AVAILABLE** | `GET /r/<sub>/about` returns subscriber counts, description, created date. | [API reference](https://www.reddit.com/dev/api/#GET_r_{subreddit}_about) |
| `created_at` | **AVAILABLE** | `created_utc`, Unix epoch, UTC. (Our Apify sample returned ISO-8601 instead — a route difference to normalize.) | observed |
| `collected_at` | **DERIVED** | Our own clock. | — |
| `edited_at` | **AVAILABLE** | `edited` is `false` or an epoch timestamp. | observed via Apify (`edited`, `editedAt`) |
| `score` / upvotes | **AVAILABLE** | `score` plus `upvote_ratio`. Treat as approximate, not an audited counter, and never compare across platforms. | observed |
| `comment_count` | **AVAILABLE** | `num_comments`. Counts removed/deleted children, so it will exceed the number of comments you can actually fetch. | observed |
| Awards | **PARTIALLY AVAILABLE** | `total_awards_received` / `gilded` still appear in response shapes, but Reddit's awards product has changed repeatedly. **Verify empirically before relying on it; do not design a metric around it.** | UNKNOWN in official docs |
| `parent_id` | **AVAILABLE** (comments) | `t3_*` for a top-level comment, `t1_*` for a reply. | [GET /comments/article](https://www.reddit.com/dev/api/#GET_comments_article) |
| Conversation / thread ID | **AVAILABLE** (comments) | `link_id` — the parent post fullname. | as above |
| Media type | **AVAILABLE** | `is_self`, `is_video`, `is_gallery`, `post_hint`, `domain`. | observed (`contentType`, `postType`) |
| Media URL | **PARTIALLY AVAILABLE** | Present for image/video/gallery posts; absent for text posts. Our lite-actor sample returned `imageUrls: []` for all text posts. | observed |
| Raw metadata | **AVAILABLE, with a retention caveat** | The full JSON object can be stored — but every stored copy inherits the deletion obligations in §7.3. Storing `raw_json` forever is the most likely way to breach the terms by accident. | [Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) |

### 4.1 Comments specifically

All comment fields come from **one endpoint**:
`GET /r/<sub>/comments/<article>` — the comment tree for a single post
([API reference](https://www.reddit.com/dev/api/#GET_comments_article)).
Parameters: `article`, `comment`, `context` (0–8), `depth`, `limit`,
`sort` (`confidence|top|new|controversial|old|random|qa|live`), `threaded`,
`truncate` (0–50). Deep trees are truncated and require follow-up calls to
`/api/morechildren`.

| Comment field | Available? | Notes |
|---|---|---|
| Comment ID | **AVAILABLE** | `t1_*` |
| Comment text | **AVAILABLE** | `body`; `[removed]` / `[deleted]` for moderated or author-deleted comments |
| Author | **RESTRICTED / PERMISSION DEPENDENT** | Same deletion rules as posts |
| Created time | **AVAILABLE** | `created_utc` |
| Parent comment ID | **AVAILABLE** | `parent_id` (`t1_*` when a reply) |
| Parent post ID | **AVAILABLE** | `link_id` (`t3_*`) |
| Score | **AVAILABLE** | `score`; may be hidden on new comments (`score_hidden`) |
| Permalink | **AVAILABLE** | Direct link to the comment anchor |
| Thread / post ID | **AVAILABLE** | `link_id` |

**The limitation that matters most:** you cannot *search* comments through the
official API. The search endpoint's `type` parameter accepts only `sr`, `link`,
`user`. To get comments you must first identify a post, then fetch its tree —
one API call per post. Since the roadmap correctly identifies comments as often
*more* valuable than posts, this has a direct cost implication (§6.3).

---

## 5. Historical Data

| Requirement | Available? | Limitation | Source |
|---|---|---|---|
| A. New posts as created | **AVAILABLE** | Poll `GET /r/<sub>/new`. There is **no push, webhook or streaming endpoint** in the Data API; "streaming" in client libraries is polling underneath. | [API reference](https://www.reddit.com/dev/api/#GET_new) |
| B. Last 24 hours | **AVAILABLE** | `/new` with `limit=100`, or `search` with `t=day`. Comfortable for low-traffic subreddits. | [API reference](https://www.reddit.com/dev/api/#GET_search) |
| C. Last 7 days | **AVAILABLE** | `t=week`, or paginate `/new`. | as above |
| D. Last 30 days | **AVAILABLE** | `t=month`. For a busy subreddit you may hit listing depth before you hit 30 days. | as above |
| E. Older historical posts | **PARTIALLY AVAILABLE** | `t=year` / `t=all` with `sort=top` or `new`, paginated by `after`. Listings are depth-capped. **The exact cap is not publicly specified in the current official documentation** — it is widely observed at ~1,000 items per listing, but Reddit does not state a number, so treat it as "unknown, assume shallow, measure it." | [Listings concept](https://www.reddit.com/dev/api/#listings) |
| F. Historical comments | **PARTIALLY AVAILABLE** | Only via per-post tree fetches on posts you have already located. No comment search, no bulk comment export. | [API reference](https://www.reddit.com/dev/api/#GET_comments_article) |
| Date-range search | **NOT AVAILABLE** | The only time control is `t` ∈ `hour, day, week, month, year, all`. No arbitrary `from`/`to`. | [API reference](https://www.reddit.com/dev/api/#GET_search) |
| Subreddit-scoped search | **AVAILABLE** | `GET /r/<sub>/search?restrict_sr=true` | as above |
| Keyword search | **AVAILABLE** | `q`, max 512 characters | as above |
| Author search | **AVAILABLE** | `GET /user/<name>/submitted` and `/user/<name>/comments`, `sort` + `t`, `limit` max 100. **Use with extreme care** — see §7.4; systematically profiling an author's history is close to the re-identification prohibition. | [API reference](https://www.reddit.com/dev/api/#GET_user_{username}_{where}) |
| Comment search | **NOT AVAILABLE** | `type` accepts only `sr`, `link`, `user`. | as above |
| Pagination | **AVAILABLE** | Cursor-based via `after` / `before` fullnames plus `count`. "Listings do not use page numbers because their content changes so frequently." | [Listings concept](https://www.reddit.com/dev/api/#listings) |
| Sorting | **AVAILABLE** | Search: `relevance, hot, top, new, comments`. Listings: `hot, new, rising, top, controversial`. | [API reference](https://www.reddit.com/dev/api/#GET_search) |
| Bulk historical archive | **NOT AVAILABLE to PainMed-PA** | The one official bulk route is Reddit for Researchers via BigQuery Analytics Hub — academic, non-commercial, IRB-gated. Pushshift is not an official Reddit product and is not offered. | [RFR Program](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program) |

### 5.1 Can we build a reliable daily collector?

**Yes — technically, for forward collection, assuming access is granted.** The
shape is:

- Poll `GET /r/<sub>/new?limit=100` per target subreddit, once or twice daily.
- Page backwards with `after` until you reach an already-seen `t3_*` id.
- For each post passing a cheap keyword prefilter, fetch
  `GET /r/<sub>/comments/<id>` for the comment tree.
- Run the same keyword set through `GET /r/<sub>/search?restrict_sr=true&sort=new&t=week`
  as a safety net for posts the listing missed.

Five real limitations to design around:

1. **Backfill is weak and shallow.** Plan forward collection from day one and
   treat any backfill as a bonus. The roadmap already says this; it is correct.
2. **Deleted and edited content drifts.** Reddit requires you to remove content
   deleted on Reddit. That means a *re-check* pass, not just a collect pass —
   which is extra quota, and the 48-hour recommendation makes it a daily job.
3. **Comment collection is the expensive part.** One request per post. A day
   with 200 candidate posts is 200 extra calls.
4. **Listing recency is not guaranteed to be complete.** Our own Phase 1 run
   found r/CodingandBilling's newest retrievable post was 2026-08-17 when
   collected on 2026-09-20 — confirmed twice, via listing and via search. Whether
   the subreddit went quiet or the index stopped, **what you get is "the most
   recent *retrievable* posts," not "the most recent posts."** Instrument this:
   alert when a subreddit's newest item is older than N days.
5. **Anything pain-management-specific is volume-starved.** Phase 1 measured
   **1 pain-relevant post in 60** in these two subreddits. A daily collector will
   work fine for general RCM problem intelligence and will starve on a strict
   pain filter.

---

## 6. API Limits / Pricing

| Item | Current information | Source |
|---|---|---|
| Rate limit (free tier) | **100 queries per minute (QPM) per OAuth client id**, averaged over a **10-minute** window to allow bursting (i.e. ~1,000 requests per 10 minutes). | [Data API Wiki, ed. 2026-05-11](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) |
| Rate-limit observability | Response headers `X-Ratelimit-Used`, `X-Ratelimit-Remaining`, `X-Ratelimit-Reset`. | as above |
| Unauthenticated traffic | "Traffic not using OAuth or login credentials will be blocked, and the default rate limit will not apply." Independently verified: HTTP 403, 2026-09-21. | as above |
| Items per request | Listings: `limit` default 25, **maximum 100**. | [API reference](https://www.reddit.com/dev/api/#GET_search) |
| Pagination depth cap | **Not publicly specified in the current official documentation.** | — |
| Reddit's right to change limits | "Reddit may set and enforce limits on your use of the Data APIs … in our sole discretion." | [Data API Terms §2.9](https://redditinc.com/policies/data-api-terms) |
| Published price list | **Not publicly specified in the current official documentation.** Reddit states only: "Reddit reserves the right to charge fees for future use or access to the Data APIs, rates to be determined at Reddit's sole discretion." | [Data API Terms §3.1](https://redditinc.com/policies/data-api-terms) |
| Paid vs free | "Reddit offers both free and paid access… Bulk exporting of Reddit data will be significantly limited by default, however, and select developers who require broader access to Reddit data may be charged fees to lift those limits." | [Reddit Help, upd. 2026-05-28](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) |
| Research tier | Free, but academic-only and not available to PainMed-PA. "Access to the RFR dataset is provided free of charge for approved, non-commercial academic projects." | [RFR Program](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program) |

### 6.1 On the "$0.24 per 1,000 calls" figure

This number circulates widely in 2026 write-ups, usually alongside "~$12,000/month
for ~50M calls." **I could not find it in any current official Reddit source.**
It traces to Reddit's 2023 pricing announcements and is repeated by commercial
blogs that have an interest in selling alternatives.

Per the brief's rule, the correct statement is:

> **Pricing is not publicly specified in the current official documentation.**
> Reddit's only current public statement is that rates are "to be determined at
> Reddit's sole discretion." Any figure you see quoted is third-party and
> unverified. PainMed-PA will receive a quote only after submitting the request.

Do not put a Reddit line-item in a budget until Reddit has quoted one.

### 6.2 What 100 QPM actually buys us

At 100 QPM sustained you have ~144,000 requests/day — far more than this project
needs. Realistic daily shape for 6 target subreddits:

| Work | Requests/day |
|---|---|
| 6 subreddits × 2 pages of `/new` | 12 |
| 6 subreddits × 5 keyword searches | 30 |
| Comment trees for ~50 candidate posts | 50 |
| Deletion re-check on ~500 stored items (`/api/info`, 100 ids/call) | 5 |
| **Total** | **≈ 100 requests/day** |

**The free rate limit is not the constraint. Authorization is.** That is the
single most important sentence in this section: we would use roughly 0.07% of
the free quota, and still need a commercial agreement.

### 6.3 Where quota does bite

If the taxonomy widens to 20+ subreddits *and* full comment trees on every post,
comment fetching dominates — 1 call per post, plus `/api/morechildren` on deep
threads. Even then this stays within 100 QPM. Budget engineering effort for
deletion re-checks, not for throughput.

---

## 7. Commercial Use / Terms

This section answers the brief's ten questions and keeps technical access,
commercial permission, separate agreements and AI restrictions apart.

### 7.1 The four-way distinction

| Layer | Status for PainMed-PA | Evidence |
|---|---|---|
| **Technical access** | Possible. OAuth + documented endpoints return exactly the data we need. | §2–§5 |
| **Officially authorized access route** | **Requires prior approval for any use.** "You must request access and get explicit approval before accessing any Reddit data through our API." | [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) |
| **Commercial permission** | **Not held.** Reddit's definition of commercial use covers use "by a business or on behalf of a business." | [Reddit Help](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) |
| **Separate agreement** | **Required, and Reddit says so twice.** "You will need to enter into a separate agreement with Reddit" (Data API Terms §3.1, Developer Terms §4.1). "We'll require a contract" (Help Centre). | [Data API Terms](https://redditinc.com/policies/data-api-terms) · [Developer Terms](https://redditinc.com/policies/developer-terms) |

Developer Terms §4.1 is the clearest single statement. Unless approved in
writing, you will not:

> "access or use any of the Reddit Services and Data **by or on behalf of a
> business** or as part of a service or product that is monetized; or sell,
> lease, sublicense, monetize, or otherwise obtain or derive revenues of any kind
> from any portion of Reddit Services and Data, whether directly or indirectly,
> **including from any data derived from the foregoing**."

The words "or on behalf of a business" and "including from any data derived"
are what make the common "but it's only internal, we're not reselling it"
argument unreliable here. This is a documentation finding, not legal advice —
PainMed-PA's counsel should read §4.1 directly.

### 7.2 The ten questions, answered

1. **What data can the API provide?** Public posts, comments, subreddit
   metadata, public user profiles, votes/engagement counts. Reddit "does not
   license or make publicly available private data about Redditors," explicitly
   excluding private messages, mod mail, deleted posts and comments, non-public
   account info, and content in quarantined or private communities.
   ([Public Content Policy](https://support.reddithelp.com/hc/en-us/articles/26410290525844-Public-Content-Policy))

2. **Restrictions on storing content?** Yes, and they are the sharp edge. See
   §7.3.

3. **Restrictions on displaying content?** Yes. The licence permits copying and
   displaying User Content "solely as necessary to develop, deploy, distribute,
   and run your App to your App Users," and "You may not modify the User Content
   except to format it for such display." Attribution is mandatory: link back to
   the content, cite the username, and indicate it is from Reddit. **No
   advertising** may run on a surface displaying Reddit content.
   ([Data API Terms §2.4](https://redditinc.com/policies/data-api-terms) ·
   [Developer Terms §5.2](https://redditinc.com/policies/developer-terms) ·
   [Reddit Help](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data))
   *For us:* a CEO dashboard quoting a post with its permalink and username is
   the shape Reddit describes. Exporting quotes into a marketing deck or a sales
   email is redistribution and is not covered.

4. **Restrictions on redistributing?** Yes. The licence is
   "non-transferable, non-sublicensable." You must not "sell, lease, or
   sublicense … or derive revenues from the use or provision of the Data APIs …
   unless there is express written approval from Reddit."
   ([Data API Terms §2.1, §3.2](https://redditinc.com/policies/data-api-terms))

5. **Deletion / update requirements?** Yes, and they are strict:
   - "You must remove any user content in your possession that has been deleted
     from Reddit."
   - On post/comment deletion: "you must delete all content related to the post
     and/or comment (e.g., title, body, embedded URLs, etc.)."
   - On account deletion: delete the `t2_*` id "and all references to the
     author-identifying information (i.e., the author ID, name, profile URL,
     avatar image URL, user flair, etc.)."
   - "To best comply with this policy, we strongly recommend routinely deleting
     any stored user data and content **within 48 hours**."
   - "Retention of content and data that has been deleted—even if disassociated,
     de-identified or anonymized—is a violation of our terms and policies."
   ([Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki))
   Developer Terms §6 adds: delete when retention "is no longer necessary for
   your App's stated and approved functionality," on Reddit's request, or on the
   user's request. On termination: "permanently delete all Reddit Licensed
   Materials in your control or possession."

6. **Restrictions on user information?** Yes, and this is the clause most likely
   to be overlooked. See §7.4.

7. **Restrictions on commercial use?** Yes — see §7.1.

8. **Restrictions on AI / ML / model training?** Yes, in three places:
   - "no other rights or licenses are granted or implied, including any right to
     use User Content for other purposes, such as for training a machine learning
     or AI model, without the express permission of rightsholders in the
     applicable User Content." ([Data API Terms §2.4](https://redditinc.com/policies/data-api-terms))
   - "You may not use content on Reddit as an input for any model training
     without explicit consent from Reddit. Commercial use of any model trained
     with Reddit data is prohibited without explicit approval."
     ([Reddit Help](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data))
   - On termination you must delete "any data or models that were derived from
     User Content." ([Data API Terms §6](https://redditinc.com/policies/data-api-terms))
   *For us:* classification by a frozen model is inference, not training, and is
   a different activity from what these clauses describe. But note the phrase
   "as an input for any model training" is broad, and Reddit does not define
   inference anywhere. Our design should: (a) never fine-tune on Reddit text,
   (b) never build an embedding index that functions as a derived corpus without
   asking, (c) state plainly in the access request that we run inference only.

9. **Restrictions on using Reddit data to build a product?** Yes — that is
   precisely what the commercial-agreement requirement governs. Reddit's own
   words: "If you're interested in using Reddit data to power, augment, or
   enhance your product or service for any commercial purposes, you'll need our
   permission, and we'll require a contract."
   ([Reddit Help](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data))

10. **Rate limits / pricing?** See §6. Limits: 100 QPM per OAuth client id.
    Pricing: not publicly specified.

### 7.3 The retention collision — the biggest design problem in this report

Reddit's guidance is to delete stored user data **within 48 hours**. The SLD is a
**trend product**: recurring problems, emerging problems, aggregated trends over
months. These pull in opposite directions.

There is a workable reconciliation, and it should be designed in now rather than
retrofitted:

- **Tier 1 — derived, non-content aggregates.** Counts by category, by month, by
  subreddit; payer and procedure mentions; no Reddit text, no usernames, no ids.
  This is what the CEO dashboard's trend lines should be built from. Note Reddit
  says retention of deleted content is a violation "even if disassociated,
  de-identified or anonymized" — that clause is about *content*, but it is broad
  enough that PainMed-PA's counsel should confirm aggregate counts are outside
  it before treating Tier 1 as permanently safe.
- **Tier 2 — content and identifiers.** Title, body, username, author id,
  permalink, raw JSON. Keep only while needed for the approved use case, subject
  to a **daily deletion re-check** against Reddit and a hard TTL.
- **Evidence quotes** are the hard case: the product needs them and they are
  Tier 2. Design so that a quote which disappears from Reddit disappears from the
  dashboard, and the surrounding trend line survives.

Whatever retention window PainMed-PA actually needs should be **stated in the
access request**, not assumed. This is a question Reddit can answer in a
contract, and cannot be answered by reading the free-tier documentation.

### 7.4 The privacy clause that bears on the named-prospect queue

The Responsible Builder Policy's "Zero Tolerance for Privacy Violations" section
states:

> "You are strictly prohibited from processing data to derive or infer
> potentially sensitive characteristics about Reddit users (e.g., health,
> political affiliation, sexual orientation). Furthermore, you must never attempt
> to re-identify, de-anonymize, or reverse engineer data about Redditors
> including by matching data with off-platform identifiers."

The Public Content Policy imposes parallel restrictions on licensees, who may not
"use public content to segment, target, or profile Redditors based on their
health…" or "perform background checks, extreme vetting, credit or risk insurance
analyses, individual profiling, psychographic segmentation…"

Read against the proposed schema:

| Our design element | Reading |
|---|---|
| `category`, `procedures`, `payers`, `denial_reasons` — attributes of the *problem described* | Low concern. These describe an operational situation at a practice, not a characteristic of the person posting. |
| `specialty`, `is_firsthand`, role inference | Low-to-moderate. Inferring "this author is a biller at a pain clinic" is an inference about a person's *employment*, from what they volunteered. Defensible, but it is inference about a user. |
| `org_name`, `org_state` derived from post text | **Moderate-to-high concern.** Deriving an employer from a pseudonymous author's text is the exact shape of "re-identify … by matching data with off-platform identifiers" if any external matching is used. |
| Named-prospect review queue built on Reddit | **Highest concern, and lowest value.** Phase 1 measured author-identifiable organisations at **1 in 60**, and that one was an offshore RCM vendor, not a prospect. |
| Any handling of patient-side health posts | **Avoid entirely.** "Health" is named explicitly as a sensitive characteristic. Restrict collection to professional/operational communities; do not collect patient-experience subreddits. |

**Recommendation:** for the Reddit source specifically, set `org_name` and
`org_state` to `null` by policy, and exclude Reddit from Deliverable B
altogether. This costs almost nothing — the measured yield is 1.7% and the one
hit was not a prospect — and it removes the highest-severity compliance exposure
in the design. Let LinkedIn and job postings, where organisations are *self*-
identified in public, carry Deliverable B.

The user brief already says anonymous Reddit users must not be identified or have
their employer inferred. This section is the official text backing that rule, and
the recommendation that the schema enforce it structurally rather than by
convention.

---

## 8. Apify

**Framing first, because the brief is right to insist on it: Apify access is not
Reddit authorization.** Apify is a compute-and-scraper marketplace. Nothing about
paying Apify creates any relationship with Reddit or any right under Reddit's
terms. Apify's own General Terms (effective 2026-07-09) push that responsibility
back to us: "You must use the Services to process only the Customer Data that you
are authorized to access and that is in compliance with all applicable laws and
regulations." ([Apify GT&C](https://docs.apify.com/legal/general-terms-and-conditions))

All actor data below was read from the Apify public API on **2026-09-21**.

| Actor | Capabilities | Output | Historical | Comments | Cost (per result, FREE tier) | Notes |
|---|---|---|---|---|---|---|
| [`trudax/reddit-scraper-lite`](https://apify.com/trudax/reddit-scraper-lite) | subreddit listings, keyword search, user posts, communities; `sort`, `time`, `postDateLimit`, `commentDateLimit` | 16 fields observed in our own run | via `time` + date limits | `skipComments`, `maxComments`, `searchComments` | **$0.004** + $0.02/GB actor start; min charge $0.04 | The actor already used in Phase 1. Build 5.7.9, 2026-07-31. 4.6M runs, 43k users. Gates `score` and `commentsCount` behind `includeMediaLinks: true` — a real trap, hit in Phase 1. |
| [`harshmaur/reddit-scraper-pro`](https://apify.com/harshmaur/reddit-scraper-pro) | posts, comments, communities, user profiles, keyword search, comment search, per-post comment crawl | **183 fields** across 4 shapes: `post` (75), `comment` (41), `community` (38), `user_profile` (29) | **True date-range:** `postedAfter` / `postedBefore` / `commentedAfter` / `commentedBefore`, `YYYY-MM-DD` or ISO-8601 | `crawlCommentsPerPost`, `maxCommentsPerPost` (default 200), `searchComments` | **$0.0015** + $0.01 start; AI analysis +$0.0005 | Build 0.0.511, **2026-09-21**. 1.9M runs. Richest schema by far. Moved from $20/mo rental to pay-per-event on 2026-08-29. |
| [`fatihtahta/reddit-scraper-search-fast`](https://apify.com/fatihtahta/reddit-scraper-search-fast) | search-focused | single flat dataset item type | not documented in metadata | not documented in metadata | **$0.00149** | Build 1.9.44, 2026-09-13. 634k runs, 34k users. Cheapest, least documented. |
| [`epctex/reddit-scraper`](https://apify.com/epctex/reddit-scraper) | posts, comments, detail queries | — | — | dedicated `comments-query` event | $0.001/item + $0.025/list query + $0.002/detail query | Build updated 2026-09-21. Unusual multi-event pricing; model total cost before running. |
| `trudax/reddit-scraper` (full) | — | — | — | — | — | **DEPRECATED as of 2026-09-21** (`isDeprecated: true`), unlisted, moved to pay-per-event. **Do not build on it.** |

### 8.1 Technical feasibility — what Apify genuinely adds

Two capabilities Apify actors offer that the **official Reddit API does not**:

1. **Arbitrary date-range queries.** `postedAfter` / `postedBefore` versus
   Reddit's coarse `t=hour|day|week|month|year|all`.
2. **Comment keyword search.** Reddit's `type` parameter has no `comment` value.

A third, per actor marketing: deeper historical retrieval than listing caps
allow. **Treat all three as unverified until measured.** The actors are
scraping a UI; date filtering is plausibly implemented by paginating and
discarding, which would mean the date range works but the *depth* limit still
binds. Our Phase 1 run already saw a real ceiling: r/CodingandBilling returned
nothing newer than 2026-08-17 on a 2026-09-20 collection, confirmed in both
listing and search mode.

### 8.2 Platform authorization — the part that must not be glossed

The actor documentation is unusually explicit about what it does. From
`harshmaur/reddit-scraper-pro`'s own README:

> "Bypass Reddit's 600 requests/10min API limit — no Reddit account, no OAuth"

> "Reddit's official API limits you to 600 requests per 10 minutes and requires
> OAuth setup. This scraper bypasses those limitations entirely, letting you
> extract millions of posts and comments without authentication, cookies, or a
> Reddit account."

And in its 2026-08-29 pricing-change note: "Reddit changes now require costly
residential proxies."

Set against Reddit's current published rules:

| Reddit rule | Source |
|---|---|
| "You must request access and get explicit approval before accessing any Reddit data through our API." | [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) |
| "You must not misrepresent or mask how or why you are accessing Reddit data." | as above |
| "You must not circumvent or exceed access limits…" | as above |
| "This extends to commercial and non-commercial mining, scraping, or using data for purposes like ads targeting or to train machine learning or AI models." | as above |
| "we see more and more entities using unauthorized access (for example, by scraping or using data brokers) … We still believe in an open internet, but we do not believe that third parties have a right to misuse public content just because it's public." | [Public Content Policy](https://support.reddithelp.com/hc/en-us/articles/26410290525844-Public-Content-Policy) |
| "Our robots.txt is for search engines, not Data API users." | [Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) |

The actor README's own FAQ says only that "scraping publicly available data from
Reddit is generally allowed" and advises respecting robots.txt — which is not
what Reddit's current policy says, and links to a *scraper vendor's blog post*
rather than to Reddit.

**Conclusion, stated the way the brief asks:**

- **TECHNICAL FEASIBILITY: CONFIRMED.** Apify retrieves Reddit posts and
  comments today, with a richer field set and better date filtering than the
  official API, at a cost of roughly **$1.50–$4.00 per 1,000 results**. We have
  already done it for $0.70.
- **PLATFORM AUTHORIZATION: NOT ESTABLISHED, and the actor's own marketing
  describes circumventing Reddit's access controls.** Residential-proxy
  rotation to evade blocking is the behaviour "misrepresent or mask" is aimed at.
  Nothing in Apify's terms transfers any right from Reddit; Apify's terms
  explicitly place that burden on us.
- **Therefore:** Apify is defensible as a **short, bounded, internal
  feasibility experiment** — measuring whether Reddit's *content* is worth
  pursuing, which is a question about the data, not a product built on the data.
  It is **not** a substitute for Reddit authorization in a production product,
  and it should not be presented to the CEO as one.

That distinction should be written into the decision record, because the
tempting failure mode is obvious: the Apify experiment works, it is cheap, and
it quietly becomes production.

---

## 9. Recommended Technical Test

Two tests. **Test A is runnable today.** **Test B must not be run until §3.3 is
answered.**

### Test A — Apify feasibility probe (runnable now, ~$3, one afternoon)

Purpose: measure whether Reddit *content* supports the CEO problem statement,
and whether comments are as valuable as the roadmap predicts. This is a data
question, not a product.

**Actor:** `harshmaur/reddit-scraper-pro` — it is the only one with a documented
comment schema, comment search and true date ranges. (Phase 1 used
`trudax/reddit-scraper-lite`; using a second actor also cross-checks the first.)

**Step 1 — communities.** Confirm each target subreddit exists and is active
before committing. Start from Phase 1's two plus four candidates, and record
subscriber count and newest-post date for each:

```
r/CodingandBilling      (Phase 1 baseline)
r/MedicalCoding         (Phase 1 baseline)
r/Medicalbillingandcoding
r/healthIT
r/medicalpractice        — verify it exists
r/physicaltherapy        — adjacent MSK/prior-auth, verify relevance
```

**Step 2 — query set.** Deliberately *not* the brief's example list, which is
too generic. Generic terms like `"medical billing"` and `"reimbursement"` return
career and commentary noise — Phase 1 found **26 of 60 posts were labour-market
posts**, and generic queries select for exactly those. Three tiers instead:

*Tier 1 — operational problem language (high recall, moderate precision):*
```
"prior auth" denied
"peer to peer" denied
denial "CO-197"          (auth/precert absent)
"clearinghouse" rejection
credentialing delay payer
```

*Tier 2 — pain-management CPT codes (low recall, very high precision).*
This is the highest-leverage idea in this test plan. A literal procedure code in
a billing post is almost never a false positive, and it solves the specificity
problem Phase 1 surfaced:
```
64483      transforaminal epidural, lumbar/sacral, single level
64635      RFA, lumbar/sacral facet joint nerve, single level
64490      paravertebral facet injection, cervical/thoracic
62323      interlaminar epidural, lumbar/sacral, with imaging
63650      percutaneous SCS electrode implantation
```

*Tier 3 — specialty phrases (bridging):*
```
"pain management" prior authorization
"interventional pain" billing
"epidural steroid injection" denied
```

**Step 3 — collection.** For each tier: `postedAfter` = 180 days ago,
`maxPostsCount` = 40, `crawlCommentsPerPost: true`, `maxCommentsPerPost: 50`.
Target ~120 posts and their comment trees.

**Step 4 — verify, field by field.** The test passes only if every line is yes:

| Check | Pass condition |
|---|---|
| Search works | Non-empty results for ≥ 7 of 13 queries |
| Posts retrieved | ≥ 100 unique `t3_*` ids |
| Timestamps | 100% non-null, parseable, plausible; UTC confirmed |
| URLs | 100% present and resolving to a live Reddit permalink (spot-check 10 in a browser) |
| Text | Body present for ≥ 85% (Phase 1 saw 5/60 empty — expect some) |
| Subreddit | 100% present |
| Author | Username present; record how often `[deleted]` appears |
| **Comments retrieved** | ≥ 300 comments, with `parentId`, `postId`, `depth`, `score` populated — **this is the single most important unproven capability**; Phase 1 collected zero comments |
| Pagination | Requesting 40 posts returns ~40, not 10 |
| Historical | `postedAfter` = 180 days ago actually returns posts older than 90 days — **measure the true depth ceiling, do not trust the claim** |
| Schema fit | All 120 posts load into the canonical `posts` table without loss (§11) |
| Recency ceiling | Record newest retrievable post per subreddit; compare to Phase 1's 2026-08-17 finding for r/CodingandBilling |

**Stop conditions.** Cap the run at $10 and 48 hours. If an actor requires
residential proxies to work at all, log it — that is evidence about Reddit's
enforcement posture, which is itself a finding for the decision.

### Test B — Official Data API smoke test (BLOCKED pending §3.3)

Do not create production credentials for PainMed-PA yet. When and only when
Reddit has answered the commercial question in writing, the smoke test is:

1. `POST https://www.reddit.com/api/v1/access_token` with
   `grant_type=client_credentials`, HTTP Basic (`client_id`:`client_secret`),
   compliant `User-Agent`. **Assert:** HTTP 200 and an `access_token`.
2. `GET https://oauth.reddit.com/r/CodingandBilling/new?limit=5`.
   **Assert:** 5 children; each has `id`, `permalink`, `title`, `created_utc`,
   `subreddit`, `score`, `num_comments`. **Log `X-Ratelimit-*` headers.**
3. `GET https://oauth.reddit.com/r/CodingandBilling/search?q=prior+authorization&restrict_sr=true&sort=new&t=month&limit=10`.
   **Assert:** results returned; confirm `t` buckets behave; confirm `type=comment`
   is indeed rejected (this documents the limitation in our own logs).
4. `GET https://oauth.reddit.com/r/CodingandBilling/comments/<id>?limit=50&depth=3`.
   **Assert:** comment objects with `parent_id`, `link_id`, `body`, `created_utc`.
5. Paginate `/new` twice with `after`. **Assert:** no overlap, no gap.
6. `GET https://oauth.reddit.com/api/info?id=t3_x,t3_y,…` with 100 stored ids.
   **Assert:** it round-trips — this is the deletion re-check mechanism, and
   proving it early is what makes §7.3 implementable.

Total: about 10 API calls. Roughly 0.01% of one minute's quota.

---

## 10. Data Quality Test

### 10.1 What we already know — do not re-run Phase 1

Phase 1 (`problem-intelligence/reddit/results/phase1_report.md`, 2026-09-20) already
hand-labelled 60 posts from two subreddits. Its measured base rates are the
honest starting point, and this investigation found nothing that contradicts
them:

| Measure | Phase 1 result |
|---|---|
| Problem evidence | 22/60 = **36.7%** |
| First-hand (of those) | **20/22** |
| Solution-seeking L2+ | 11/60 = 18.3% (9/60 = 15.0% restricted to RCM problems) |
| Vendor-seeking L3+ | 2/60 — "not zero" rather than a rate |
| Identifiable role | 34/60 = **56.7%** |
| Identifiable *author* organisation | 1/60 = 1.7% — and it was an offshore RCM vendor |
| **Pain-management relevant** | **1/60 = 1.7%** |
| Cost | $0.70 for four Apify runs |

**The 30/30 validation should therefore not repeat that work.** It should test
the two things Phase 1 could not: **comments**, and **pain-specific targeting**.

### 10.2 The 30-post / 30-comment validation

**Sampling — stratified, never random.** A random draw reproduces Phase 1.
Draw from Test A's pool:

- **15 posts** from Tier 2 (CPT-code queries) — tests whether procedure codes
  solve the 1.7% specificity problem.
- **10 posts** from Tier 1 (operational problem language).
- **5 posts** from plain subreddit recency — the control, comparable to Phase 1.
- **30 comments** drawn from the comment trees of those posts, sampled as the
  top-scoring comment plus one random comment per post until 30, so both
  high-visibility and ordinary replies are represented.

**Label every item against these questions.** Reuse Phase 1's rules verbatim so
the numbers are comparable — especially the rule that separates RCM *work* from
the *labour market* around it, which is what kept Phase 1's headline honest:

| # | Question | Field |
|---|---|---|
| 1 | About a pain-management practice? | `pain_management_relevant` |
| 2 | Actually RCM-related (operational, not career)? | `relevant_to_rcm` |
| 3 | First-hand? | `is_firsthand` |
| 4 | Concrete operational problem, not commentary or anticipatory worry? | `problem_evidence` |
| 5 | Usable verbatim quote? | `evidence_quote` |
| 6 | Original URL preserved and live? | spot-check in a browser |
| 7 | Date accurate and plausible? | compare `created_at` to the live page |
| 8 | Current enough? | age in days; flag anything > 12 months |
| 9 | Noise? | `relevant_to_rcm = no` counts as noise |
| 10 | Duplicate? | exact id, **and** near-identical text — Phase 1 found a same-author pair minutes apart under different titles |
| 11 | Bot / spam? | AutoModerator, mod stickies, vendor self-promo — Phase 1's naive recency pull caught one AutoModerator post |
| 12 | Useful for the CEO problem statement? | judgement, with a one-line reason |

**Comment-specific checks** — these are the new information:

| Check | Why it matters |
|---|---|
| Does the comment describe the *commenter's own* situation? | The roadmap's central claim is that comments carry more first-hand evidence than posts. Measure it: compute first-hand rate for comments and compare to Phase 1's 20/22 for posts. |
| Is it interpretable without the parent post? | Determines whether we must store parent context, which changes storage volume and the §7.3 deletion problem. |
| Does it name a payer, CPT code, or system? | Comments are where specifics surface in reply to a general question. |
| Is it short-form noise? | "Same here", "following", "^this". Measure the share — this is the comment-specific noise floor and it will be high. |

**Decision gates** — declare these before looking at results:

| Gate | Pass |
|---|---|
| Comment first-hand rate | ≥ 30% of comments carry first-hand operational evidence → comments justify their collection cost |
| CPT-code precision | ≥ 60% of the 15 Tier-2 posts are genuinely pain-management RCM → procedure-code targeting solves the specificity problem |
| Overall noise | ≤ 50% of the 60 items are `relevant_to_rcm = no` |
| URL and date integrity | 100% — anything less is a collector bug, not a source finding |

**The decision this test is actually for.** Phase 1 left one question open and
it is a product question, not an engineering one: *is this product
pain-management RCM intelligence, or RCM intelligence generally?* At 1 in 60,
a strict pain filter starves. If the CPT-code gate passes, pain-specific
targeting is viable and the narrow product survives. If it fails, the honest
recommendation is to widen the scope to RCM generally and let pain-management
relevance be a *ranking* signal rather than a *filter*. Settle that before Phase
2 freezes the taxonomy.

---

## 11. Canonical Schema Mapping

### 11.1 `posts`

| Our field | Reddit field | Direct / Derived / Unavailable | Notes |
|---|---|---|---|
| `id` | — | **Derived** | Our surrogate key. Do not use Reddit's id as PK — you will need to delete rows and keep referential integrity. |
| `source` | — | **Derived** | Constant `reddit`. |
| `external_id` | `name` (`t3_*` / `t1_*`) | **Direct** | Store the prefixed form; it disambiguates posts from comments. |
| `url` | `permalink` | **Direct** | Reddit *requires* the link-back. Store the canonical `reddit.com` permalink, not a redirect. |
| `author_handle` | `author` | **Direct, RESTRICTED** | Must be purged on account deletion, along with author id, profile URL, avatar URL and flair. Make it nullable and make purging a supported operation, not a migration. |
| `title` | `title` | **Direct** (posts only) | `null` for comments. |
| `body` | `selftext` / `body` | **Direct** | Empty for link posts (~8% in Phase 1). |
| `created_at` | `created_utc` | **Direct** | Epoch → UTC timestamp. Normalize: the official API returns epoch, Apify actors return ISO-8601. |
| `captured_at` | — | **Derived** | Our clock. |
| `raw_json` | full object | **Direct, with a caveat** | The highest-risk column in the schema under §7.3. Recommend: store it, but on the Tier-2 TTL with the rest of the content, and never treat it as a permanent archive. |
| `passed_filter` | — | **Derived** | Our prefilter. |

**Fields the schema is missing and should add**, because they are free from
Reddit and each solves a real problem:

| Suggested field | Reddit field | Why |
|---|---|---|
| `channel` / `subreddit` | `subreddit` | The roadmap's own "UHC lesson" — you must be able to attribute a trend to the community it came from. Currently there is nowhere to put it. |
| `score`, `num_comments` | `score`, `num_comments` | Engagement. Within-source only. |
| `parent_external_id` | `parent_id` | Required to reconstruct comment threads. |
| `thread_external_id` | `link_id` | Groups comments under their post. |
| `item_type` | — | `post` \| `comment`. The schema currently has no way to tell them apart. |
| `edited_at` | `edited` | Detects revision; useful for the re-check pass. |
| `last_seen_at` | — | **Required to implement deletion compliance.** Without it there is no way to know which rows need re-checking. |
| `deleted_on_source_at` | — | Tombstone for content removed from Reddit. |

### 11.2 `classifications`

Every field here is **derived by us** — Reddit supplies none of them. That is
expected; the row below records the constraint rather than the mapping.

| Our field | Direct / Derived / Unavailable | Notes |
|---|---|---|
| `post_id`, `signal_type`, `is_firsthand`, `category`, `procedures`, `payers`, `denial_reasons`, `specialty` | **Derived** | LLM inference over the text. Inference, not training — see §7.2 q8. |
| `evidence_quote` | **Derived from Reddit content** | Subject to the deletion rules. When the source post dies, the quote must go. |
| `reason`, `model`, `prompt_version`, `classified_at` | **Derived** | Ours entirely. |
| `org_name` | **Unavailable in practice, and RESTRICTED** | 1/60 measured. Recommend hard-`null` for `source = reddit`. See §7.4. |
| `org_state` | **Unavailable in practice, and RESTRICTED** | Same. Occasionally volunteered ("a 4-provider pain clinic in Ohio") — but deriving it is inference about a user, and combined with `org_name` it is the re-identification pattern. |

### 11.3 `queue_items`

| Our field | Direct / Derived / Unavailable | Notes |
|---|---|---|
| all fields | **Derived** | Purely internal workflow state. |

**Recommendation:** Reddit-sourced rows should not enter the named-prospect
queue at all. Phase 1 measured the yield at 1 in 60 and the one hit was a
vendor, while §7.4 shows it carries the highest compliance exposure in the
design. Either add a `source`-based guard on queue insertion, or scope the
queue to LinkedIn and job postings.

### 11.4 Summary

| | Count |
|---|---|
| Directly supplied by Reddit | 7 of 11 `posts` fields (`external_id`, `url`, `author_handle`, `title`, `body`, `created_at`, `raw_json`) |
| Must be derived by us | all 14 `classifications` fields, all 8 `queue_items` fields, and 4 `posts` fields (`id`, `source`, `captured_at`, `passed_filter`) |
| Impossible or restricted | `org_name`, `org_state` (restricted + 1.7% yield); author fields (available but deletion-bound) |
| Should be optional / nullable | `title`, `body`, `author_handle`, `evidence_quote`, `org_*` |
| **Should be added** | `subreddit`, `item_type`, `parent_external_id`, `thread_external_id`, `score`, `num_comments`, `last_seen_at`, `deleted_on_source_at` |

---

## 12. Production Readiness Checklist

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Technical feasibility | **CONFIRMED** | Endpoints, fields and pagination all documented and sufficient; 320 items already collected in this repo. |
| 2 | Official API availability | **CONFIRMED** | Reddit Data API exists and is documented. [Reddit Help](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) |
| 3 | Authentication feasibility | **PARTIALLY CONFIRMED** | Mechanism is clear (OAuth2 `client_credentials`). But approval precedes credentials, and Reddit says new requests are being restricted. [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) · [2026-08-05 newsroom](https://redditinc.com/news/modernizing-reddits-infrastructure-and-moderation-tools) |
| 4 | Commercial-use requirements | **REQUIRES VERIFICATION** | Requirement is unambiguous (permission + contract). Whether PainMed-PA obtains one is unknown. [Data API Terms §3.1](https://redditinc.com/policies/data-api-terms) |
| 5 | Historical-data availability | **PARTIALLY CONFIRMED** | Forward collection yes; deep backfill no; date-range search no; comment search no. Depth cap not publicly specified. [API reference](https://www.reddit.com/dev/api/#GET_search) |
| 6 | Daily collection feasibility | **CONFIRMED (conditional on #4)** | ~100 requests/day against a 100 QPM limit. Must include a deletion re-check pass. |
| 7 | Data richness | **CONFIRMED** | All canonical `posts` fields available except our own derived ones; full comment threading. |
| 8 | RCM relevance | **CONFIRMED** | 36.7% problem evidence, 20/22 first-hand, measured on our own 60-post sample. |
| 9 | Pain-management relevance | **REQUIRES VERIFICATION** | 1/60 measured. CPT-code targeting (§9 Tier 2) is the untested mitigation. |
| 10 | Noise level | **PARTIALLY CONFIRMED** | 26/60 labour-market posts; AutoModerator and near-duplicate pairs observed. Manageable with query design and dedup. Comment noise floor unmeasured. |
| 11 | Apify feasibility | **CONFIRMED technically / NOT ESTABLISHED contractually** | Actors work and are cheap; actor marketing describes bypassing Reddit's controls. §8.2 |
| 12 | Cost considerations | **PARTIALLY CONFIRMED** | Apify: $1.50–$4.00 per 1,000 results, measured. Reddit: **not publicly specified**. |
| 13 | Compliance / terms | **REQUIRES VERIFICATION** | Three open items: commercial agreement (§7.1), 48-hour retention vs trend product (§7.3), re-identification clause vs `org_*` and the prospect queue (§7.4). |
| 14 | Engineering complexity | **PARTIALLY CONFIRMED** | Collection is simple. **Deletion-compliance machinery is the real work** — `last_seen_at`, tombstones, daily re-check, cascade from post to quote to dashboard. Budget for it explicitly; it is easy to skip and expensive to retrofit. |

---

## 13. Final Findings

*No ranking or score is given, per the brief.*

### Confirmed

- Reddit operates an official Data API with OAuth2, sufficient endpoints, and
  every field the canonical schema needs except our own derived ones.
- The free-tier rate limit is **100 QPM per OAuth client id** over a 10-minute
  window — roughly 1,000× more than this project needs.
- Reddit content genuinely contains the evidence the CEO problem statement asks
  for: **36.7% problem evidence, 20 of 22 first-hand**, measured on our own
  labelled sample rather than assumed.
- **Commercial use requires Reddit's written permission and a contract**, stated
  in three separate official documents.
- **Approval now precedes all API access**, not just commercial access.
- Unauthenticated `.json` access is blocked — verified directly, HTTP 403,
  2026-09-21.
- **No comment search** and **no date-range search** in the official API.
- Deletion propagation is mandatory, with a **48-hour** recommendation, and
  applies even to de-identified copies of deleted content.
- Model training on Reddit content is prohibited without explicit consent.
- Apify actors can technically retrieve richer Reddit data than the official
  API, at $1.50–$4.00 per 1,000 results.
- Reddit for Researchers is free and bulk — and **PainMed-PA is not eligible**.

### Uncertain

- Whether Reddit will grant PainMed-PA commercial access at all, given the
  2026-08-05 statement that new requests are being restricted.
- What Reddit would charge. Not publicly specified; every circulating figure is
  third-party.
- The true listing depth cap — not publicly specified, and it determines how much
  backfill is possible.
- Whether Apify actors' `postedAfter` / `postedBefore` reach genuinely older
  content or just filter within the same shallow window.
- Whether comments carry the higher first-hand rate the roadmap predicts.
  **Completely unmeasured — zero comments collected so far.**
- Whether pain-management specificity can be rescued by CPT-code targeting, or
  whether the product scope has to widen to RCM generally.
- Whether Reddit reads LLM *inference* as distinct from *model training*.

### Must be verified with Reddit directly

Submit via the official Data API request form —
`https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164`
(verified live 2026-09-21), selecting the enterprise/commercial path
(`&tf_42139884615700=api_request_type_enterprise_clone`). Ask, explicitly:

1. Is an internal, non-redistributed market-intelligence dashboard built by an
   RCM services company classified as commercial use?
2. Given the 2026-08-05 restriction on new requests, is new commercial access
   available at all right now?
3. What retention period is permitted for stored post/comment content, and is
   the 48-hour guidance a hard requirement or a recommendation for our use case?
4. Are derived, non-content aggregate counts permitted to persist beyond the
   content retention window?
5. Does classifying retrieved content with a frozen third-party LLM (inference,
   no training, no fine-tuning) fall inside the model-training prohibition?
6. What are the fees, and what is the review timeline?

**Be honest and specific in the request.** Reddit's policies penalise vague or
masked descriptions, and the form output feeds the eligibility decision.

### Can be tested immediately with Apify

- Comment retrieval and comment quality — the largest gap in what we know.
- CPT-code query precision — the only proposed fix for the 1.7% specificity
  problem.
- Real historical depth, measured rather than claimed.
- Canonical schema round-trip, including the fields §11 recommends adding.
- Per-subreddit recency ceilings, to see whether r/CodingandBilling's
  2026-08-17 wall was a one-off or structural.

All of this is a **data-feasibility experiment**, bounded at ~$10, and it should
be recorded as such.

### Must NOT yet be assumed

- **That the free tier covers us.** It does not; PainMed-PA is a business.
- **That Apify access substitutes for Reddit authorization.** It does not, and
  the actors' own documentation describes bypassing Reddit's controls.
- **That we can store Reddit content indefinitely.** The 48-hour guidance and
  the deletion-propagation duty are real and, unmanaged, are the most likely way
  this project breaches the terms by accident.
- **That the named-prospect queue can be built on Reddit.** 1/60 measured yield,
  against the highest-severity clause in Reddit's current policy.
- **That "Reddit's API is dead in 2026."** Widely repeated, and contradicted by
  Reddit's own newsroom post. What is true is narrower and more actionable: new
  requests are being gradually restricted.
- **That successful Phase 1 collection implies production authorization.** Phase
  1's own report says so plainly, and this investigation confirms it: the
  week-1 action of applying for Data API access remains open.

---

## Appendix A — Official sources

All fetched 2026-09-21. Dates are as reported by each source.

| # | Document | URL | Date reported by source |
|---|---|---|---|
| 1 | Reddit Data API Terms | https://redditinc.com/policies/data-api-terms | Effective 2023-06-19; **Last Revised 2026-07-20** |
| 2 | Reddit Developer Terms | https://redditinc.com/policies/developer-terms | Effective 2024-09-24; **Last Revised 2026-03-24** |
| 3 | Developer Platform & Accessing Reddit Data | https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data | **Updated 2026-05-28** |
| 4 | Responsible Builder Policy | https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy | Created 2025-10-28; **edited 2026-06-05** |
| 5 | Reddit Data API Wiki | https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki | Created 2023-06-01; **edited 2026-05-11** |
| 6 | Public Content Policy | https://support.reddithelp.com/hc/en-us/articles/26410290525844-Public-Content-Policy | **edited 2025-05-29** |
| 7 | Reddit for Researchers Program | https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program | **edited 2026-06-02** |
| 8 | App Migration Program 2026 Terms | https://support.reddithelp.com/hc/en-us/articles/47822311698452-Reddit-Developer-Platform-App-Migration-Program-2026-Terms | Created 2026-04-01 |
| 9 | Modernizing Reddit's Infrastructure and Moderation Tools | https://redditinc.com/news/modernizing-reddits-infrastructure-and-moderation-tools | **2026-08-05** |
| 10 | Reddit API reference (endpoints/params) | https://www.reddit.com/dev/api/ | undated, live |
| 11 | OAuth2 guide (linked by Reddit) | https://github.com/reddit-archive/reddit/wiki/OAuth2 | repo **archived 2017-11-09** — see §2 caveat |
| 12 | App registration | https://developers.reddit.com/app-registration | live; bounty registration deadline 2026-08-30 |
| 13 | Data API access request form | https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164 | verified live (HTTP 200) |
| 14 | Apify General Terms & Conditions | https://docs.apify.com/legal/general-terms-and-conditions | **Effective 2026-07-09** |
| 15 | Apify actor metadata & pricing | `https://api.apify.com/v2/acts/<actor>` | live, read 2026-09-21 |

**Deliberately not relied on:** third-party blogs and SEO pages about Reddit API
pricing and "API shutdown." Several were surfaced during research; none are
cited for any factual claim. Where they conflict with official Reddit sources —
notably on the "$0.24/1,000 calls" figure and on the claim that the API is dead —
this report follows the official source and says so.

## Appendix B — Direct observations made during this investigation

Not documentation; measurements taken from this machine on 2026-09-21.

| Observation | Result |
|---|---|
| `GET https://www.reddit.com/r/CodingandBilling/new.json` (descriptive UA) | **HTTP 403** |
| Same, with a browser UA | **HTTP 403** |
| `GET https://www.reddit.com/search.json?q=prior%20authorization` | **HTTP 403** |
| `GET https://old.reddit.com/r/MedicalCoding/new.json` | **HTTP 302** (login) |
| `GET https://www.reddit.com/prefs/apps` | HTTP 200, redirects to login — page still live |
| Data API request form | HTTP 200 — live |
| `trudax/reddit-scraper` (full) | `isDeprecated: true` |
| Existing repo sample (`data/raw/`) | 320 Apify items, **all `dataType: post`, zero comments** |
