"""
=============================================================
  Tata Steel Safety Dashboard — Updated Extraction Script
  Version 2.0 — Handles:
  ✅ Orange Stripe + Red Stripe (English only)
  ✅ PDF files
  ✅ Word (.docx) files
  ✅ Combined PDFs (multiple stripes in one file)
  ✅ All naming variations (Hindi/English detection)
  ✅ FY-20 through FY-26
=============================================================
"""

import os
import io
import re
import pdfplumber
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Try importing docx — for Word files
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️  python-docx not installed. Run: pip install python-docx")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ROOT_FOLDER_ID = "1vJpRF6p5UWRj3u99Mo1tv925ieINym7z"
CREDENTIALS_FILE = "credentials.json"
OUTPUT_CSV = r"..\data\raw\tata_steel_safety_incidents_v2.csv"

# Fiscal years to process (FY-20 to FY-26)
TARGET_FY = ["FY-20", "FY-21", "FY-22", "FY-23", "FY-24", "FY-25", "FY-26"]


# ─────────────────────────────────────────────
# STEP 1: Connect to Google Drive
# ─────────────────────────────────────────────

def connect_to_drive():
    print("Connecting to Google Drive...")
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=scopes
    )
    service = build("drive", "v3", credentials=credentials)
    print("✅ Connected!\n")
    return service


# ─────────────────────────────────────────────
# STEP 2: Get files from folder
# ─────────────────────────────────────────────

def get_files_in_folder(service, folder_id):
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


def is_english_file(name):
    """
    Returns True if file is English (not Hindi).
    Handles many naming variations seen in the data:
    - "Orange Stripe#88_English.pdf" → ✅
    - "Orange Stripe#88 Hindi.pdf"   → ❌
    - "Orange Stripe#88(Hindi).pdf"  → ❌
    - "Orange Stripe#81.pdf"         → ✅ (no language tag = assume English)
    - "Orange stripe#85_Hindi.pdf"   → ❌
    """
    name_lower = name.lower()

    # Explicit Hindi markers
    hindi_markers = ["hindi", "हिंदी", "_hi.", "(hindi)", "-hindi", "hindi."]
    for marker in hindi_markers:
        if marker in name_lower:
            return False

    return True


def is_target_file(name):
    """
    Returns True only for Orange Stripe or Red Stripe files.
    Skips images, guidelines, random docs.
    """
    name_lower = name.lower()

    # Must be orange or red stripe
    is_stripe = ("orange stripe" in name_lower or 
                 "red stripe" in name_lower or
                 "orange stripe" in name_lower.replace("#", " "))
    
    # Must be PDF or DOCX
    is_valid_type = (name_lower.endswith(".pdf") or 
                     name_lower.endswith(".docx"))

    # Skip images
    is_image = any(name_lower.endswith(ext) for ext in 
                   [".jpg", ".jpeg", ".png", ".gif", ".bmp"])

    return is_stripe and is_valid_type and not is_image


def get_all_target_files(service, root_folder_id):
    """
    Scans all year folders and collects English Orange/Red Stripe files.
    """
    print("Scanning year folders...")
    all_files = []

    year_folders = get_files_in_folder(service, root_folder_id)

    for folder in year_folders:
        if folder["mimeType"] != "application/vnd.google-apps.folder":
            continue

        folder_name = folder["name"]

        # Only process target fiscal years
        if folder_name not in TARGET_FY:
            continue

        print(f"  📁 {folder_name}...")
        files = get_files_in_folder(service, folder["id"])

        count = 0
        for f in files:
            name = f["name"]
            if is_target_file(name) and is_english_file(name):
                f["fiscal_year"] = folder_name
                name_lower = name.lower()
                f["stripe_type"] = "Red Stripe" if "red stripe" in name_lower else "Orange Stripe"
                all_files.append(f)
                count += 1

        print(f"     ✅ {count} English Orange/Red Stripe files found")

    print(f"\n📊 Total files to extract: {len(all_files)}\n")
    return all_files


# ─────────────────────────────────────────────
# STEP 3: Download files
# ─────────────────────────────────────────────

def download_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────
# STEP 4: Extract text from PDF or DOCX
# ─────────────────────────────────────────────

def extract_text_from_pdf(buffer):
    """Extract all text from a PDF file."""
    full_text = ""
    try:
        with pdfplumber.open(buffer) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
    except Exception as e:
        print(f"    ⚠️  PDF read error: {e}")
    return full_text


def extract_text_from_docx(buffer):
    """Extract all text from a Word (.docx) file."""
    if not DOCX_AVAILABLE:
        return ""
    try:
        doc = DocxDocument(buffer)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"    ⚠️  DOCX read error: {e}")
        return ""


# ─────────────────────────────────────────────
# STEP 5: Split combined files into sections
# ─────────────────────────────────────────────

def split_into_incidents(full_text, file_name, fiscal_year, stripe_type):
    """
    KEY FUNCTION: Splits a combined PDF/DOCX containing multiple
    incidents into separate sections — one per incident.

    Example: A file with Orange Stripe 01, 02, 03 inside becomes
    3 separate rows in our dataset.

    Detection: Each new incident starts with a line like:
    "Health & Safety Safety Alert Orange Stripe: XX /FY-XX"
    or "Safety Alert Red Stripe: XX/FY-XX"
    """

    # Pattern that marks the start of a new incident section
    split_pattern = re.compile(
        r'(?:Health\s*&\s*Safety\s*)?Safety\s*Alert\s*'
        r'(?:Orange|Red)\s*Stripe[:\s#]+\s*\d+',
        re.IGNORECASE
    )

    # Find all positions where a new incident starts
    matches = list(split_pattern.finditer(full_text))

    if len(matches) <= 1:
        # Single incident — return as one section
        return [full_text]

    # Multiple incidents found — split into sections
    sections = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        section = full_text[start:end].strip()
        if len(section) > 100:  # Skip tiny fragments
            sections.append(section)

    print(f"    📄 Found {len(sections)} incidents in this file")
    return sections


# ─────────────────────────────────────────────
# STEP 6: Parse fields from each incident section
# ─────────────────────────────────────────────

def extract_field(text, *patterns, default=""):
    """Try multiple regex patterns, return first match."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip().replace("\n", " ")
            value = re.sub(r'\s+', ' ', value).strip()
            return value[:300]  # Cap length
    return default


def parse_incident(text, file_name, fiscal_year, stripe_type):
    """
    Parses all 20 fields from a single incident text block.
    Returns a dictionary — one row for the CSV.
    """

    # Stripe Number
    stripe_number = extract_field(
        text,
        r'(?:Orange|Red)\s+Stripe[:\s#]+([0-9]+\s*/?\s*FY[-\s]?\d+)',
        r'Stripe[:\s#]+([0-9]+\s*/?\s*FY[-\s]?\d+)',
    )

    # Incident Date
    incident_date = extract_field(
        text,
        r'Date\s+of\s+Incident\s*[:\-]\s*([^\n]{4,30})',
        r'Date\s*[:\-]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
        r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})',
    )

    # Time
    incident_time = extract_field(
        text,
        r'Time\s*[:\-]\s*([^\n]{3,20})',
    )
    # Clean duplicate time values
    if incident_time:
        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)', incident_time)
        if time_match:
            incident_time = time_match.group(1).strip()

    # Location / Plant
    location_plant = extract_field(
        text,
        r'Location\s*[:\-]\s*([^\n]{5,100})',
        r'(?:Tata\s+(?:Steel|Metaliks)[^\n]{0,60})',
    )

    # Department
    department = extract_field(
        text,
        r'Department\s*[:\-]\s*([^\n]{3,80})',
        r'Dept\.?\s*[:\-]\s*([^\n]{3,80})',
    )

    # Section
    section = extract_field(
        text,
        r'Section\s*[:\-]\s*([^\n]{3,80})',
    )

    # Incident Type
    incident_type = extract_field(
        text,
        r'Incident\s*[:\-]\s*([^\n]{5,150})',
    )

    # Injury
    injury = extract_field(
        text,
        r'Injury\s*[:\-]\s*([^\n]{3,150})',
        r'Injuries?\s*[:\-]\s*([^\n]{3,150})',
    )

    # Employee Type
    employee_type = ""
    text_lower = text.lower()
    if "company employee" in text_lower:
        employee_type = "Company"
    elif "contractor employee" in text_lower or "contract employee" in text_lower:
        employee_type = "Contractor"

    # Vendor Name
    vendor_name = extract_field(
        text,
        r'Name\s+of\s+the\s+[Vv]endor\s*[:\-]\s*([^\n]{3,100})',
        r'[Vv]endor\s+[Nn]ame\s*[:\-]\s*([^\n]{3,100})',
    )

    # Vendor Star Rating
    vendor_rating = extract_field(
        text,
        r'(?:Current\s+)?Star\s+Rating\s+of\s+the\s+[Vv]endor\s*[:\-]\s*([^\n]{1,20})',
        r'Star\s+[Rr]ating\s*[:\-]\s*([^\n]{1,20})',
    )

    # Risk Type
    risk_type = extract_field(
        text,
        r'Risk\s+Type\s*[:\-]\s*([^\n]{3,50})',
        r'((?:Blue|Yellow|Red|Green)\s+[Rr]isk\s*\(?[^)]*\)?)',
    )

    # LTI Free Days
    lti_free_days = extract_field(
        text,
        r'(?:Incident\s*\(?LTI\)?\s*)?[Ff]ree\s+[Dd]ays?\s*(?:of\s+the\s+department\s*)?[:\-]?\s*([0-9,]+\s*(?:[Dd]ays?)?)',
        r'LTI.{0,20}free.{0,10}days?\s*[:\-]\s*([^\n]{1,30})',
    )

    # Camera Surveillance
    camera = extract_field(
        text,
        r'(?:Under\s+)?[Cc]amera\s+[Ss]urveillance\s*[:\-]\s*([^\n]{1,10})',
    )

    # What Happened — first 500 chars
    what_happened = extract_field(
        text,
        r'What\s+[Hh]appened[:\-]?\s*([\s\S]{20,600}?)(?=Preliminary|Photograph|$)',
    )
    what_happened = re.sub(r'\s+', ' ', what_happened).strip()[:500]

    # Preliminary Findings
    findings = extract_field(
        text,
        r'Preliminary\s+Findings?[:\-]?\s*([\s\S]{20,600}?)(?=Immediate|Recommendation|$)',
    )
    findings = re.sub(r'\s+', ' ', findings).strip()[:500]

    # Recommendations
    recommendations = extract_field(
        text,
        r'Recommendations?\s*[:\-]?\s*([\s\S]{20,600}?)(?=Family|$|\Z)',
    )
    recommendations = re.sub(r'\s+', ' ', recommendations).strip()[:500]

    return {
        "File Name":            file_name,
        "Fiscal Year":          fiscal_year,
        "Stripe Type":          stripe_type,
        "Stripe Number":        stripe_number,
        "Incident Date":        incident_date,
        "Incident Time":        incident_time,
        "Location / Plant":     location_plant,
        "Department":           department,
        "Section":              section,
        "Incident Type":        incident_type,
        "Injury Description":   injury,
        "Employee Type":        employee_type,
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
# STEP 7: Main pipeline
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Tata Steel Safety Extraction — Version 2.0")
    print("  FY-20 to FY-26 | English Only | PDF + DOCX")
    print("=" * 60)

    # Install python-docx if needed
    if not DOCX_AVAILABLE:
        print("\n⚠️  Installing python-docx...")
        os.system("pip install python-docx")

    service = connect_to_drive()
    target_files = get_all_target_files(service, ROOT_FOLDER_ID)

    if not target_files:
        print("❌ No files found. Check credentials and folder access.")
        return

    all_rows = []
    errors = []

    print("Extracting data...\n")

    for i, file in enumerate(target_files, 1):
        file_name = file["name"]
        file_id   = file["id"]
        fy        = file["fiscal_year"]
        stripe    = file["stripe_type"]
        mime      = file["mimeType"]

        print(f"  [{i}/{len(target_files)}] {file_name[:60]}")

        try:
            # Download
            buffer = download_file(service, file_id)

            # Extract text based on file type
            if file_name.lower().endswith(".docx"):
                raw_text = extract_text_from_docx(buffer)
            else:
                raw_text = extract_text_from_pdf(buffer)

            if not raw_text or len(raw_text.strip()) < 50:
                print(f"    ⚠️  No text extracted (scanned image?)")
                errors.append({"file": file_name, "error": "No text"})
                continue

            # Split combined files into individual incidents
            sections = split_into_incidents(raw_text, file_name, fy, stripe)

            # Parse each incident section
            for section in sections:
                row = parse_incident(section, file_name, fy, stripe)
                all_rows.append(row)

        except Exception as e:
            print(f"    ❌ Error: {e}")
            errors.append({"file": file_name, "error": str(e)})

    # Save results
    if all_rows:
        os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
        df = pd.DataFrame(all_rows)
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

        print(f"\n{'=' * 60}")
        print(f"✅ Extraction Complete!")
        print(f"   Total incidents extracted : {len(df)}")
        print(f"   Orange Stripe (LTI)       : {len(df[df['Stripe Type'] == 'Orange Stripe'])}")
        print(f"   Red Stripe (Fatal)         : {len(df[df['Stripe Type'] == 'Red Stripe'])}")
        print(f"   Files with errors          : {len(errors)}")
        print(f"   CSV saved at               : {OUTPUT_CSV}")
        print(f"\n  Breakdown by Fiscal Year:")
        print(df["Fiscal Year"].value_counts().sort_index().to_string())
        print(f"{'=' * 60}")

    if errors:
        pd.DataFrame(errors).to_csv(
            r"..\data\raw\extraction_errors_v2.csv", index=False
        )
        print(f"\n⚠️  Error log: data/raw/extraction_errors_v2.csv")


if __name__ == "__main__":
    main()
    