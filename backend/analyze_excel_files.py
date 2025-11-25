#!/usr/bin/env python3
"""
Script to analyze Excel files and detect potential issues with structure
"""
import sys
import pandas as pd
from pathlib import Path
from reconciliation import find_header_row, detect_schema, extract_company_name, extract_period

def analyze_excel_file(filepath):
    """Analyze a single Excel file and report structure issues"""
    print(f"\n{'='*80}")
    print(f"Analyzing: {Path(filepath).name}")
    print(f"{'='*80}")

    try:
        # Load workbook
        xl = pd.ExcelFile(filepath)
        print(f"✓ Sheets found: {xl.sheet_names}")

        # Analyze first sheet (usually the data sheet)
        first_sheet = xl.sheet_names[0]
        df_raw = pd.read_excel(filepath, sheet_name=first_sheet, header=None)

        print(f"\n📊 Sheet: '{first_sheet}'")
        print(f"   Dimensions: {df_raw.shape[0]} rows × {df_raw.shape[1]} columns")

        # Try to find header row
        header_row_idx = find_header_row(df_raw)
        if header_row_idx is None:
            print(f"   ❌ PROBLEM: Could not detect header row")
            print(f"   First 10 rows preview:")
            for idx, row in df_raw.head(10).iterrows():
                print(f"   Row {idx}: {row.dropna().tolist()[:5]}")
            return False
        else:
            print(f"   ✓ Header detected at row {header_row_idx}")

        # Try to extract company name
        company_name = extract_company_name(df_raw, header_row_idx)
        if company_name:
            print(f"   ✓ Company name: {company_name}")
        else:
            print(f"   ⚠️  Warning: Could not extract company name")

        # Try to extract period
        period = extract_period(df_raw, header_row_idx)
        if period:
            print(f"   ✓ Period: {period}")
        else:
            print(f"   ⚠️  Warning: Could not extract period")

        # Load with detected header
        df = pd.read_excel(filepath, sheet_name=first_sheet, header=header_row_idx)
        print(f"\n   Column headers: {df.columns.tolist()}")

        # Try schema detection
        schema = detect_schema(df)
        print(f"\n   Schema detection results:")
        for key, col in schema.items():
            status = "✓" if col is not None else "❌"
            print(f"   {status} {key}: {col}")

        # Check for critical missing columns
        critical_cols = ['cuenta', 'fecha', 'debe', 'haber']
        missing_critical = [c for c in critical_cols if schema.get(c) is None]

        if missing_critical:
            print(f"\n   ❌ CRITICAL: Missing required columns: {missing_critical}")
            return False

        # Check data quality
        print(f"\n   Data Quality:")
        print(f"   - Non-empty rows: {df[schema['cuenta']].notna().sum()}")
        print(f"   - Date range: {df[schema['fecha']].min()} to {df[schema['fecha']].max()}")

        # Check for accounts starting with 43 (AR) and 40 (AP)
        accounts = df[schema['cuenta']].astype(str).str.strip()
        ar_count = accounts.str.startswith('43').sum()
        ap_count = accounts.str.startswith('40').sum()
        other_count = (~accounts.str.startswith('43') & ~accounts.str.startswith('40')).sum()

        print(f"   - AR accounts (43*): {ar_count} rows")
        print(f"   - AP accounts (40*): {ap_count} rows")
        print(f"   - Other accounts: {other_count} rows")

        if ar_count == 0 and ap_count == 0:
            print(f"   ⚠️  Warning: No AR (43*) or AP (40*) accounts found!")
            print(f"   Sample accounts: {accounts.dropna().unique()[:10].tolist()}")

        print(f"\n   ✅ File structure is VALID")
        return True

    except Exception as e:
        print(f"\n   ❌ ERROR analyzing file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Get all Excel files
    base_dir = Path(__file__).parent.parent
    excel_files = []

    # Check frontend/public
    public_dir = base_dir / "frontend" / "public"
    if public_dir.exists():
        excel_files.extend(public_dir.glob("*.xlsx"))
        excel_files.extend(public_dir.glob("*.xls"))

    # Filter out temp files
    excel_files = [f for f in excel_files if not f.name.startswith('~$')]

    if not excel_files:
        print("No Excel files found in frontend/public/")
        return

    print(f"Found {len(excel_files)} Excel files to analyze\n")

    results = {}
    for filepath in sorted(excel_files):
        results[filepath.name] = analyze_excel_file(str(filepath))

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    valid_count = sum(1 for v in results.values() if v)
    invalid_count = len(results) - valid_count

    print(f"✅ Valid files: {valid_count}")
    print(f"❌ Invalid files: {invalid_count}")

    if invalid_count > 0:
        print("\nFiles with issues:")
        for filename, is_valid in results.items():
            if not is_valid:
                print(f"  - {filename}")

if __name__ == "__main__":
    main()
