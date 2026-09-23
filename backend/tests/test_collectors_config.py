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


def test_linkedin_search_url_is_built_per_family():
    urls = {family: linkedin._search_url(query) for family, query in linkedin.QUERY_FAMILIES.items()}
    assert len(urls) == len(linkedin.QUERY_FAMILIES)
    assert all(u.startswith("https://www.linkedin.com/search/") for u in urls.values())


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
