"""Crawlers package — platform-specific job board scrapers."""

from crawlers.base import BaseCrawler
from crawlers.custom import (
    AmazonCrawler,
    AppleCrawler,
    CiscoCrawler,
    GoogleCrawler,
    IbmCrawler,
    IntelCrawler,
    MathCompanyCrawler,
    MetaCrawler,
    NvidiaCrawler,
    OracleCrawler,
    QualcommCrawler,
    SwiggyCrawler,
    TredenceCrawler,
)
from crawlers.greenhouse import GreenhouseCrawler
from crawlers.lever import LeverCrawler
from crawlers.ashby import AshbyCrawler
from crawlers.smartrecruiters import SmartRecruitersCrawler
from crawlers.workable import WorkableCrawler
from crawlers.registry import register_crawler
from crawlers.workday import WorkdayCrawler

register_crawler("greenhouse", GreenhouseCrawler)
register_crawler("lever", LeverCrawler)
register_crawler("workday", WorkdayCrawler)
register_crawler("ashby", AshbyCrawler)
register_crawler("smartrecruiters", SmartRecruitersCrawler)
register_crawler("workable", WorkableCrawler)
register_crawler("google_careers", GoogleCrawler)
register_crawler("amazon_careers", AmazonCrawler)
register_crawler("meta_careers", MetaCrawler)
register_crawler("nvidia_careers", NvidiaCrawler)
register_crawler("ibm_careers", IbmCrawler)
register_crawler("oracle_careers", OracleCrawler)
register_crawler("cisco_careers", CiscoCrawler)
register_crawler("intel_careers", IntelCrawler)
register_crawler("qualcomm_careers", QualcommCrawler)
register_crawler("apple_careers", AppleCrawler)
register_crawler("mathcompany_careers", MathCompanyCrawler)
register_crawler("swiggy_careers", SwiggyCrawler)
register_crawler("tredence_careers", TredenceCrawler)

__all__ = [
    "BaseCrawler",
    "GreenhouseCrawler",
    "LeverCrawler",
    "WorkdayCrawler",
    "AshbyCrawler",
    "SmartRecruitersCrawler",
    "WorkableCrawler",
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
