---
title: SLD Zero-Shot Classifier
emoji: 🔎
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

Zero-shot classification API for the Social Listening Dashboard
(`MoritzLaurer/deberta-v3-base-zeroshot-v2.0`).

- `GET /health`
- `POST /classify` with body `{"text": "...", "hypotheses": ["...", "..."]}` and header
  `Authorization: Bearer <SPACE_API_KEY>`. Returns `{"labels": [...], "scores": [...]}`, ranked.

Set `SPACE_API_KEY` under Settings → Variables and secrets.
