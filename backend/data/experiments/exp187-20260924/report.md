# SLD evaluation run `exp187-20260924`

Run 2026-09-24T06:12:55Z -> 2026-09-24T07:08:35Z. Stored as analysis versions `exp187-20260924-v1` / `exp187-20260924-v2`; production `sld-analysis-v1/-v2` rows and the gold files were not modified.

**LLM fallback used:** ollama `llama3.1` at http://localhost:11434. Calls attempted 33, succeeded 33, failed 0. boto3 imported during run: False.

Scores: v1 bands High>=20 / Mid>=10 / Watch>=4 / Low; v2 bands Act>=55 / Engage>=30 / Watch>=10 / Discard (the dashboard's cutoffs). v2 weights are unchanged.

## Per-source summary

| | aapc | reddit | linkedin | facebook | overall |
|---|---:|---:|---:|---:|---:|
| Posts | 102 | 35 | 30 | 20 | 187 |
| Processed OK | 102 | 35 | 30 | 20 | 187 |
| Processing errors | 0 | 0 | 0 | 0 | 0 |
| RCM-relevant (Step 1) | 75 | 9 | 18 | 6 | 108 |
| Problem evidence (Step 2) | 36 | 6 | 5 | 1 | 48 |
| v1 mean / median | 10.36 / 8.29 | 0.73 / 0.0 | 10.66 / 8.05 | 4.29 / 0.0 | 7.96 / 3.4 |
| v1 max | 39.49 | 4.38 | 29.62 | 31.56 | 39.49 |
| v2 mean / median | 24.34 / 11.55 | 2.67 / 0.19 | 10.85 / 2.92 | 4.0 / 0.19 | 15.94 / 6.5 |
| v2 max | 95.0 | 47.0 | 70.0 | 23.65 | 95.0 |
| Avg seconds / post | 21.34 | 10.24 | 20.36 | 9.74 | 17.86 |

## v2 action bands

| Band | aapc | reddit | linkedin | facebook | overall |
|---|---:|---:|---:|---:|---:|
| Act (>=55) | 18 (18%) | 0 (0%) | 2 (7%) | 0 (0%) | 20 (11%) |
| Engage (30-55) | 14 (14%) | 1 (3%) | 0 (0%) | 0 (0%) | 15 (8%) |
| Watch (10-30) | 27 (26%) | 0 (0%) | 8 (27%) | 4 (20%) | 39 (21%) |
| Discard (<10) | 43 (42%) | 34 (97%) | 20 (67%) | 16 (80%) | 113 (60%) |

## v1 bands

| Band | aapc | reddit | linkedin | facebook | overall |
|---|---:|---:|---:|---:|---:|
| High (>=20) | 19 | 0 | 8 | 1 | 28 |
| Mid (10-20) | 24 | 0 | 7 | 2 | 33 |
| Watch (4-10) | 21 | 1 | 3 | 2 | 27 |
| Low (<4) | 38 | 34 | 12 | 15 | 99 |

## Seeking level (Step 4)

| Level | aapc | reddit | linkedin | facebook | overall |
|---|---:|---:|---:|---:|---:|
| L0 | 6 | 0 | 0 | 0 | 6 |
| L1 | 44 | 8 | 1 | 3 | 56 |
| L2 | 8 | 0 | 0 | 0 | 8 |
| L3 | 0 | 0 | 0 | 0 | 0 |
| none (supplying / not relevant) | 44 | 27 | 29 | 17 | 117 |

## Step 4 decision source and LLM calls

| | aapc | reddit | linkedin | facebook | overall |
|---|---:|---:|---:|---:|---:|
| stance via rule | 0 | 0 | 0 | 0 | 0 |
| stance via nli | 60 | 9 | 14 | 3 | 86 |
| stance via llm | 15 | 0 | 4 | 3 | 22 |
| stance via skipped | 27 | 26 | 12 | 14 | 79 |
| seeking via nli | 48 | 8 | 0 | 3 | 59 |
| seeking via llm | 10 | 0 | 1 | 0 | 11 |
| seeking via skipped | 44 | 27 | 29 | 17 | 117 |
| LLM calls attempted | 25 | 0 | 5 | 3 | 33 |
| LLM calls failed | 0 | 0 | 0 | 0 | 0 |
| Re-normalized text != stored | 0 | 0 | 0 | 0 | 0 |

## Speaker type

| Speaker | aapc | reddit | linkedin | facebook | overall |
|---|---:|---:|---:|---:|---:|
| practice_side | 11 | 0 | 2 | 1 | 14 |
| unknown | 91 | 35 | 27 | 19 | 172 |
| vendor | 0 | 0 | 1 | 0 | 1 |

## Agreement with human scores (gold set, 167 posts)

Facebook posts have no human labels, so this covers the 167 gold posts only.

| Scorer | Pearson | Spearman | Human top-20 found |
|---|---:|---:|---:|
| v1, fresh run | 0.556 | 0.587 | 11 / 20 |
| v2, fresh run | 0.755 | 0.794 | 14 / 20 |
| v1, stored production rows | 0.564 | 0.59 | 11 / 20 |
| v2, reference (model_comparison.csv) | 0.754 | 0.793 | 14 / 20 |

v1 score changed vs stored row on 70 posts; v2 changed vs the gold-set reference on 75 posts.

## Facebook by group

| Group | Posts | RCM-relevant | v1 mean | v2 mean | v2 max | Act+Engage |
|---|---:|---:|---:|---:|---:|---:|
| medical_claims_tasks | 7 | 3 | 3.4 | 5.17 | 17.6 | 0 |
| pmr_interventional_pain_billing | 9 | 3 | 6.9 | 4.73 | 23.65 | 0 |
| usa_medical_billing | 4 | 0 | 0.0 | 0.33 | 0.88 | 0 |

## Facebook posts

| Post id | Group | v1 | v2 | v2 band | Seeking | Excerpt |
|---|---|---:|---:|---|---|---|
| 1619623016563863 | pmr_interventional_pain_billing | 18.4 | 23.6 | Watch (10-30) | L1 | 64492 denying for TON Hello! I was doing some research on some denials, and thought that i... |
| 1588485609490104 | medical_claims_tasks | 9.9 | 17.6 | Watch (10-30) | none | 📌 النصيحة المهنية اليومية / Hospital RCM 80 🚨 أحيانًا المشكلة ليست في أي قسم من أقسام الـR... |
| 1588486999489965 | medical_claims_tasks | 9.9 | 17.6 | Watch (10-30) | none | 📌 النصيحة المهنية اليومية / Hospital RCM 80 🚨 أحيانًا المشكلة ليست في أي قسم من أقسام الـR... |
| 1620918836434281 | pmr_interventional_pain_billing | 31.6 | 14.8 | Watch (10-30) | L1 | Hello Our providers are thinking about offering qEEG Quantitative Electroencephalogram wit... |
| 1622055466320618 | pmr_interventional_pain_billing | 12.1 | 2.9 | Discard (<10) | L1 | Is anyone here doing cryoablation via Iovera for lumbar facets? Are you getting paid? If s... |
| 2493899787782035 | usa_medical_billing | 0.0 | 0.9 | Discard (<10) | none | 🚨 IT SUPPORT ENGINEER REQUIRED – USA 🇺🇸 📍 Location: Valley Relocation and Storage 4020 Nel... |
| 1588592222812776 | medical_claims_tasks | 0.0 | 0.2 | Discard (<10) | none | مهارات يا شباب |
| 1588614956143836 | medical_claims_tasks | 0.0 | 0.2 | Discard (<10) | none | الغلطة الأولى مجانا |
| 1589379062734092 | medical_claims_tasks | 0.0 | 0.2 | Discard (<10) | none | كتاب جديد بقلم خبير كبير |
| 1590177149320950 | medical_claims_tasks | 3.9 | 0.2 | Discard (<10) | none | 📚 كتاب يحتاجه كل زميل في الرعاية الصحية والتأمين الطبي 🏥🩺 هل تريد أن تفهم التأمين الصحي ال... |
| 1590320719306593 | medical_claims_tasks | 0.0 | 0.2 | Discard (<10) | none | دكتور محمد شريف رحمه الله رحمة واسعة واحد من أهم الأساتذة المؤثرين في أجيال من الأطباء الم... |
| 1619037083289123 | pmr_interventional_pain_billing | 0.0 | 0.2 | Discard (<10) | none | Let's welcome our new members! Kayla Thompson |
| 1619492153243616 | pmr_interventional_pain_billing | 0.0 | 0.2 | Discard (<10) | none | Let's welcome our new members! Glowandgolife Chaudhry |
| 1620101426516022 | pmr_interventional_pain_billing | 0.0 | 0.2 | Discard (<10) | none | Let's welcome our new members! Shannon Kay |
| 1620501536476011 | pmr_interventional_pain_billing | 0.0 | 0.2 | Discard (<10) | none | Let's welcome our new members! IntraMed, Apoorva Nyayapathi |
| 1622080969651401 | pmr_interventional_pain_billing | 0.0 | 0.2 | Discard (<10) | none | Let's welcome our new members! David Webb |
| 1624563519403146 | pmr_interventional_pain_billing | 0.0 | 0.2 | Discard (<10) | none | Let's welcome our new members! Elvina Edwards, Rachael Schlensker |
| 2493887067783307 | usa_medical_billing | 0.0 | 0.2 | Discard (<10) | none | Amazon Basics Eye Vitamin and Mineral Supplement, AREDS 2 Formula with Lutein & Zeaxanthin... |
| 2493889024449778 | usa_medical_billing | 0.0 | 0.2 | Discard (<10) | none | 𝐏𝐄𝐍𝐓𝐀𝐌𝐄𝐃 𝐌𝐚𝐧𝐮𝐚𝐥 𝐍𝐞𝐞𝐝𝐥𝐞 & 𝐒𝐲𝐫𝐢𝐧𝐠𝐞 𝐃𝐞𝐬𝐭𝐫𝐨𝐲𝐞𝐫 𝐇𝐮𝐛 𝐂𝐮𝐭𝐭𝐞𝐫 𝐌𝐚𝐜𝐡𝐢𝐧𝐞 𝐒𝐭𝐚𝐢𝐧𝐥𝐞𝐬𝐬 𝐒𝐭𝐞𝐞𝐥. 𝐂𝐚𝐩𝐚𝐜𝐢𝐭𝐲 𝟓𝟎... |
| 2493895101115837 | usa_medical_billing | 0.0 | 0.1 | Discard (<10) | none | SUBMIT YOUR ABSTRACT Share Your Research. Present Your Innovation. Shape the Future of Pha... |

## Processing errors

None.
