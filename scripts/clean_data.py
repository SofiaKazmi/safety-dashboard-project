"""
=============================================================
  Tata Steel Safety Dashboard — Phase 3: Data Cleaning
  
  Takes the raw extracted CSV and produces a clean,
  analysis-ready dataset for Power BI.
  
  Run from the scripts folder:
      python clean_data.py
=============================================================
"""

import pandas as pd
import numpy as np
import re
import os

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

RAW_CSV     = r"..\data\raw\tata_steel_safety_incidents.csv"
CLEANED_CSV = r"..\data\cleaned\tata_steel_safety_incidents_cleaned.csv"

# ─────────────────────────────────────────────
# STEP 1: Load the raw data
# ─────────────────────────────────────────────

def load_data(path):
    """
    Loads the raw CSV into a pandas DataFrame.
    Tells us immediately what we're working with.
    """
    print("=" * 60)
    print("  Phase 3: Data Cleaning")
    print("=" * 60)
    print(f"\n📂 Loading raw data from: {path}")
    
    df = pd.read_csv(path, encoding="utf-8-sig")
    
    print(f"✅ Loaded successfully!")
    print(f"   Rows    : {len(df)}")
    print(f"   Columns : {len(df.columns)}")
    
    return df


# ─────────────────────────────────────────────
# STEP 2: Quality Report — BEFORE cleaning
# ─────────────────────────────────────────────

def quality_report(df, stage="BEFORE"):
    """
    Shows a snapshot of data quality issues.
    We run this BEFORE and AFTER cleaning to see improvement.
    """
    print(f"\n{'─' * 60}")
    print(f"  DATA QUALITY REPORT — {stage} CLEANING")
    print(f"{'─' * 60}")
    
    # Count "Not Found" values per column
    not_found_counts = (df == "Not Found").sum()
    missing_counts   = df.isnull().sum()
    
    print(f"\n{'Column':<25} {'Not Found':>12} {'Null/Empty':>12}")
    print(f"{'─'*25} {'─'*12} {'─'*12}")
    
    for col in df.columns:
        nf = not_found_counts.get(col, 0)
        nl = missing_counts.get(col, 0)
        if nf > 0 or nl > 0:
            print(f"{col:<25} {nf:>12} {nl:>12}")
    
    print(f"\nStripe Type breakdown:")
    print(df["Stripe Type"].value_counts().to_string())
    
    print(f"\nFiscal Year breakdown:")
    print(df["Fiscal Year"].value_counts().sort_index().to_string())


# ─────────────────────────────────────────────
# STEP 3: Fix "Not Found" values
# ─────────────────────────────────────────────

def fix_not_found(df):
    """
    Replaces all "Not Found" strings with proper NaN (empty).
    This is important because:
    - "Not Found" is a string — pandas treats it as data
    - NaN is a proper null — pandas knows it's missing
    - Power BI handles NaN correctly as blank
    """
    print("\n🔧 Fixing 'Not Found' values...")
    
    before = (df == "Not Found").sum().sum()
    df = df.replace("Not Found", np.nan)
    after  = df.isnull().sum().sum()
    
    print(f"   Replaced {before} 'Not Found' values with proper blanks.")
    return df


# ─────────────────────────────────────────────
# STEP 4: Clean Incident Date
# ─────────────────────────────────────────────

def clean_dates(df):
    """
    The raw dates come in many formats:
    - "30.03.2022"
    - "08.03.2022 Time: 06:45 PM"  ← time got mixed in!
    - "April 16, 2025"
    - "09.08.2018"
    
    We extract just the date and standardize to DD/MM/YYYY.
    """
    print("\n🔧 Cleaning Incident Dates...")
    
    def parse_date(val):
        if pd.isnull(val):
            return np.nan
        
        val = str(val).strip()
        
        # Remove anything after "Time:" if it crept in
        val = re.split(r'[Tt]ime', val)[0].strip()
        
        # Try DD.MM.YYYY or DD-MM-YYYY or DD/MM/YYYY
        match = re.search(r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})', val)
        if match:
            day, month, year = match.groups()
            if len(year) == 2:
                year = "20" + year
            try:
                return pd.to_datetime(f"{day}/{month}/{year}", 
                                      dayfirst=True).strftime("%d/%m/%Y")
            except:
                pass
        
        # Try written format: "April 16, 2025"
        try:
            return pd.to_datetime(val, dayfirst=True).strftime("%d/%m/%Y")
        except:
            return np.nan
    
    before_nulls = df["Incident Date"].isnull().sum()
    df["Incident Date"] = df["Incident Date"].apply(parse_date)
    after_nulls  = df["Incident Date"].isnull().sum()
    
    print(f"   Dates cleaned. Unparseable dates: {after_nulls - before_nulls} new nulls.")
    return df


# ─────────────────────────────────────────────
# STEP 5: Clean Incident Time
# ─────────────────────────────────────────────

def clean_time(df):
    """
    Times came out messy — sometimes doubled:
    "Time : Around 12:15 PM   Around 12:15 PM"
    
    We extract just the first clean time value.
    """
    print("\n🔧 Cleaning Incident Times...")
    
    def parse_time(val):
        if pd.isnull(val):
            return np.nan
        
        val = str(val).strip()
        
        # Extract HH:MM AM/PM pattern
        match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)', val)
        if match:
            return match.group(1).strip()
        
        # Extract 24hr time
        match = re.search(r'(\d{1,2}:\d{2})', val)
        if match:
            return match.group(1).strip()
        
        return np.nan
    
    df["Incident Time"] = df["Incident Time"].apply(parse_time)
    print(f"   Times cleaned.")
    return df


# ─────────────────────────────────────────────
# STEP 6: Add useful derived columns
# ─────────────────────────────────────────────

def add_derived_columns(df):
    """
    Creates new columns that will be very useful in Power BI:
    - Severity       : "Fatal" or "LTI" (cleaner than Stripe Type)
    - FY Number      : 2019, 2020... (for trend charts)
    - Incident Month : January, February... (for seasonal analysis)
    - Incident Year  : 2021, 2022... (actual calendar year)
    - Hour of Day    : 0-23 (for time-of-day analysis)
    - Risk Level     : Extracted from Risk Type field
    """
    print("\n🔧 Adding derived columns...")
    
    # Severity — clean label
    df["Severity"] = df["Stripe Type"].map({
        "Red Stripe":    "Fatal",
        "Orange Stripe": "LTI"
    })
    
    # FY Number — extract year as integer e.g. FY-22 → 2022
    def fy_to_year(fy):
        if pd.isnull(fy):
            return np.nan
        match = re.search(r'(\d{2,4})', str(fy))
        if match:
            yr = int(match.group(1))
            return 2000 + yr if yr < 100 else yr
        return np.nan
    
    df["FY Number"] = df["Fiscal Year"].apply(fy_to_year)
    
    # Incident Month and Year from cleaned date
    def extract_month(date_str):
        try:
            return pd.to_datetime(date_str, dayfirst=True).strftime("%B")
        except:
            return np.nan
    
    def extract_year(date_str):
        try:
            return pd.to_datetime(date_str, dayfirst=True).year
        except:
            return np.nan
    
    def extract_quarter(date_str):
        try:
            month = pd.to_datetime(date_str, dayfirst=True).month
            return f"Q{(month - 1) // 3 + 1}"
        except:
            return np.nan

    df["Incident Month"] = df["Incident Date"].apply(extract_month)
    df["Incident Year"]  = df["Incident Date"].apply(extract_year)
    df["Incident Quarter"] = df["Incident Date"].apply(extract_quarter)
    
    # Hour of Day
    def extract_hour(time_str):
        try:
            t = pd.to_datetime(str(time_str), format="%I:%M %p")
            return t.hour
        except:
            try:
                t = pd.to_datetime(str(time_str), format="%H:%M")
                return t.hour
            except:
                return np.nan
    
    df["Hour of Day"] = df["Incident Time"].apply(extract_hour)
    
    # Shift — based on hour
    def get_shift(hour):
        if pd.isnull(hour):
            return np.nan
        hour = int(hour)
        if 6 <= hour < 14:
            return "A Shift (6AM-2PM)"
        elif 14 <= hour < 22:
            return "B Shift (2PM-10PM)"
        else:
            return "C Shift (10PM-6AM)"
    
    df["Shift"] = df["Hour of Day"].apply(get_shift)
    
    # Risk Level — extract Blue/Yellow/Red from Risk Type
    def extract_risk_level(val):
        if pd.isnull(val):
            return np.nan
        val = str(val).lower()
        if "red" in val:
            return "Red (High)"
        elif "yellow" in val:
            return "Yellow (Medium)"
        elif "blue" in val:
            return "Blue (Low)"
        elif "green" in val:
            return "Green (Very Low)"
        return np.nan
    
    df["Risk Level"] = df["Risk Type"].apply(extract_risk_level)
    
    # LTI Free Days — extract number only
    def extract_lti_days(val):
        if pd.isnull(val):
            return np.nan
        match = re.search(r'(\d+)', str(val).replace(",", ""))
        if match:
            return int(match.group(1))
        return np.nan
    
    df["LTI Free Days (Number)"] = df["LTI Free Days"].apply(extract_lti_days)
    
    print(f"   Added: Severity, FY Number, Incident Month, Incident Year,")
    print(f"          Incident Quarter, Hour of Day, Shift, Risk Level,")
    print(f"          LTI Free Days (Number)")
    return df


# ─────────────────────────────────────────────
# STEP 7: Clean Department names
# ─────────────────────────────────────────────

def clean_departments(df):
    """
    Department names sometimes have extra text, line breaks,
    or slight variations. We trim and standardize them.
    """
    print("\n🔧 Cleaning Department names...")
    
    def clean_dept(val):
        if pd.isnull(val):
            return np.nan
        # Remove extra whitespace and line breaks
        val = re.sub(r'\s+', ' ', str(val)).strip()
        # Remove trailing punctuation
        val = val.rstrip('.,;:')
        # Title case for consistency
        return val.strip()
    
    df["Department"] = df["Department"].apply(clean_dept)
    df["Section"]    = df["Section"].apply(clean_dept)
    
    print(f"   Departments cleaned.")
    print(f"   Unique departments found: {df['Department'].nunique()}")
    return df


# ─────────────────────────────────────────────
# STEP 8: Clean Employee Type
# ─────────────────────────────────────────────

def clean_employee_type(df):
    """
    Standardizes Employee Type to just 'Company' or 'Contractor'.
    """
    print("\n🔧 Cleaning Employee Type...")
    
    def standardize(val):
        if pd.isnull(val):
            return np.nan
        val = str(val).lower()
        if "company" in val:
            return "Company"
        elif "contractor" in val or "contract" in val:
            return "Contractor"
        return np.nan
    
    df["Employee Type"] = df["Employee Type"].apply(standardize)
    print(f"   {df['Employee Type'].value_counts().to_dict()}")
    return df


# ─────────────────────────────────────────────
# STEP 9: Save cleaned data
# ─────────────────────────────────────────────

def save_cleaned(df, path):
    """
    Saves the cleaned DataFrame to the data/cleaned/ folder.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"\n✅ Cleaned data saved to: {path}")
    print(f"   Total rows    : {len(df)}")
    print(f"   Total columns : {len(df.columns)}")


# ─────────────────────────────────────────────
# MAIN — Run all cleaning steps
# ─────────────────────────────────────────────

def main():
    # Load
    df = load_data(RAW_CSV)
    
    # Quality report BEFORE
    quality_report(df, stage="BEFORE")
    
    # Clean step by step
    df = fix_not_found(df)
    df = clean_dates(df)
    df = clean_time(df)
    df = clean_departments(df)
    df = clean_employee_type(df)
    df = add_derived_columns(df)
    
    # Quality report AFTER
    quality_report(df, stage="AFTER")
    
    # Save
    save_cleaned(df, CLEANED_CSV)
    
    # Final summary
    print(f"\n{'=' * 60}")
    print(f"  🎉 Phase 3 Complete!")
    print(f"{'=' * 60}")
    print(f"\n  Your cleaned dataset has:")
    print(f"  • {len(df)} incidents")
    print(f"  • {df['Severity'].value_counts().get('Fatal', 0)} Fatal (Red Stripe)")
    print(f"  • {df['Severity'].value_counts().get('LTI', 0)} LTI (Orange Stripe)")
    print(f"  • {df['FY Number'].nunique()} fiscal years")
    print(f"  • {df['Department'].nunique()} unique departments")
    print(f"  • {len(df.columns)} total columns (ready for Power BI)")
    print(f"\n  Next step: Open Power BI and load the cleaned CSV!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
