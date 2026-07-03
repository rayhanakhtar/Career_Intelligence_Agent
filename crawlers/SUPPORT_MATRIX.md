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
| 7 | Microsoft | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 8 | Amazon | Custom | Requests | ✅ Working | Proprietary jobs API |
| 9 | Deloitte | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 10 | Uber | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 11 | Target | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 12 | Meta | Custom | Requests | ✅ Working | `__INITIAL_STATE__` parse |
| 13 | NVIDIA | Custom | Requests | ✅ Working | Workday-backed custom |
| 14 | IBM | Custom | Requests | ✅ Working | HTML scrape fallback |
| 15 | Oracle | Custom | Requests | ✅ Working | Custom careers |
| 16 | Cisco | Custom | Requests | ✅ Working | Custom careers |
| 17 | Intel | Custom | Requests | ✅ Working | Custom careers |
| 18 | Qualcomm | Custom | Requests | ✅ Working | Custom careers |
| 19 | Apple | Custom | Requests | ✅ Working | Custom careers |
| | **Tier 1: Global Tech** | | | | |
| 20 | Adobe | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 21 | SAP | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 22 | Salesforce | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 23 | ServiceNow | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 24 | Atlassian | Greenhouse | Requests | ✅ Working | Verified: API responds |
| 25 | Walmart | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 26 | Goldman Sachs | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 27 | JPMorgan Chase | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 28 | Visa | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 29 | PayPal | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 30 | American Express | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| | **Tier 2: Indian Product & AI** | | | | |
| 31 | PhonePe | Greenhouse | Requests | ✅ Working | Verified: 58 jobs from API |
| 32 | Razorpay | Greenhouse | Requests | ✅ Working | Generic crawler |
| 33 | Swiggy | Swiggy | Requests | ✅ Working | MyNextHire ATS — direct API |
| 34 | CRED | Lever | Requests | ✅ Working | Verified: 5 jobs from API |
| 35 | Meesho | Lever | Requests | ✅ Working | Generic crawler |
| 36 | InMobi | Greenhouse | Requests | ✅ Working | Generic crawler |
| 37 | Fractal Analytics | Workday | Playwright | 🔧 In progress | Cloudflare WAF — site=`Careers` |
| 38 | Tiger Analytics | Workable | Requests | ✅ Working | Verified: 185 jobs from API |
| 39 | Tredence | Tredence | Requests | ✅ Working | RippleHire ATS — direct API |
| 40 | TheMathCompany | Custom | Requests | ⚪ Talent community | No active jobs |
| 41 | Sarvam AI | Ashby | Requests | ✅ Working | Generic crawler |
| | **Tier 3: IT Services & Consulting** | | | | |
| 42 | Infosys | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 43 | Wipro | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 44 | TCS | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 45 | HCLTech | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 46 | Tech Mahindra | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 47 | Cognizant | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 48 | Capgemini | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 49 | EY | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 50 | PwC | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |
| 51 | KPMG | Workday | Playwright | 🔧 In progress | Cloudflare WAF — `page.evaluate` browser fetch |

## Legend

| Icon | Meaning |
|------|---------|
| ✅ Working | Crawler exists and is expected to function |
| 🔧 In progress | Crawler being built / tested |
| 🔍 Needs investigation | Requires deeper analysis |
| ⚪ Talent community | No live job postings to crawl |
