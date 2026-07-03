# Crawler Support Matrix

| # | Company | Platform | Renderer | Status | Notes |
|---|---------|----------|----------|--------|-------|
| | **Existing (Sprint 1)** | | | | |
| 1 | Bosch | Greenhouse | Requests | ✅ Working | Generic crawler |
| 2 | Flipkart | Greenhouse | Requests | ✅ Working | Generic crawler |
| 3 | Samsung | Greenhouse | Requests | ✅ Working | Generic crawler |
| 4 | Intuit | Greenhouse | Requests | ✅ Working | Generic crawler |
| 5 | Accenture | Lever | Requests | ✅ Working | Generic crawler |
| 6 | Google | Custom | Requests | ✅ Working | JSON LD embedded in HTML |
| 7 | Microsoft | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF blocks `requests` |
| 8 | Amazon | Custom | Requests | ✅ Working | Proprietary jobs API |
| 9 | Deloitte | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF blocks `requests` |
| 10 | Uber | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF blocks `requests` |
| 11 | Target | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF blocks `requests` |
| 12 | Meta | Custom | Requests | ✅ Working | `__INITIAL_STATE__` parse |
| 13 | NVIDIA | Custom | Requests | ✅ Working | Workday-backed custom |
| 14 | IBM | Custom | Requests | ✅ Working | HTML scrape fallback |
| 15 | Oracle | Custom | Requests | ✅ Working | Custom careers |
| 16 | Cisco | Custom | Requests | ✅ Working | Custom careers |
| 17 | Intel | Custom | Requests | ✅ Working | Custom careers |
| 18 | Qualcomm | Custom | Requests | ✅ Working | Custom careers |
| 19 | Apple | Custom | Requests | ✅ Working | Custom careers |
| | **Tier 1: Global Tech** | | | | |
| 20 | Adobe | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF (verified: wd5 unreachable via `requests`) |
| 21 | SAP | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 22 | Salesforce | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 23 | ServiceNow | Workday | Playwright | 🔍 Needs investigation | API 422 / page 406 |
| 24 | Atlassian | Greenhouse | Requests | ✅ Working | Verified: API responds |
| 25 | Walmart | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 26 | Goldman Sachs | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 27 | JPMorgan Chase | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 28 | Visa | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 29 | PayPal | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 30 | American Express | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| | **Tier 2: Indian Product & AI** | | | | |
| 31 | PhonePe | Greenhouse | Requests | ✅ Working | Verified: 58 jobs from API |
| 32 | Razorpay | Greenhouse | Requests | ✅ Working | Generic crawler |
| 33 | Swiggy | Swiggy | Requests | ✅ Working | MyNextHire ATS — direct API |
| 34 | CRED | Lever | Requests | ✅ Working | Verified: 5 jobs from API |
| 35 | Meesho | Lever | Requests | ✅ Working | Generic crawler |
| 36 | InMobi | Greenhouse | Requests | ✅ Working | Generic crawler |
| 37 | Fractal Analytics | Workday | Playwright | ⚠️ Needs session (422) | SmartRecruiters available as secondary |
| 38 | Tiger Analytics | Workable | Requests | ✅ Working | Verified: 185 jobs from API |
| 39 | Tredence | Tredence | Requests | ✅ Working | RippleHire ATS — direct API |
| 40 | TheMathCompany | Custom | Requests | ⚪ Talent community | No active jobs |
| 41 | Sarvam AI | Ashby | Requests | ✅ Working | Generic crawler |
| | **Tier 3: IT Services & Consulting** | | | | |
| 42 | Infosys | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 43 | Wipro | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 44 | TCS | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 45 | HCLTech | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 46 | Tech Mahindra | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 47 | Cognizant | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 48 | Capgemini | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 49 | EY | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 50 | PwC | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |
| 51 | KPMG | Workday | Playwright | ⚠️ Needs session (422) | Cloudflare WAF |

## Legend

| Icon | Meaning |
|------|---------|
| ✅ Working | Crawler exists and is expected to function |
| 🔧 In progress | Crawler being built (custom/Playwright) |
| 🔍 Needs investigation | Requires deeper analysis |
| ⚪ Talent community | No live job postings to crawl |
