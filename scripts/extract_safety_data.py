"""
=============================================================
  Tata Steel Safety Dashboard — Data Extraction Script
  Extracts all Orange Stripe (LTI) and Red Stripe (Fatal)
  English reports from Google Drive into a clean CSV.
=============================================================

HOW TO RUN THIS ON YOUR MACHINE:
  1. Install libraries:
       pip install pdfplumber pandas google-auth google-api-python-client

  2. Set up Google Drive API credentials:
       - Go to https://console.cloud.google.com/
       - Create a project → Enable "Google Drive API"
       - Create credentials → "Service Account"
       - Download the JSON key file
       - Save it as: credentials.json in the same folder as this script
       - Share your Drive folder with the service account email

  3. Run:
       python extract_safety_data.py
"""

# ─────────────────────────────────────────────
# STEP 1: Import all libraries
# ─────────────────────────────────────────────
import os
import io
import re
import pdfplumber
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ─────────────────────────────────────────────
# STEP 2: Configuration — change these paths
# ─────────────────────────────────────────────

# The folder ID from your Google Drive link
# https://drive.google.com/drive/folders/1vJpRF6p5UWRj3u99Mo1tv925ieINym7z
ROOT_FOLDER_ID = "1vJpRF6p5UWRj3u99Mo1tv925ieINym7z"

# Path to your service account credentials JSON file
CREDENTIALS_FILE = "credentials.json"

# Where to save the final CSV
OUTPUT_CSV = "tata_steel_safety_incidents.csv"


# ─────────────────────────────────────────────
# STEP 3: Connect to Google Drive
# ─────────────────────────────────────────────

def connect_to_drive():
    """
    Authenticates with Google Drive using a service account.
    Returns a Drive API service object.
    """
    print("Connecting to Google Drive...")
    
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=scopes
    )
    
    service = build("drive", "v3", credentials=credentials)
    print("✅ Connected to Google Drive successfully.\n")
    return service


# ─────────────────────────────────────────────
# STEP 4: Find all relevant PDF files
# ─────────────────────────────────────────────

def get_files_in_folder(service, folder_id):
    """
    Lists all files inside a specific Google Drive folder.
    Returns a list of file dictionaries with id, name, mimeType.
    """
    files = []
    page_token = None
    
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token
        ).execute()
        
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        
        if not page_token:
            break
    
    return files


def get_all_target_pdfs(service, root_folder_id):
    """
    Walks all year-wise subfolders (FY-19 to FY-26),
    finds only English Orange Stripe and Red Stripe PDFs.
    
    Rules applied:
    - File title must contain 'Orange Stripe' OR 'Red Stripe' (case-insensitive)
    - File title must NOT contain 'Hindi' or 'hindi'
    - File must be a PDF
    """
    print("Scanning year-wise folders for Orange/Red Stripe English PDFs...")
    all_target_files = []
    
    # Get all year folders inside root
    year_folders = get_files_in_folder(service, root_folder_id)
    
    for folder in year_folders:
        # Only look inside subfolders (skip any loose files at root)
        if folder["mimeType"] != "application/vnd.google-apps.folder":
            continue
        
        folder_name = folder["name"]
        print(f"  📁 Scanning folder: {folder_name}")
        
        # Get all files inside this year folder
        files_in_year = get_files_in_folder(service, folder["id"])
        
        count = 0
        for file in files_in_year:
            name = file["name"]
            name_lower = name.lower()
            
            # Must be a PDF
            if not name_lower.endswith(".pdf"):
                continue
            
            # Must contain orange stripe or red stripe
            is_orange = "orange stripe" in name_lower
            is_red = "red stripe" in name_lower
            if not (is_orange or is_red):
                continue
            
            # Must NOT be Hindi
            if "hindi" in name_lower:
                continue
            
            # Add fiscal year tag for reference
            file["fiscal_year"] = folder_name
            file["stripe_type"] = "Orange Stripe" if is_orange else "Red Stripe"
            all_target_files.append(file)
            count += 1
        
        print(f"     Found {count} relevant files.")
    
    print(f"\n✅ Total files to process: {len(all_target_files)}\n")
    return all_target_files


# ─────────────────────────────────────────────
# STEP 5: Download a PDF from Drive into memory
# ─────────────────────────────────────────────

def download_pdf(service, file_id):
    """
    Downloads a PDF file from Google Drive directly into memory
    (no need to save to disk — faster and cleaner).
    Returns a BytesIO object that pdfplumber can read.
    """
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    
    done = False
    while not done:
        _, done = downloader.next_chunk()
    
    buffer.seek(0)  # Reset pointer to start of file
    return buffer


# ─────────────────────────────────────────────
# STEP 6: Extract text from PDF
# ─────────────────────────────────────────────

def extract_text_from_pdf(pdf_buffer):
    """
    Uses pdfplumber to extract all text from a PDF.
    Joins all pages into one string for easier parsing.
    """
    full_text = ""
    
    with pdfplumber.open(pdf_buffer) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
    
    return full_text


# ─────────────────────────────────────────────
# STEP 7: Parse fields from extracted text
# ─────────────────────────────────────────────

def extract_field(text, *patterns, default="Not Found"):
    """
    Helper function: tries multiple regex patterns on the text,
    returns the first match found, or 'Not Found' if none match.
    
    Why multiple patterns? Because report formatting varies across
    years — sometimes a field is labeled 'Date of Incident:', 
    sometimes just 'Date:'. We try all variants.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Clean up: strip whitespace and remove line breaks
            return match.group(1).strip().replace("\n", " ")
    return default


def parse_report(text, file_name, fiscal_year, stripe_type):
    """
    The main parsing function.
    Takes raw text from a PDF and extracts all structured fields.
    Returns a dictionary — one row for the CSV.
    """
    
    # ── Stripe Number ──────────────────────────────
    # Examples: "Orange Stripe: 91 /FY-22", "Red Stripe: 02/FY26"
    stripe_number = extract_field(
        text,
        r"(?:Orange|Red)\s+Stripe[:\s]+([^\n]+?)(?:\n|$)",
    )
    
    # ── Incident Date ──────────────────────────────
    incident_date = extract_field(
        text,
        r"Date of Incident\s*[:\-]\s*([^\n]+)",
        r"Date\s*[:\-]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    )
    
    # ── Time ──────────────────────────────────────
    incident_time = extract_field(
        text,
        r"Time\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Location/Plant ─────────────────────────────
    # Appears just below the stripe header line
    location_plant = extract_field(
        text,
        r"(?:Tata Steel[^\n]*?|Location\s*[:\-]\s*)([^\n]{5,80})",
        r"Location\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Department ────────────────────────────────
    department = extract_field(
        text,
        r"Department\s*[:\-]\s*([^\n]+)",
        r"Dept\.?\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Section ───────────────────────────────────
    section = extract_field(
        text,
        r"Section\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Incident Type (from Incident field) ────────
    incident_type = extract_field(
        text,
        r"Incident\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Injury Description ────────────────────────
    injury = extract_field(
        text,
        r"Injury\s*[:\-]\s*([^\n]+)",
        r"Injury Type\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Employee Type (Company / Contractor) ───────
    employee_type = "Not Found"
    if "company employee" in text.lower():
        employee_type = "Company"
    elif "contractor employee" in text.lower() or "contract employee" in text.lower():
        employee_type = "Contractor"
    
    # ── Vendor Name ────────────────────────────────
    vendor_name = extract_field(
        text,
        r"Name of the vendor\s*[:\-]\s*([^\n]+)",
        r"vendor\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Vendor Star Rating ─────────────────────────
    vendor_rating = extract_field(
        text,
        r"(?:Current\s+)?Star\s+Rating\s+of\s+the\s+vendor\s*[:\-]\s*([^\n]+)",
        r"Star Rating\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Risk Type ─────────────────────────────────
    # Examples: "Blue Risk (C3, F3)", "Red Risk (C4, L4)"
    risk_type = extract_field(
        text,
        r"Risk\s+Type\s*[:\-]\s*([^\n]+)",
        r"((?:Blue|Yellow|Red|Green)\s+[Rr]isk\s*\([^)]+\))",
    )
    
    # ── LTI Free Days ─────────────────────────────
    lti_free_days = extract_field(
        text,
        r"(?:LTI[- ]free|Incident.*?free)\s+days?\s*[:\-]?\s*([0-9,]+\s*(?:Days?)?)",
        r"Incident\s*\(LTI\)\s+free\s+days\s*[:\-]\s*([^\n]+)",
    )
    
    # ── Camera Surveillance ────────────────────────
    camera = extract_field(
        text,
        r"(?:Under\s+)?[Cc]amera\s+[Ss]urveillance\s*[:\-]\s*([^\n]+)",
    )
    
    # ── What Happened (first 500 chars to keep it concise) ──
    what_happened = extract_field(
        text,
        r"What [Hh]appened[:\-]?\s*([\s\S]{20,500}?)(?=Preliminary|Photograph|$)",
        r"What [Hh]appened\s*([\s\S]{20,300})",
    )
    # Clean up extra whitespace
    what_happened = re.sub(r"\s+", " ", what_happened).strip()[:500]
    
    # ── Preliminary Findings (summary) ────────────
    findings = extract_field(
        text,
        r"Preliminary\s+Findings?\s*[:\-]?\s*([\s\S]{20,600}?)(?=Immediate|Recommendation|$)",
    )
    findings = re.sub(r"\s+", " ", findings).strip()[:500]
    
    # ── Recommendations (summary) ─────────────────
    recommendations = extract_field(
        text,
        r"Recommendations?\s*[:\-]?\s*([\s\S]{20,600}?)(?=Family|$|\Z)",
    )
    recommendations = re.sub(r"\s+", " ", recommendations).strip()[:500]

    # ── Build and return the row dictionary ───────
    return {
        "File Name":            file_name,
        "Fiscal Year":          fiscal_year,
        "Stripe Type":          stripe_type,          # Orange or Red
        "Stripe Number":        stripe_number,
        "Incident Date":        incident_date,
        "Incident Time":        incident_time,
        "Location / Plant":     location_plant,
        "Department":           department,
        "Section":              section,
        "Incident Type":        incident_type,
        "Injury Description":   injury,
        "Employee Type":        employee_type,        # Company or Contractor
        "Vendor Name":          vendor_name,
        "Vendor Star Rating":   vendor_rating,
        "Risk Type":            risk_type,
        "LTI Free Days":        lti_free_days,
        "Camera Surveillance":  camera,
        "What Happened":        what_happened,
        "Preliminary Findings": findings,
        "Recommendations":      recommendations,
    }


# ─────────────────────────────────────────────
# STEP 8: Main pipeline — run everything
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Tata Steel Safety Data Extraction Pipeline")
    print("=" * 60)
    
    # Connect to Drive
    service = connect_to_drive()
    
    # Find all relevant files
    target_files = get_all_target_pdfs(service, ROOT_FOLDER_ID)
    
    if not target_files:
        print("❌ No files found. Check folder ID and credentials.")
        return
    
    # Process each file
    all_rows = []
    errors = []
    
    print("Extracting data from PDFs...\n")
    
    for i, file in enumerate(target_files, 1):
        file_name = file["name"]
        file_id   = file["id"]
        fy        = file["fiscal_year"]
        stripe    = file["stripe_type"]
        
        print(f"  [{i}/{len(target_files)}] {file_name}")
        
        try:
            # Download PDF into memory
            pdf_buffer = download_pdf(service, file_id)
            
            # Extract raw text
            raw_text = extract_text_from_pdf(pdf_buffer)
            
            if not raw_text.strip():
                print(f"    ⚠️  No text extracted (possibly scanned image PDF)")
                errors.append({"file": file_name, "error": "No text extracted"})
                continue
            
            # Parse all fields
            row = parse_report(raw_text, file_name, fy, stripe)
            all_rows.append(row)
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            errors.append({"file": file_name, "error": str(e)})
    
    # ── Save results ──────────────────────────────
    if all_rows:
        df = pd.DataFrame(all_rows)
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        
        print(f"\n{'=' * 60}")
        print(f"✅ Extraction complete!")
        print(f"   Total records extracted : {len(df)}")
        print(f"   Orange Stripe (LTI)     : {len(df[df['Stripe Type'] == 'Orange Stripe'])}")
        print(f"   Red Stripe (Fatal)      : {len(df[df['Stripe Type'] == 'Red Stripe'])}")
        print(f"   Files with errors       : {len(errors)}")
        print(f"   CSV saved at            : {OUTPUT_CSV}")
        print(f"{'=' * 60}")
        
        # Preview first 3 rows
        print("\nPreview (first 3 rows):")
        print(df[["Fiscal Year", "Stripe Type", "Incident Date", 
                   "Department", "Injury Description", "Employee Type"]].head(3).to_string())
    else:
        print("\n❌ No data extracted. Check errors above.")
    
    # Save error log if any
    if errors:
        error_df = pd.DataFrame(errors)
        error_df.to_csv("extraction_errors.csv", index=False)
        print(f"\n⚠️  Error log saved to: extraction_errors.csv")


# ─────────────────────────────────────────────
# Run the script
# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
