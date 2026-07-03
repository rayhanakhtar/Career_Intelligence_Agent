"""Custom company-specific scrapers for non-ATS career portals."""

from crawlers.custom.google_careers import GoogleCrawler
from crawlers.custom.amazon_careers import AmazonCrawler
from crawlers.custom.meta_careers import MetaCrawler
from crawlers.custom.nvidia_careers import NvidiaCrawler
from crawlers.custom.ibm_careers import IbmCrawler
from crawlers.custom.oracle_careers import OracleCrawler
from crawlers.custom.cisco_careers import CiscoCrawler
from crawlers.custom.intel_careers import IntelCrawler
from crawlers.custom.qualcomm_careers import QualcommCrawler
from crawlers.custom.apple_careers import AppleCrawler
from crawlers.custom.mathcompany_careers import MathCompanyCrawler
from crawlers.custom.swiggy_careers import SwiggyCrawler
from crawlers.custom.tredence_careers import TredenceCrawler

__all__ = [
    "GoogleCrawler",
    "AmazonCrawler",
    "MetaCrawler",
    "NvidiaCrawler",
    "IbmCrawler",
    "OracleCrawler",
    "CiscoCrawler",
    "IntelCrawler",
    "QualcommCrawler",
    "AppleCrawler",
    "MathCompanyCrawler",
    "SwiggyCrawler",
    "TredenceCrawler",
]
