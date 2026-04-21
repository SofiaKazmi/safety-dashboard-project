# 🏭 Industrial Safety Dashboard — Tata Steel (FY2019–FY2026)

> **A end-to-end Data Analytics portfolio project** — from raw PDF safety reports to an interactive Power BI dashboard.  
> Built using Python, Google Drive API, pandas, and Power BI.

---

## 📌 Project Overview

This project analyzes **7 years of real industrial safety incident data** from Tata Steel's Safety Alert reports (FY-19 to FY-26).

The goal is to extract actionable insights from hundreds of PDF safety reports and build a dashboard that answers critical questions:

- Which departments have the highest injury rates?
- Are fatalities increasing or decreasing year over year?
- What are the most common causes of Lost Time Injuries (LTIs)?
- Which contractors have the worst safety records?
- What time of day do most incidents occur?

---

## 🗂️ Project Structure

```
safety-dashboard-project/
│
├── 📁 scripts/
│   ├── extract_safety_data.py      # Phase 2: PDF extraction via Google Drive API
│   ├── clean_data.py               # Phase 3: Data cleaning & preprocessing
│   └── github_push.py              # Utility: Auto-push updates to GitHub
│
├── 📁 data/
│   ├── raw/                        # Original extracted CSV (do not edit)
│   └── cleaned/                    # Cleaned, analysis-ready dataset
│
├── 📁 notebooks/
│   └── exploratory_analysis.ipynb  # Phase 3: EDA & pattern discovery
│
├── 📁 dashboard/
│   └── safety_dashboard.pbix       # Phase 4: Power BI dashboard file
│
├── 📁 docs/
│   ├── Phase1_Project_Planning.md
│   ├── Phase2_Data_Extraction.md
│   └── dashboard_screenshots/      # Screenshots of the final dashboard
│
└── README.md
```

---

## 🚀 Project Phases

| Phase | Description | Status |
|-------|-------------|--------|
| ✅ Phase 1 | Project Planning & KPI Definition | Complete |
| ✅ Phase 2 | Data Extraction (PDF → CSV via Python) | Complete |
| 🔄 Phase 3 | Data Cleaning & Exploratory Analysis | In Progress |
| ⏳ Phase 4 | Power BI Dashboard Development | Upcoming |
| ⏳ Phase 5 | Insights & Storytelling | Upcoming |

---

## 📊 Dataset Summary

| Property | Value |
|----------|-------|
| Source | Tata Steel Safety Alert PDFs |
| Years Covered | FY-2019 to FY-2026 (7 years) |
| Report Types | Orange Stripe (LTI) + Red Stripe (Fatal) |
| Extraction Method | Python + pdfplumber + Google Drive API |
| Total Fields Extracted | 20 fields per incident |

### Fields Extracted

| Field | Description |
|-------|-------------|
| `Stripe Type` | Orange (LTI) or Red (Fatal) |
| `Stripe Number` | Unique incident number per FY |
| `Fiscal Year` | FY-19 through FY-26 |
| `Incident Date` | Date of the incident |
| `Incident Time` | Time of the incident |
| `Location / Plant` | Tata Steel plant/site |
| `Department` | Department where incident occurred |
| `Section` | Sub-section within department |
| `Incident Type` | LTI / Fatal description |
| `Injury Description` | Type of injury sustained |
| `Employee Type` | Company employee or Contractor |
| `Vendor Name` | Contractor company name |
| `Vendor Star Rating` | Contractor safety star rating |
| `Risk Type` | Blue / Yellow / Red risk classification |
| `LTI Free Days` | Days since last LTI in department |
| `Camera Surveillance` | Whether CCTV was present |
| `What Happened` | Incident narrative |
| `Preliminary Findings` | Root cause analysis findings |
| `Recommendations` | Corrective actions recommended |

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.x | Data extraction & cleaning |
| pdfplumber | PDF text extraction |
| pandas | Data manipulation |
| Google Drive API | Accessing source PDF files |
| Jupyter Notebook | Exploratory data analysis |
| Power BI | Dashboard & visualization |
| GitHub | Version control & portfolio |

---

## ⚙️ How to Run

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/safety-dashboard-project.git
cd safety-dashboard-project
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up Google Drive credentials
- Create a Service Account in Google Cloud Console
- Download the JSON key as `credentials.json`
- Place it in the `scripts/` folder
- Share your Drive folder with the service account email

### 4. Run the extraction
```bash
python scripts/extract_safety_data.py
```

### 5. Run the cleaning script
```bash
python scripts/clean_data.py
```

---

## 📈 Key KPIs Tracked in the Dashboard

- **Total Incidents** (by year, type, department)
- **Fatal vs LTI breakdown**
- **Contractor vs Company employee incidents**
- **Most dangerous departments**
- **Risk type distribution**
- **Incident trends over 7 fiscal years**
- **Top injury types**
- **LTI-free day streaks by department**
- **Vendor safety ratings vs incident frequency**

---

## 👤 About This Project

This project was built as part of a transition into **Data Analytics**, applying real-world industrial safety data to demonstrate:
- End-to-end data pipeline development
- API integration (Google Drive)
- PDF parsing and text extraction
- Data cleaning and preprocessing
- Dashboard design and storytelling

---

## 📬 Contact

**Sofia Kazmi**  
📧 sofianksk@gmail.com  
🔗 [LinkedIn](https://linkedin.com/in/YOUR_PROFILE)

---

*Data sourced from internal Tata Steel Safety Alert reports. Used for educational/portfolio purposes.*
