# Market research: Taiwan hospitals as the first customers

Sources checked on 2026-11-12. Only facts with a source are listed. Figures marked *derived* are our own
arithmetic, and the sections that state assumptions are labelled as such.

## Why now: regulation

- **PDPA amendment, promulgated 2025-11-11** (passed by the Legislative Yuan 2025-10-17). It adds breach
  notification to the people affected (Art. 12) and a new competent authority, the Personal Data Protection
  Commission. Its effective date is still to be set by the Executive Yuan, and the commission is a preparatory
  office as of Oct 2026.
  [MOJ law database](https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=I0050021) ·
  [CNA 2025-10-17](https://www.cna.com.tw/news/aipl/202510170211.aspx) ·
  [K&L Gates 2026-01-13](https://www.klgates.com/New-Developments-in-the-Taiwan-Personal-Data-Protection-Act-1-13-2026)
- **Fines already in force** (2023 amendment, Art. 48). A non-government organisation that fails its security
  duty pays NT$20,000–2,000,000, then NT$150,000–15,000,000 for each failure to correct. Serious cases go
  directly to NT$150,000–15,000,000. Private hospitals are non-government organisations under the PDPA.
- **Medical records are special-category data** (PDPA Art. 6). Research use is allowed only when the data
  "無從識別特定之當事人" (cannot identify the person). The Enforcement Rules (Art. 17) and MOJ interpretations
  say the test fails if the data can still be identified once combined with other data. This is exactly the
  quasi-identifier problem that RedactAgent's agentic check targets.
- **Constitutional Court judgment 111年憲判字第13號 (2022-08-12, NHI research database).** It upheld research
  use on the premise of de-identification and noted that de-identified data can still be indirectly identifiable.
  It required an opt-out right and independent oversight.
  [judgment text](https://laws.gov.taipei/law/Judge/ConstitutionalJudgeContent/CJ00000872)
- **NHI Data Management Act** (全民健康保險資料管理條例), passed 2025-12-02, **in force 2026-08-10**. It
  provides an opt-out right, limits applicants to government, hospitals, research institutes and universities,
  and fines unauthorised use NT$2M–10M.
  [MOHW](https://mohw.gov.tw/cp-16-84706-1.html) ·
  [Manager Today 2026-08-12](https://www.managertoday.com.tw/articles/view/72724)
- **Human Subjects Research Act** Art. 19: research material must be destroyed after the study unless the subject
  consents or the material is de-linked.
  [MOJ](https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=L0020176)
- **Medical Care Act** Art. 71: hospitals must provide copies of medical records on request.

## Who: the beachhead

MOHW statistics for 2025 (published 2026-07-31):
[MOHW](https://dep.mohw.gov.tw/DOS/cp-5099-87296-113.html)

- **460 hospitals**: 25 medical centres, 3 quasi-medical centres, 71 regional hospitals, 292 district hospitals,
  38 psychiatric hospitals and 28 unaccredited.
- **3.35 M discharges** and **120.4 M outpatient visits** a year. Every discharge creates a chart that may later
  be requested for research, insurance, disputes or copies.
- **First target: the ~100 medical centres and regional hospitals.** They run IRBs and most clinical research,
  and have records offices and information departments that buy on-premises systems.
- **Channel.** ASUS already sells AI to hospitals: its 智慧病歷助手 (smart medical-record assistant) runs
  on-premises at Taipei Veterans General Hospital
  ([NOWnews 2025-12-04](https://www.nownews.com/news/6761482)).
- **Second wave: courts.** The Judicial Yuan already runs an automatic redaction system for e-case files, with
  staff review ([iThome](https://www.ithome.com.tw/news/156693)), which shows the need exists. After courts come
  insurers and government agencies handling information requests.

## Competition (checked 2026-11-12)

| Product | Runs on premises | Traditional Chinese + Taiwan IDs | Scanned images | Price published |
|---|---|---|---|---|
| Microsoft Presidio | yes (open source) | needs custom models and recognisers | basic image redactor | free; "no guarantee" it finds all sensitive data ([GitHub](https://github.com/microsoft/presidio)) |
| Google Cloud Sensitive Data Protection | **no** (cloud API) | has Taiwan ID / passport detectors | yes (OCR) | US$3/GiB inspected after 1 GiB ([pricing](https://cloud.google.com/sensitive-data-protection/pricing)) |
| AWS Comprehend Medical + Textract | **no** | **no**: Comprehend Medical is US English only; Textract OCR has no Chinese ([docs](https://docs.aws.amazon.com/comprehend-medical/latest/dev/comprehendmedical-welcome.html)) | via Textract | US$0.0014 per 100 characters + US$1.50 per 1,000 pages |
| Azure Health Data Services de-identification | **no** | **no** (English, French, German, Spanish) ([docs](https://learn.microsoft.com/en-us/azure/healthcare-apis/deidentification/languages-supported)) | no (text only) | US$0.05/MB |
| Azure AI Language PII | cloud; offline container by commitment | yes, zh-hant text | native documents | US$1 per 1,000 records |
| Private AI (Limina) | yes (container) | **no**: Traditional Mandarin "coming soon" ([docs](https://docs.private-ai.com/languages)) | Core languages only | contact sales |
| John Snow Labs clinical de-ID for PDF | yes / AWS | English | yes | US$95 per host-hour ([AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-ddhtngof3o6fa)) |
| Adobe Acrobat Pro | desktop | manual tool | manual redaction | ~US$20 per user per month |

No product we found combines on-premises operation, Traditional Chinese with Taiwan identifiers, scanned pages
with signatures and seals, and a re-identification check. We found no Taiwanese vendor selling de-identification
to hospitals.

## Value: what the evidence says

- **People miss identifiers.** In Neamatullah et al. 2008 (BMC Med Inform Decis Mak 8:32), single clinicians found
  63–94 % of PHI in clinical notes (mean 81 %). Two people reached 94 % and three reached 98 %, still not all
  ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2526997/)).
- **It is slow.** Manual de-identification took 87 ± 61 s per clinical note (Dorr et al. 2006, Methods Inf Med) for
  text notes. Scanned forms with seals and handwriting are not covered by that figure.
- **Caution.** Machine pre-annotation does not automatically save reviewer time (South et al. 2014). The claim has
  to be measured, which is why we built the `/study` page.
- **Labour cost** (*derived*): clerical support staff earn NT$40,000 a month (MOL wage survey, 2025), about
  NT$227 an hour. Labour per page is therefore small; **the value is risk and capacity, not salary**:
  - a single reviewer's ~81 % recall against RedactAgent's 96.7 % on unseen pages, before human review;
  - a fine of up to NT$15M per uncorrected security failure;
  - research data released in hours instead of a queue.

## Hardware

Intel Arc Pro B70 32 GB: US$949 suggested price at launch (2026-03-25). The ASUS UGen card is €1,799 including VAT
in Germany ([Guru3D](https://www.guru3d.com/story/asus-arc-pro-b70-32gb-arrives-in-europe-at/)). We found no NT$
price for a complete 2x B70 workstation; the deck therefore shows measured running cost per 1,000 pages
instead of a price.

## Not found

- Number of IRBs in Taiwan.
- Annual volume of medical-record copy requests and research data applications.
- Salary of medical-records staff.
- Current NT$ fee ceilings for record copies.
- Effective date of the 2025 PDPA amendment.
