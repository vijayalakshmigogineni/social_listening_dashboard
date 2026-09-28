"""
Forum quote-reply stripping (text_signals.strip_quoted_parent). Step 2 uses
it so a reply is classified on what its author wrote, not on the parent post
it quotes.
"""

from __future__ import annotations

from app.analysis.text_signals import QUOTE_BLOCK_RE, strip_quoted_parent

QUOTING_REPLY = (
    "wjbruton said:\n"
    "We have had a lot of denials from Medicare on our claims and our billing team "
    "cannot keep up. Any help appreciated.\n"
    "Click to expand...\n"
    "GT as a modifier is invalid."
)


def test_quoted_parent_is_removed():
    own = strip_quoted_parent(QUOTING_REPLY)
    assert "GT as a modifier is invalid." in own
    assert "cannot keep up" not in own, "the parent's pain leaked into the reply"


def test_quote_block_is_matched_for_parent_context():
    match = QUOTE_BLOCK_RE.match(QUOTING_REPLY)
    assert match and "cannot keep up" in match.group(0)


def test_reply_that_is_only_a_quote_keeps_its_text():
    # Stripping everything would leave an empty string; the original text is
    # kept instead.
    only_quote = "someone said:\nI have denials on our Medicare claims.\nClick to expand...\n"
    assert strip_quoted_parent(only_quote).strip()


def test_text_without_quote_is_unchanged():
    assert strip_quoted_parent("Plain post about CO-16 denials.") == "Plain post about CO-16 denials."
    assert strip_quoted_parent(None) == ""
