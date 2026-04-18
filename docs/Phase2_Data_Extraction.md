# Phase 2: Data Extraction

## Approach
All PDF reports are stored in Google Drive in year-wise folders (FY-19 to FY-26).
We use the Google Drive API + pdfplumber to download and extract text from each file.

## Filter Logic Applied
- ✅ Include: Files with "Orange Stripe" in the name (LTI reports)
- ✅ Include: Files with "Red Stripe" in the name (Fatal reports)
- ❌ Exclude: Files with "Hindi" in the name (duplicate translations)
- ❌ Exclude: Guidelines, policy documents, near-miss reports

## Fields Extracted (20 per incident)

| # | Field | Extraction Method |
|---|-------|-------------------|
| 1 | File Name | From Drive metadata |
| 2 | Fiscal Year | From folder name |
| 3 | Stripe Type | From file name |
| 4 | Stripe Number | Regex on PDF text |
| 5 | Incident Date | Regex: "Date of Incident:" |
| 6 | Incident Time | Regex: "Time:" |
| 7 | Location / Plant | Regex: header line |
| 8 | Department | Regex: "Department:" |
| 9 | Section | Regex: "Section:" |
| 10 | Incident Type | Regex: "Incident:" |
| 11 | Injury Description | Regex: "Injury:" |
| 12 | Employee Type | Keyword: "company"/"contractor" |
| 13 | Vendor Name | Regex: "Name of the vendor:" |
| 14 | Vendor Star Rating | Regex: "Star Rating of the vendor:" |
| 15 | Risk Type | Regex: "Risk Type:" |
| 16 | LTI Free Days | Regex: "LTI-free days:" |
| 17 | Camera Surveillance | Regex: "Camera Surveillance:" |
| 18 | What Happened | Regex: "What Happened" section |
| 19 | Preliminary Findings | Regex: "Preliminary Findings" section |
| 20 | Recommendations | Regex: "Recommendations" section |

## Script
`scripts/extract_safety_data.py`

## Output
`data/raw/tata_steel_safety_incidents.csv`

## Known Limitations
- Some older PDFs (FY-19) may be scanned images — these will show "No text extracted"
- Date formats vary across years (DD.MM.YYYY, DD-MM-YYYY, etc.) — handled in Phase 3 cleaning
- Some fields may show "Not Found" if the report format deviates from the standard template
