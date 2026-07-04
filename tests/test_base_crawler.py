"""Tests for the BaseCrawler abstract base class."""

from crawlers.base import BaseCrawler


class TestBaseCrawler:
    """Tests for BaseCrawler ABC."""

    def test_cannot_instantiate_directly(self):
        """BaseCrawler should not be instantiable directly (abstract)."""
        try:
            BaseCrawler("test", "Test Company")
            raise AssertionError("Should have raised TypeError")
        except TypeError:
            pass

    def test_subclass_must_implement_fetch_jobs(self):
        """A subclass that doesn't implement fetch_jobs should not be instantiable."""

        class Incomplete(BaseCrawler):
            pass

        try:
            Incomplete("x", "X")
            raise AssertionError("Should have raised TypeError")
        except TypeError:
            pass

    def test_concrete_subclass_can_be_instantiated(self):
        """A fully implemented subclass should work."""

        class Concrete(BaseCrawler):
            platform = "test"

            def fetch_jobs(self):
                return []

        instance = Concrete("test_id", "Test Display")
        assert instance.company_id == "test_id"
        assert instance.display_name == "Test Display"
        assert instance.locations == []

    def test_locations_defaults_to_empty_list(self):
        """locations should default to [] when not provided."""

        class Concrete(BaseCrawler):
            platform = "test"

            def fetch_jobs(self):
                return []

        instance = Concrete("id", "Name")
        assert instance.locations == []

    def test_locations_from_constructor(self):
        """locations should be stored when provided."""

        class Concrete(BaseCrawler):
            platform = "test"

            def fetch_jobs(self):
                return []

        locs = ["Bengaluru", "Mumbai"]
        instance = Concrete("id", "Name", locations=locs)
        assert instance.locations == locs
