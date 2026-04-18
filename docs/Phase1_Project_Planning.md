# Phase 1: Project Planning

## Objective
Build a Safety Dashboard using 7 years (FY-19 to FY-26) of Tata Steel incident reports to identify safety trends, high-risk departments, contractor safety performance, and year-over-year patterns.

## Data Source
- **Type:** PDF Safety Alert Reports (Orange Stripe = LTI, Red Stripe = Fatal)
- **Location:** Google Drive, organized in year-wise folders
- **Volume:** ~200–400 English PDF reports across 8 fiscal years
- **Owner:** Tata Steel Health & Safety Department

## Key KPIs Defined

| KPI | Description | Source Field |
|-----|-------------|--------------|
| Total Incidents | Count of all LTI + Fatal incidents | Stripe Type |
| Fatal Count | Count of Red Stripe reports | Stripe Type = Red |
| LTI Count | Count of Orange Stripe reports | Stripe Type = Orange |
| Contractor vs Company Split | % incidents by employee type | Employee Type |
| Top Departments | Departments with most incidents | Department |
| Risk Type Distribution | Blue / Yellow / Red risk breakdown | Risk Type |
| YoY Trend | Incidents per fiscal year | Fiscal Year |
| Injury Type Frequency | Most common injuries | Injury Description |
| LTI Free Day Streaks | Dept safety performance | LTI Free Days |
| Vendor Safety Rating | Contractor performance | Vendor Star Rating |

## Dashboard Pages Planned
1. **Overview** — KPI cards, total incidents, fatal vs LTI split
2. **Trend Analysis** — Year-over-year incident trends
3. **Department Risk** — Heatmap of incidents by department
4. **Contractor Analysis** — Vendor ratings vs incident count
5. **Injury Analysis** — Types, body parts, severity
6. **Time Analysis** — Incidents by time of day, shift

## Tools Decided
- **Extraction:** Python (pdfplumber + Google Drive API)
- **Cleaning:** Python (pandas)
- **Analysis:** Jupyter Notebook
- **Dashboard:** Power BI
- **Version Control:** GitHub
