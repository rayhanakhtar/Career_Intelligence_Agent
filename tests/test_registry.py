"""Tests for the company registry and crawler class mapping."""

import json
import os
import tempfile

from crawlers.greenhouse import GreenhouseCrawler
from crawlers.registry import (
    build_crawlers,
    get_companies_by_platform,
    get_company,
    get_crawler_class,
    get_enabled_companies,
    load_companies,
    register_crawler,
    save_companies,
)

SAMPLE_COMPANIES = [
    {
        "id": "bosch",
        "company": "Bosch",
        "platform": "greenhouse",
        "board_token": "boschglobalsof",
        "enabled": True,
        "locations": ["Bengaluru", "Electronic City"],
    },
    {
        "id": "google",
        "company": "Google",
        "platform": "google_careers",
        "careers_url": "https://careers.google.com/",
        "enabled": True,
        "locations": ["Bengaluru", "Hyderabad"],
    },
    {
        "id": "disabled_co",
        "company": "Disabled Co",
        "platform": "lever",
        "board_token": "disabled",
        "enabled": False,
        "locations": [],
    },
]


class TestRegisterCrawler:
    """Tests for register_crawler / get_crawler_class."""

    def test_register_and_retrieve(self):
        """A registered class should be retrievable by platform name."""
        register_crawler("test_platform", GreenhouseCrawler)
        cls = get_crawler_class("test_platform")
        assert cls is GreenhouseCrawler

    def test_get_nonexistent_returns_none(self):
        """An unregistered platform should return None."""
        assert get_crawler_class("nonexistent_platform") is None


class TestLoadSaveCompanies:
    """Tests for load_companies / save_companies."""

    def test_load_save_round_trip(self):
        """Companies saved to JSON should load back identically."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
            json.dump(SAMPLE_COMPANIES, f)

        try:
            loaded = load_companies(tmp_path)
            assert len(loaded) == 3
            assert loaded[0]["id"] == "bosch"
            assert loaded[1]["id"] == "google"

            loaded[0]["company"] = "Bosch GmbH"
            save_companies(loaded, tmp_path)
            reloaded = load_companies(tmp_path)
            assert reloaded[0]["company"] == "Bosch GmbH"
        finally:
            os.unlink(tmp_path)

    def test_load_missing_file_returns_empty(self):
        """Loading a nonexistent file should return an empty list."""
        assert load_companies("/tmp/nonexistent_companies_file.json") == []


class TestGetEnabledCompanies:
    """Tests for get_enabled_companies."""

    def test_filters_disabled(self):
        """Only enabled companies should be returned."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
            json.dump(SAMPLE_COMPANIES, f)

        try:
            enabled = get_enabled_companies(tmp_path)
            assert len(enabled) == 2
            ids = {c["id"] for c in enabled}
            assert "bosch" in ids
            assert "google" in ids
            assert "disabled_co" not in ids
        finally:
            os.unlink(tmp_path)


class TestGetCompany:
    """Tests for get_company."""

    def test_get_by_id_found(self):
        """get_company should return the matching company dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
            json.dump(SAMPLE_COMPANIES, f)

        try:
            company = get_company("bosch", tmp_path)
            assert company is not None
            assert company["company"] == "Bosch"
        finally:
            os.unlink(tmp_path)

    def test_get_by_id_not_found(self):
        """get_company should return None for a missing id."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
            json.dump(SAMPLE_COMPANIES, f)

        try:
            company = get_company("nonexistent", tmp_path)
            assert company is None
        finally:
            os.unlink(tmp_path)


class TestGetCompaniesByPlatform:
    """Tests for get_companies_by_platform."""

    def test_filters_by_platform(self):
        """Only companies with the matching platform should be returned."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
            json.dump(SAMPLE_COMPANIES, f)

        try:
            gh = get_companies_by_platform("greenhouse", tmp_path)
            assert len(gh) == 1
            assert gh[0]["id"] == "bosch"

            unknown = get_companies_by_platform("unknown", tmp_path)
            assert unknown == []
        finally:
            os.unlink(tmp_path)


class TestBuildCrawlers:
    """Tests for build_crawlers."""

    def test_build_known_platforms(self):
        """build_crawlers should instantiate crawlers for registered platforms."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
            json.dump(SAMPLE_COMPANIES, f)

        try:
            crawlers = build_crawlers(tmp_path)
            assert len(crawlers) == 2  # bosch (greenhouse) + google (google_careers)
            assert isinstance(crawlers[0], GreenhouseCrawler)
            assert crawlers[0].company_id == "bosch"
            assert crawlers[0].display_name == "Bosch"
            assert crawlers[1].company_id == "google"
            assert crawlers[1].display_name == "Google"
        finally:
            os.unlink(tmp_path)

    def test_build_unknown_platform_skipped(self):
        """Companies with no registered crawler class should be skipped."""
        companies_no_match = [
            {
                "id": "unknown_co",
                "company": "Unknown",
                "platform": "does_not_exist",
                "enabled": True,
                "locations": [],
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
            json.dump(companies_no_match, f)

        try:
            crawlers = build_crawlers(tmp_path)
            assert crawlers == []
        finally:
            os.unlink(tmp_path)
