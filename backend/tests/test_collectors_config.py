"""
Collection recall changes: LinkedIn query families, Reddit subreddit list,
AAPC forum list. These are config-shape tests -- no network calls (Apify/RSS
are not hit here).
"""

from __future__ import annotations

from app.collectors import aapc, linkedin, reddit


def test_linkedin_has_multiple_query_families_including_payer_agnostic_ones():
    assert len(linkedin.QUERY_FAMILIES) >= 4
    # At least one family must not require a payer name, unlike the original
    # single DEFAULT_QUERY (testing/SLD-ROADMAP.md's measured 0/95 finding).
    payer_terms = ("unitedhealthcare", "aetna", "cigna", "humana", "medicare", "medicaid")
    payer_free_families = [
        q for q in linkedin.QUERY_FAMILIES.values()
        if not any(p in q.lower() for p in payer_terms)
    ]
    assert payer_free_families, "expected at least one payer-agnostic query family"


def test_linkedin_runs_one_actor_call_per_query_family():
    # The harvestapi actor takes the query itself (searchQueries), not a
    # LinkedIn search URL -- so check one call per family, each carrying that
    # family's query, with no network access.
    from unittest.mock import patch

    with patch.object(linkedin, "run_actor_sync", return_value=[]) as run:
        linkedin.collect_families(limit_per_query=5)

    sent = [call.args[1]["searchQueries"] for call in run.call_args_list]
    assert sent == [[q] for q in linkedin.QUERY_FAMILIES.values()]
    assert all(call.args[1]["maxPosts"] == 5 for call in run.call_args_list)


def test_reddit_default_subreddits_include_phase1b_validated_communities():
    validated = {"CodingandBilling", "MedicalCoding", "Medicalbillingandcoding",
                 "therapists", "medicine", "FamilyMedicine", "MedicalAssistant", "PrivatePractice"}
    assert validated.issubset(set(reddit.DEFAULT_SUBREDDITS))
    # Explicitly excluded patient-voice communities must never be added.
    excluded = {"ChronicPain", "PainManagement", "HealthInsurance"}
    assert excluded.isdisjoint(set(reddit.DEFAULT_SUBREDDITS))


def test_aapc_default_forums_include_rss_validated_additions():
    validated = {"billing_reimbursement", "payer_health_plan", "modifiers",
                 "anesthesia", "interventional_radiology", "medicare_regulations",
                 "orthopaedics", "general_discussion"}
    assert validated.issubset(set(aapc.DEFAULT_FORUMS.keys()))
    for url in aapc.DEFAULT_FORUMS.values():
        assert url.startswith("https://www.aapc.com/discuss/forums/")
        assert url.endswith("/index.rss")
