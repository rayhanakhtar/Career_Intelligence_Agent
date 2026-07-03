# Sprint 2A — Investigation Report

**Goal:** Investigate all ~32 missing companies' career pages to determine ATS platform, renderer, API endpoints, and blockers.

**Status:** ✅ Complete — All companies investigated, `companies.yml` populated with 32 new entries.

---

## Summary Statistics

| Tier | Companies | Workday | Greenhouse | Lever | Ashby | Custom | Other |
|------|-----------|---------|------------|-------|-------|--------|-------|
| Tier 1 (Global Tech) | 11 | 9 | 1 | 0 | 0 | 0 | 1 (WF blocked) |
| Tier 2 (Indian Product & AI) | 11 | 1 | 3 | 2 | 1 | 3 | 1 (Workable) |
| Tier 3 (IT Services & Consulting) | 10 | 10 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **32** | **20** | **4** | **2** | **1** | **3** | **2** |

---

## Tier 1: Global Tech (11 companies)

| Company | ATS Platform | Tenant/Board | Renderer | Notes |
|---------|-------------|--------------|----------|-------|
| Adobe | Workday | `adobe.wd5` | requests | Standard Workday instance |
| SAP | Workday | `sap.wd5` | requests | Also has SuccessFactors |
| Salesforce | Workday | `salesforce.wd1` | requests | Also has custom careers page |
| ServiceNow | Workday | `servicenow.wd1` | playwright | 403 on direct fetch (blocked/Cloudflare) |
| Atlassian | Greenhouse | `atlassian` | requests | Standard Greenhouse board |
| Walmart | Workday | `walmart.wd5` | requests | Standard Workday instance |
| Goldman Sachs | Workday | `goldmansachs.wd1` | requests | Standard Workday instance |
| JPMorgan Chase | Workday | `jpmc.wd1` | requests | Standard Workday instance |
| Visa | Workday | `visa.wd1` | requests | Standard Workday instance |
| PayPal | Workday | `paypal.wd1` | requests | Standard Workday instance |
| American Express | Workday | `aexp.wd1` | requests | Standard Workday instance |

---

## Tier 2: Indian Product & AI (11 companies)

| Company | ATS Platform | Tenant/Board | Renderer | Notes |
|---------|-------------|--------------|----------|-------|
| PhonePe | Greenhouse | `phonepe` | requests | Custom front-end, Greenhouse backend |
| Razorpay | Greenhouse | `razorpaysoftwareprivatelimited` | requests | Standard Greenhouse board |
| Swiggy | Custom (MyNextHire) | — | playwright | Indian AI-first ATS, custom careers page |
| CRED | Lever | `cred` | requests | Standard Lever board |
| Meesho | Lever | `meesho` | requests | Standard Lever board |
| InMobi | Greenhouse | `inmobi` | requests | Standard Greenhouse board |
| Fractal Analytics | Workday | `fractal.wd1` | requests | Also has SmartRecruiters (dual) |
| Tiger Analytics | Workable | — | playwright | Also has Sense (dual ATS setup) |
| Tredence | Custom (RippleHire) | — | playwright | Indian enterprise AI ATS |
| TheMathCompany | Custom | — | playwright | Talent community signup model |
| Sarvam AI | Ashby | `sarvam` | playwright | Custom front-end, Ashby-powered |

---

## Tier 3: IT Services & Consulting (10 companies)

| Company | ATS Platform | Tenant/Board | Renderer | Notes |
|---------|-------------|--------------|----------|-------|
| Infosys | Workday | `infosys.wd1` | requests | Standard Workday instance |
| Wipro | Workday | `wipro.wd1` | requests | Standard Workday instance |
| TCS | Workday | `tcs.wd1` | requests | Standard Workday instance |
| HCLTech | Workday | `hcltech.wd1` | requests | Standard Workday instance |
| Tech Mahindra | Workday | `techmahindra.wd1` | requests | Standard Workday instance |
| Cognizant | Workday | `cognizant.wd1` | requests | Standard Workday instance |
| Capgemini | Workday | `capgemini.wd1` | requests | Standard Workday instance |
| EY | Workday | `ey.wd1` | requests | Standard Workday instance |
| PwC | Workday | `pwc.wd1` | requests | Standard Workday instance |
| KPMG | Workday | `kpmg.wd1` | requests | Standard Workday instance |

---

## Key Findings

### 1. Workday Dominance
- **20 out of 32 companies (62.5%)** use Workday
- ALL IT Services & Consulting firms (10/10) use Workday
- ALL financial firms (GS, JPMC, AmEx, Visa, PayPal) use Workday
- Workday is the clear enterprise standard

### 2. Greenhouse for Indian Fintech/Product
- PhonePe, Razorpay, InMobi, and Atlassian use Greenhouse
- Indian fintech startups favor Greenhouse for developer hiring

### 3. Lever for Consumer Tech
- CRED and Meesho both use Lever
- Lever's single-page application flow makes it a preferred choice

### 4. Custom/Niche ATS for Indian Analytics Firms
- Swiggy (MyNextHire), Tredence (RippleHire), TheMathCompany (custom), Tiger Analytics (Workable/Sense) — Indian analytics/consulting firms tend toward niche Indian ATS providers or custom solutions

### 5. Ashby for AI Startups
- Sarvam AI uses Ashby — aligns with Ashby's popularity among AI-first startups

### 6. Blockers
- ServiceNow returns 403 on direct HTTP fetch (likely Cloudflare/WAF) — needs Playwright
- Custom career pages (Swiggy, Tredence, TheMathCompany, Sarvam AI) need Playwright for JavaScript rendering

---

## `companies.yml` Update

- **19 existing entries** (Bosch, Flipkart, Samsung, Intuit, Accenture, Google, Microsoft, Amazon, Deloitte, Uber, Target, Meta, NVIDIA, IBM, Oracle, Cisco, Intel, Qualcomm, Apple)
- **32 new entries added** across all three tiers
- **Total: 51 companies** now registered

---

## Next Steps (Sprint 2B)

1. **Build Ashby crawler** (`crawlers/ashby.py`) — for Sarvam AI and future Ashby clients
2. **Build SmartRecruiters crawler** (`crawlers/smartrecruiters.py`) — for Fractal Analytics
3. **Build Workable crawler** (`crawlers/workable.py`) — for Tiger Analytics
4. **Build MyNextHire/RippleHire custom scrapers** — for Swiggy and Tredence (needs Playwright)
5. **Build/verify Workday crawler** reusability — covers 20 companies
6. **Build/verify Greenhouse crawler** reusability — covers 4 new companies
7. **Build/verify Lever crawler** reusability — covers 2 new companies
8. **Tier 1 priority crawlers**: Adobe, SAP, Salesforce, ServiceNow (blocked), Atlassian, Walmart, GS, JPMC, Visa, PayPal, AmEx
9. **Tier 2 priority crawlers**: PhonePe, Razorpay, CRED, Meesho, InMobi, Fractal Analytics, Sarvam AI
10. **Tier 3 priority crawlers**: Infosys, Wipro, TCS, HCLTech, TechM, Cognizant, Capgemini, EY, PwC, KPMG
