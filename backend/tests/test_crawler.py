import os
import pytest
from app.ingestion.crawler import is_allowlisted_url, compute_content_hash, SchemeCrawler

ALLOWLIST = ["gov.in", "nic.in", "maharashtra.gov.in", "scholarships.gov.in"]

def test_allowlist_domain_checker():
    assert is_allowlisted_url("https://scholarships.gov.in/scheme", ALLOWLIST) is True
    assert is_allowlisted_url("https://maharashtra.gov.in/portal", ALLOWLIST) is True
    assert is_allowlisted_url("https://subdomain.nic.in/page", ALLOWLIST) is True

    # Rejections
    assert is_allowlisted_url("https://malicious-site.com/fake-scheme", ALLOWLIST) is False
    assert is_allowlisted_url("https://phishing-gov.in.attacker.org/test", ALLOWLIST) is False
    assert is_allowlisted_url("invalid-url-string", ALLOWLIST) is False

def test_content_hash_deterministic():
    text = "Government Scheme Eligibility Rules Text"
    hash1 = compute_content_hash(text)
    hash2 = compute_content_hash(text)
    assert hash1 == hash2
    assert len(hash1) == 64

def test_html_extraction():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_scheme.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html_text = f.read()

    crawler = SchemeCrawler(allowlisted_domains=ALLOWLIST)
    extracted = crawler._extract_html_text(html_text)
    assert "Engineering Students Maharashtra" in extracted
    assert "2.5 lakh" in extracted
