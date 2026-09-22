# Medical Billing Live — data-collection feasibility

Investigated 2026-09-21. Entry point:
`https://www.medicalbillinglive.com/members/index.php`

**Scope: feasibility only.** No classification, no production collector, and
no bulk crawl. The probes below fetch tens of pages, not thousands.

## Verdict

Collectable. Every field in the brief is obtainable from the public HTML
except **location**, which this forum never renders. No login is required
anywhere, and `robots.txt` does not disallow the forum.

Individual posts are publicly readable and each has a permalink that
resolves standalone (verified on 3 posts, all 200 with the target post
present in the response).

The real constraints are editorial, not technical — see *Caveats*.

## What the source is

Simple Machines Forum (SMF) 2.0.19 mounted at `/members/`, sitting behind a
WordPress marketing site. The index reports **45,781 posts in 13,127 topics
by 62,716 members**.

URL scheme:

| Thing | Pattern |
|---|---|
| Board page | `/members/index.php/board,<board_id>.<offset>.html` |
| Thread page | `/members/index.php/topic,<topic_id>.<offset>.html` |
| Post permalink | `/members/index.php/topic,<topic_id>.msg<msg_id>.html#msg<msg_id>` |
| Profile | `/members/index.php?action=profile;u=<user_id>` |

`<offset>` is an **item offset, not a page number** — 20 topics per board
page, 15 posts per thread page. Board page 2 is `board,7.20.html`.

## Categories

13 boards, all publicly readable. 8 carry revenue-cycle discussion:

| Board | id | Pages |
|---|---|---|
| General Questions | 6 | 222 |
| Billing | 7 | 97 |
| Coding | 8 | 49 |
| Facility Billing | 4 | 15 |
| Insurance Payments | 2 | 14 |
| NPI Numbers | 5 | 9 |
| Patient Billing | 3 | 9 |
| HIPAA | 9 | 4 |

Not RCM: New! (13), Starting Your Own Medical Billing Business (10),
Software Reviews (11), Software Questions (12), Student Section (14).

## Field availability

| Field | Available | Where it comes from |
|---|---|---|
| thread title | yes | board listing + thread `<title>` |
| thread URL | yes | board listing anchor |
| post URL / id | yes | thread page `h5` anchor (`msg<id>`) |
| author name | yes | poster column `h4` |
| author profile URL | registered only | poster column `h4` anchor |
| date / time | yes | `.keyinfo .smalltext`, per post |
| post text | yes | `.post .inner`, full body |
| category | yes | breadcrumb board link |
| reply count | yes | board listing `td.stats` |
| **location** | **no** | not rendered by this install |

The poster column exposes only `membergroup`, `postgroup` and `postcount`.
Location was probed for explicitly across 30 posts and appeared zero times.

## Three quirks that will bite a collector

1. **Rotating session ids.** Guest URLs carry a `PHPSESSID` that changes per
   request. Strip it or every URL looks new on each crawl. `clean_url()` in
   `mbl_common.py` handles this, including the case where stripping the
   leading param strands the rest behind an `&`.
2. **Encoding lies.** Pages declare `ISO-8859-1` but serve cp1252 bytes
   (smart quotes, nbsp). Decoding by the declared charset mangles them.
3. **Intermittent 503s.** The host drops requests under sequential access.
   This initially looked like a `;` vs `&` query-separator issue; measured
   over 6 trials each, both returned 200 every time, so it is load, not
   syntax. Everything goes through a retrying `fetch()` with a 2s delay.

## Feed / API

An SMF XML feed exists and is board-scopable:

```
/members/index.php?action=.xml&type=rss|rss2|atom[&board=<id>][&limit=N]
```

It is **not sufficient as a collector**:

- Bodies are truncated with an ellipsis, not full post text.
- RSS carries no author; only the Atom variant does.
- It exposes recent items only, so it cannot reach the archive.

Useful for change detection; HTML scraping is required for the content.

There is **no forum API**. `/wp-json/` answers because the marketing site
runs WordPress, but it returns no posts and no forum content, and the SMF
install has no `api.php`.

## Caveats

- **Spam contamination.** Page 1 of several boards carries off-topic
  link-spam threads (casino and sports), and some land as replies inside
  genuine RCM threads. Recorded as an observation only — nothing here is
  classified or filtered.
- **Recency is misleading.** Board pages sort by *last* post, so a 2026
  timestamp often sits on a thread opened years earlier. Deep pages are
  clean: Billing page 97 reaches March 2008.
- **Guest posts.** A meaningful share of posts are by guests, who display a
  name but have no profile URL and no stable author id.

## Files

| File | What it does |
|---|---|
| `mbl_common.py` | Shared fetch/retry, URL cleaning, board map |
| `mbl_access_test.py` | Step 1 — robots, guest access, board map |
| `mbl_category_pagination_test.py` | Step 2 — category page + pagination |
| `mbl_thread_post_test.py` | Step 3 — thread + per-post fields |
| `mbl_feed_api_test.py` | Step 4 — feed and API discovery |
| `mbl_sample_report.py` | Step 5 — consolidated report + live sample |

Each writes a `*_report.json` beside itself. Run from inside this folder,
in step order:

```bash
cd problem-intelligence/medical-billing-live
python mbl_access_test.py
python mbl_category_pagination_test.py
python mbl_thread_post_test.py
python mbl_feed_api_test.py
python mbl_sample_report.py        # reads the four above
```

`mbl_sample_report.json` is the deliverable: field-by-field availability
plus real sampled records.
