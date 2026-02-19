import pandas as pd
import numpy as np
import re
import io
from typing import List, Dict, Tuple, Optional, Any
from difflib import SequenceMatcher

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    lower_map = {c: re.sub(r"\s+", " ", str(c)).strip().lower() for c in df.columns}
    df.rename(columns=lower_map, inplace=True)
    return df

def find_col(df: pd.DataFrame, patterns: List[str]) -> Optional[str]:
    for p in patterns:
        for c in df.columns:
            if re.search(p, c, flags=re.IGNORECASE):
                return c
    return None

def find_cols(df: pd.DataFrame, patterns: List[str]) -> List[str]:
    out = []
    for c in df.columns:
        for p in patterns:
            if re.search(p, c, flags=re.IGNORECASE):
                out.append(c)
                break
    return list(dict.fromkeys(out))

def find_header_row(df_head: pd.DataFrame) -> int:
    best_idx = 0
    max_score = 0
    # Extended keywords in Spanish, Catalan and English
    keywords = [
        r"fecha", r"data", r"date",
        r"cuenta", r"compte", r"account",
        r"debe", r"deure", r"debit", r"cargo",
        r"haber", r"haver", r"credit", r"abono",
        r"saldo", r"balance",
        r"descripci[oó]n", r"descripc", r"tercero", r"tercer",
        r"importe", r"import", r"amount",
        r"documento", r"document", r"factura", r"invoice"
    ]

    # print(f"[DEBUG] Searching for header row in first 30 rows...")

    for idx, row in df_head.iterrows():
        row_str = " ".join([str(x).lower() for x in row.values])
        score = 0
        for kw in keywords:
            if re.search(kw, row_str):
                score += 1
        # if score > 0:
        #     print(f"[DEBUG] Row {idx} score: {score} - Contains: {row_str[:100]}...")
        if score > max_score:
            max_score = score
            best_idx = idx

    # print(f"[DEBUG] Header row detected at index {best_idx} with score {max_score}")

    if max_score < 2:
        # print(f"[DEBUG] Warning: Low confidence header detection (score < 2), defaulting to row 0")
        return 0
    return best_idx

def detect_schema(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    # print(f"[DEBUG] Detecting schema from columns: {list(df.columns)[:10]}...")
    # Extended patterns for Spanish, Catalan and English
    date_col   = find_col(df, [r"fecha", r"data", r"date", r"f\.?contab", r"asiento.*fecha"])
    cuenta_col = find_col(df, [r"cuenta", r"compte", r"cta", r"account", r"cod.*cta"])
    debe_col   = find_col(df, [r"debe", r"deure", r"cargo", r"càrrec", r"debit"])
    haber_col  = find_col(df, [r"haber", r"haver", r"abono", r"abonament", r"credit", r"crèdit"])
    saldo_col  = find_col(df, [r"saldo", r"balance"])
    tercero_col= find_col(df, [r"descripci[oó]n", r"descripc", r"proveedor", r"proveïdor", r"cliente", r"client", r"tercero", r"tercer", r"contrapartida", r"nombre", r"nom", r"raz[oó]n\s*social"])
    doc_col    = find_col(df, [r"factura", r"documento", r"document", r"n[ºo]\s*doc", r"n[úu]mero", r"número", r"ref"])
    concepto_col=find_col(df, [r"concepto", r"concepte", r"desc", r"glosa", r"detalle", r"detall", r"narr"])
    # Detect pre-reconciled column (Punt. / Punteado / Check / Reconciled)
    punt_col   = find_col(df, [r"punt\.?$", r"punteado", r"puntejat", r"check", r"reconciled", r"conciliado", r"conciliat"])

    schema = {
        "fecha": date_col, "cuenta": cuenta_col, "debe": debe_col, "haber": haber_col,
        "saldo": saldo_col, "tercero": tercero_col, "documento": doc_col, "concepto": concepto_col,
        "punt": punt_col
    }

    # Fallback for headless sheets
    if not (schema["fecha"] and schema["cuenta"] and (schema["debe"] or schema["haber"])):
        # print(f"[DEBUG] Schema detection failed, using fallback. Detected schema: {schema}")
        if len(df.columns) >= 9:
            cols = list(df.columns)
            schema = {
                "cuenta": cols[0],
                "tercero": cols[1],
                "punt": cols[2] if len(cols) > 2 else None,  # Punt. is typically column 3
                "fecha": cols[3],
                "concepto": cols[4],
                "documento": cols[5],
                "debe": cols[6],
                "haber": cols[7],
                "saldo": cols[8]
            }
    return schema

def extract_invoice_references(text: str) -> List[str]:
    """Extract potential invoice references from text using common patterns, including ranges"""
    if not text:
        return []

    text = str(text).upper()
    references = []

    # First, detect ranges of invoices (e.g., "Fact 1234-1236" or "Fra. 1000 a 1003")
    range_patterns = [
        r'(?:FACT|FRA|FAC|INV)?\.?\s*(\d+)\s*[-A]\s*(\d+)',  # Fact 1234-1236, Fra 1000 a 1003
        r'(\d+)\s*[-/]\s*(\d+)(?:\s*Y\s*(\d+))?',           # 1234-1236 y 1238
    ]

    for pattern in range_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) >= 2:
                start_num = match[0]
                end_num = match[1]

                # Extract numeric parts for range expansion
                try:
                    start = int(re.search(r'\d+', str(start_num)).group())
                    end = int(re.search(r'\d+', str(end_num)).group())

                    # If end is shorter, it might be abbreviated (1234-36 means 1234-1236)
                    if len(str(end)) < len(str(start)):
                        prefix = str(start)[:-len(str(end))]
                        end = int(prefix + str(end))

                    # Generate all numbers in range (limit to 10 to avoid excessive expansion)
                    if 0 < (end - start) <= 10:
                        for num in range(start, end + 1):
                            references.append(str(num))
                    else:
                        # If range is too large, just add endpoints
                        references.append(str(start))
                        references.append(str(end))

                    # Add third number if present (e.g., "1234-1236 y 1238")
                    if len(match) > 2 and match[2]:
                        references.append(str(match[2]))

                except (ValueError, AttributeError):
                    # If parsing fails, add as-is
                    references.extend([str(m) for m in match if m])

    # Detect multiple comma-separated references (e.g., "Fact 123, 456, 789")
    multi_patterns = [
        r'(?:FACT|FRA|FAC|INV)?\.?\s*((?:\d+\s*,\s*)+\d+)',  # Fact 123, 456, 789
    ]

    for pattern in multi_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Split by comma and extract numbers
            parts = match.split(',')
            for part in parts:
                num_match = re.search(r'\d+', part.strip())
                if num_match:
                    references.append(num_match.group())

    # Common invoice patterns (existing)
    patterns = [
        r'A/(\d+)',                    # A/337748 (specific format from real data)
        r'INV[-/\s]?(\d+)',           # INV-123, INV/123, INV 123
        r'F[-/\s]?(\d+)',              # F-123, F/123, F 123
        r'FAC[-/\s]?(\d+)',            # FAC-123, FACTURA 123
        r'FRA\.?\s*(\d+)',             # FRA. 123, FRA 123 (from "PAGO FRA.")
        r'FACTURA\s+(\d+)',            # FACTURA 2144642
        r'(\d+)[-/]\d{4}',             # 123-2024, 123/2024
        r'(\d{5,})',                   # Any 5+ digit number (like 2144642)
        r'[A-Z]{1,3}[-/](\d+)',        # A/123, AB/123, ABC-123
        r'#(\d+)',                     # #123
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        references.extend(matches)

    # Also include the full text split by common separators for partial matching
    # This helps when invoice ref doesn't follow standard patterns
    text_parts = re.split(r'[\s,;/\-]+', text)
    references.extend([p for p in text_parts if len(p) >= 2 and not p.isspace()])

    # Remove duplicates while preserving order
    seen = set()
    unique_refs = []
    for ref in references:
        if ref and ref not in seen:
            seen.add(ref)
            unique_refs.append(ref)

    return unique_refs

def fuzzy_match_score(str1: str, str2: str, threshold: float = 0.8) -> float:
    """Calculate fuzzy match score between two strings (0-1)"""
    if not str1 or not str2:
        return 0.0

    str1 = str(str1).upper().strip()
    str2 = str(str2).upper().strip()

    # Exact match
    if str1 == str2:
        return 1.0

    # One string contains the other
    if str1 in str2 or str2 in str1:
        return 0.9

    # Use SequenceMatcher for fuzzy matching
    ratio = SequenceMatcher(None, str1, str2).ratio()

    # Check if strings are similar after removing common prefixes
    for prefix in ['INV', 'F', 'FAC', '#']:
        s1_clean = str1.replace(prefix, '').strip('-/ ')
        s2_clean = str2.replace(prefix, '').strip('-/ ')
        if s1_clean and s2_clean:
            clean_ratio = SequenceMatcher(None, s1_clean, s2_clean).ratio()
            ratio = max(ratio, clean_ratio)

    return ratio if ratio >= threshold else 0.0

def extract_company_name(df_head: pd.DataFrame, header_row: int) -> Optional[str]:
    """Extract company name from the rows before the header"""
    if header_row == 0:
        return None
    
    # Look at rows before the header
    for idx in range(min(header_row, 10)):
        row = df_head.iloc[idx]
        # Get non-empty cells
        non_empty = [str(val).strip() for val in row.values if pd.notna(val) and str(val).strip()]
        
        # Look for patterns like "Empresa: COMPANY NAME" or "Company: NAME"
        for val in non_empty:
            # Check for explicit company patterns
            empresa_match = re.search(r'(?:Empresa|Company|Razón Social|Razon Social|Cliente|Client):\s*(.+)', val, flags=re.IGNORECASE)
            if empresa_match:
                company_name = empresa_match.group(1).strip()
                if company_name and len(company_name) > 2:
                    return company_name
        
        # Fallback: look for potential company names (longer strings, not numbers, not common header keywords)
        for val in non_empty:
            # Skip if it looks like a header keyword or is too short
            if len(val) < 3 or len(val) > 100:
                continue
            # Skip if it's mostly numbers
            if sum(c.isdigit() for c in val) > len(val) * 0.5:
                continue
            # Skip common non-company words and patterns
            if re.search(r'fecha|date|cuenta|account|debe|haber|saldo|balance|total|período|periodo|period', val, flags=re.IGNORECASE):
                continue
            # Skip if it starts with common prefixes that aren't company names
            if re.match(r'^(de |from |to |a )', val, flags=re.IGNORECASE):
                continue
            # This looks like a potential company name
            return val
    
    return None


def extract_period(df_head: pd.DataFrame, header_row: int) -> Optional[str]:
    """Extract period information from the rows before the header"""
    if header_row == 0:
        return None

    # Look at rows before the header
    for idx in range(min(header_row, 10)):
        row = df_head.iloc[idx]
        # Get non-empty cells
        non_empty = [str(val).strip() for val in row.values if pd.notna(val) and str(val).strip()]

        # Look for patterns like "Período: de 01/01/2025 a 31/12/2025"
        for val in non_empty:
            # Check for explicit period patterns
            period_match = re.search(r'(?:Período|Periodo|Period):\s*(.+)', val, flags=re.IGNORECASE)
            if period_match:
                period_text = period_match.group(1).strip()
                if period_text and len(period_text) > 5:
                    # Try to extract a cleaner format like "1T 2025" or "Q1 2025"
                    # First check if it's already in short format
                    if re.search(r'\d[TQ]\s*\d{4}', period_text, flags=re.IGNORECASE):
                        return period_text

                    # Try to extract from date range format: "de DD/MM/YYYY a DD/MM/YYYY"
                    date_range_match = re.search(r'de\s+(\d{1,2})/(\d{1,2})/(\d{4})\s+a\s+(\d{1,2})/(\d{1,2})/(\d{4})', period_text, flags=re.IGNORECASE)
                    if date_range_match:
                        start_month = int(date_range_match.group(2))
                        end_month = int(date_range_match.group(5))
                        year = date_range_match.group(6)

                        # Determine quarter based on months
                        if start_month == 1 and end_month in [3, 12]:
                            quarter = "1T" if end_month == 3 else "Anual"
                        elif start_month == 4 and end_month == 6:
                            quarter = "2T"
                        elif start_month == 7 and end_month == 9:
                            quarter = "3T"
                        elif start_month == 10 and end_month == 12:
                            quarter = "4T"
                        else:
                            # Return the full date range if we can't determine quarter
                            return period_text

                        return f"{quarter} {year}" if quarter != "Anual" else f"Anual {year}"

                    # Return as is if no pattern matched
                    return period_text

    return None


class Reconciler:
    def __init__(self, tol: float = 0.01):
        self.tol = tol
        self.open_invoices = []  # List of dicts
        self.out_rows = []
        self.set_id = 0

    def add_invoice(self, row):
        # Extract multiple possible references from document field
        doc_refs = []
        if row["doc"]:
            doc_refs = extract_invoice_references(str(row["doc"]))

        self.open_invoices.append({
            "doc_key": row["doc_key"],
            "remaining": float(row["neto_norm"]),
            "fecha": row["fecha"],
            "row_id": row["row_id"],
            "doc_ref": str(row["doc"]).lower().strip() if row["doc"] else "",
            "doc_refs": doc_refs,  # Multiple possible references
            "original_row": row
        })

    def process_payment(self, payment_row, tercero):
        payment_amount = -float(payment_row["neto_norm"])
        payment_left = payment_amount
        payment_concept = str(payment_row["concepto"]).lower() if payment_row["concepto"] else ""
        payment_date = payment_row["fecha"]

        # Extract potential references from payment concept
        payment_refs = extract_invoice_references(payment_concept) if payment_concept else []

        matches = [] # List of (invoice_index, amount_to_take, method, confidence)

        # --- Phase 1: Enhanced Reference Match with Fuzzy Logic ---
        if payment_left > self.tol and (payment_concept or payment_row.get("doc")):
            best_ref_matches = []

            for idx, inv in enumerate(self.open_invoices):
                if inv["remaining"] <= self.tol:
                    continue

                max_score = 0.0

                # Check exact substring match (legacy behavior for compatibility)
                if len(inv["doc_ref"]) >= 3 and inv["doc_ref"] in payment_concept:
                    max_score = 0.95

                # Check against extracted references with fuzzy matching
                for inv_ref in inv["doc_refs"]:
                    for pay_ref in payment_refs:
                        score = fuzzy_match_score(inv_ref, pay_ref, threshold=0.7)
                        if score > max_score:
                            max_score = score

                if max_score >= 0.7:  # Threshold for considering a reference match
                    best_ref_matches.append((idx, max_score))

            # Sort by score and process best matches first
            best_ref_matches.sort(key=lambda x: x[1], reverse=True)

            for idx, score in best_ref_matches:
                if payment_left <= self.tol:
                    break
                inv = self.open_invoices[idx]
                if inv["remaining"] > self.tol:
                    take = min(inv["remaining"], payment_left)
                    # Confidence: 95-100% for perfect match, 80-95% for fuzzy match
                    confidence = min(95 + (score * 5), 100) if score >= 0.9 else 80 + (score * 15)
                    matches.append((idx, take, "Reference", confidence))
                    inv["remaining"] -= take
                    payment_left -= take

        # --- Phase 2: Exact Amount Match ---
        if payment_left > self.tol:
            candidates = []
            for idx, inv in enumerate(self.open_invoices):
                if inv["remaining"] <= self.tol:
                    continue
                if abs(inv["remaining"] - payment_left) <= self.tol:
                    candidates.append(idx)

            if candidates:
                # Prefer candidates closer in date
                if payment_date and payment_date != pd.NaT:
                    candidates.sort(key=lambda idx: abs((self.open_invoices[idx]["fecha"] - payment_date).days)
                                    if self.open_invoices[idx]["fecha"] != pd.NaT else 999999)

                best_match_idx = candidates[0]
                take = payment_left
                # Higher confidence if dates are close
                days_diff = abs((self.open_invoices[best_match_idx]["fecha"] - payment_date).days) if payment_date != pd.NaT and self.open_invoices[best_match_idx]["fecha"] != pd.NaT else 999
                confidence = 90 if days_diff <= 30 else 85 if days_diff <= 60 else 80
                matches.append((best_match_idx, take, "Exact", confidence))
                self.open_invoices[best_match_idx]["remaining"] -= take
                payment_left -= take

        # --- Phase 3: Combined Amount Match (Multiple Invoices) ---
        # Try to find combinations of 2-3 invoices that sum to the payment amount
        if payment_left > self.tol:
            # Get all open invoices with their amounts
            open_inv_indices = []
            for idx, inv in enumerate(self.open_invoices):
                if inv["remaining"] > self.tol:
                    open_inv_indices.append((idx, inv["remaining"]))

            # Try combinations of 2 invoices first
            if len(open_inv_indices) >= 2:
                for i in range(len(open_inv_indices)):
                    for j in range(i + 1, len(open_inv_indices)):
                        idx1, amount1 = open_inv_indices[i]
                        idx2, amount2 = open_inv_indices[j]
                        combined_amount = amount1 + amount2

                        # Check if combination matches payment (within 1% tolerance)
                        if abs(combined_amount - payment_left) <= max(self.tol, payment_left * 0.01):
                            # Found a match! Process both invoices
                            confidence = 85  # High confidence for exact combination

                            # Match first invoice
                            take1 = min(self.open_invoices[idx1]["remaining"], amount1)
                            matches.append((idx1, take1, "CombinedAmount", confidence))
                            self.open_invoices[idx1]["remaining"] -= take1
                            payment_left -= take1

                            # Match second invoice
                            take2 = min(self.open_invoices[idx2]["remaining"], amount2)
                            matches.append((idx2, take2, "CombinedAmount", confidence))
                            self.open_invoices[idx2]["remaining"] -= take2
                            payment_left -= take2
                            break
                    if payment_left <= self.tol:
                        break

            # Rebuild open_inv_indices after 2-combo matching (some may have been consumed)
            if payment_left > self.tol:
                open_inv_indices = []
                for idx, inv in enumerate(self.open_invoices):
                    if inv["remaining"] > self.tol:
                        open_inv_indices.append((idx, inv["remaining"]))

            # Try combinations of 3 invoices if still unmatched
            if payment_left > self.tol and len(open_inv_indices) >= 3:
                for i in range(len(open_inv_indices)):
                    for j in range(i + 1, len(open_inv_indices)):
                        for k in range(j + 1, len(open_inv_indices)):
                            idx1, amount1 = open_inv_indices[i]
                            idx2, amount2 = open_inv_indices[j]
                            idx3, amount3 = open_inv_indices[k]
                            combined_amount = amount1 + amount2 + amount3

                            # Check if combination matches payment
                            if abs(combined_amount - payment_left) <= max(self.tol, payment_left * 0.01):
                                confidence = 80  # Good confidence for 3-invoice combination

                                # Match all three invoices
                                for idx, amount in [(idx1, amount1), (idx2, amount2), (idx3, amount3)]:
                                    if self.open_invoices[idx]["remaining"] > self.tol:
                                        take = min(self.open_invoices[idx]["remaining"], amount)
                                        matches.append((idx, take, "CombinedAmount", confidence))
                                        self.open_invoices[idx]["remaining"] -= take
                                        payment_left -= take
                                break
                        if payment_left <= self.tol:
                            break
                    if payment_left <= self.tol:
                        break

        # --- Phase 4: Date Proximity Match ---
        if payment_left > self.tol and payment_date and payment_date != pd.NaT:
            proximity_candidates = []

            for idx, inv in enumerate(self.open_invoices):
                if inv["remaining"] <= self.tol:
                    continue

                inv_date = inv["fecha"]
                if inv_date and inv_date != pd.NaT:
                    days_diff = (payment_date - inv_date).days
                    # Payment within 0-45 days after invoice
                    if 0 <= days_diff <= 45:
                        # Check if amount is reasonably close (within 20%)
                        amount_ratio = payment_left / inv["remaining"] if inv["remaining"] > 0 else 0
                        if 0.8 <= amount_ratio <= 1.2:
                            proximity_candidates.append((idx, days_diff, amount_ratio))

            if proximity_candidates:
                # Sort by days difference (prefer closer dates)
                proximity_candidates.sort(key=lambda x: x[1])
                best_idx, days_diff, amount_ratio = proximity_candidates[0]

                if self.open_invoices[best_idx]["remaining"] > self.tol:
                    take = min(self.open_invoices[best_idx]["remaining"], payment_left)
                    # Confidence based on date proximity and amount match
                    date_confidence = 75 - (days_diff * 0.5)  # Max 75, decreases with days
                    amount_confidence = 70 if 0.95 <= amount_ratio <= 1.05 else 65
                    confidence = min(date_confidence, amount_confidence)
                    matches.append((best_idx, take, "DateProximity", confidence))
                    self.open_invoices[best_idx]["remaining"] -= take
                    payment_left -= take

        # --- Phase 5: FIFO Fallback ---
        # Enhanced FIFO: More aggressive matching for partial and split payments
        if payment_left > self.tol:
            for idx, inv in enumerate(self.open_invoices):
                if inv["remaining"] <= self.tol:
                    continue

                # Allow partial payment allocation regardless of amount
                take = min(inv["remaining"], payment_left)

                # Calculate dynamic confidence for FIFO matches
                confidence = 45  # Base confidence for FIFO (increased from 40)

                # Factor 1: Amount coverage ratio (does payment cover invoice well?)
                if inv["remaining"] > 0:
                    coverage_ratio = take / inv["remaining"]
                    if 0.90 <= coverage_ratio <= 1.10:
                        confidence += 15  # Payment covers 90-110% of invoice (increased)
                    elif 0.80 <= coverage_ratio <= 1.20:
                        confidence += 10  # Payment covers 80-120% of invoice (increased)
                    elif coverage_ratio >= 0.40:  # Accept partial payments down to 40%
                        confidence += 5   # At least 40% coverage

                # Factor 2: Date proximity (more flexible for real-world delays)
                if payment_date and payment_date != pd.NaT and inv["fecha"] and inv["fecha"] != pd.NaT:
                    days_diff = (payment_date - inv["fecha"]).days
                    if days_diff >= -30:  # Payment from 30 days before invoice
                        if days_diff <= 45:
                            confidence += 20  # Within 45 days (increased window)
                        elif days_diff <= 75:
                            confidence += 15  # Within 75 days (increased)
                        elif days_diff <= 120:
                            confidence += 10  # Within 120 days (increased)
                        elif days_diff <= 180:
                            confidence += 5   # Within 180 days

                # Factor 3: Position in queue (is this the first/oldest invoice?)
                if idx == 0:
                    confidence += 5  # First invoice in FIFO queue

                # Factor 4: Boost for clean allocations
                if abs(take - payment_left) < self.tol or abs(take - inv["remaining"]) < self.tol:
                    confidence += 5  # Fully allocates payment or invoice

                # Cap confidence at reasonable max for FIFO
                confidence = min(confidence, 75)  # Increased cap

                matches.append((idx, take, "FIFO", confidence))
                inv["remaining"] -= take
                payment_left -= take
                if payment_left <= self.tol:
                    break
        
        # --- Record Results ---
        # We need to record matches. Note that one payment might match multiple invoices (mixed methods)
        for match_tuple in matches:
            if len(match_tuple) == 4:  # New format with confidence
                idx, take, method, confidence = match_tuple
            else:  # Legacy format without confidence (shouldn't happen but for safety)
                idx, take, method = match_tuple
                confidence = 50  # Default confidence

            inv = self.open_invoices[idx]
            self.out_rows.append({
                "SetID": self.set_id,
                "Tercero": tercero,
                "Fecha_doc": inv["fecha"],
                "Fecha_pago": payment_row["fecha"],
                "DocKey": inv["doc_key"],
                "PagoKey": payment_row["doc_key"],
                "Asignado": take,
                "ResidualFacturaTras": inv["remaining"],
                "Hoja_doc": inv["original_row"]["hoja"],
                "Hoja_pago": payment_row["hoja"],
                "MatchMethod": method,
                "Confidence": round(confidence, 1),
                # Invoice original fields
                "Cuenta_doc": inv["original_row"]["cuenta"],
                "Documento_doc": inv["original_row"]["doc"],
                "Concepto_doc": inv["original_row"]["concepto"],
                # Payment original fields
                "Cuenta_pago": payment_row["cuenta"],
                "Documento_pago": payment_row["doc"],
                "Concepto_pago": payment_row["concepto"]
            })

        # Cleanup fully paid invoices
        self.open_invoices = [inv for inv in self.open_invoices if inv["remaining"] > self.tol]

        # Handle Unallocated Payment
        if payment_left > self.tol:
            # Generate suggestion for unmatched payment
            unmatched_row = {
                "SetID": self.set_id,
                "Tercero": tercero,
                "Fecha_doc": pd.NaT,
                "Fecha_pago": payment_row["fecha"],
                "DocKey": None,
                "PagoKey": payment_row["doc_key"],
                "Asignado": -payment_left,
                "ResidualFacturaTras": np.nan,
                "Hoja_doc": None,
                "Hoja_pago": payment_row["hoja"],
                "MatchMethod": "Unallocated",
                "Confidence": 0,  # 0% confidence for unallocated
                # Invoice fields - empty for unallocated payments
                "Cuenta_doc": None,
                "Documento_doc": None,
                "Concepto_doc": None,
                # Payment original fields
                "Cuenta_pago": payment_row["cuenta"],
                "Documento_pago": payment_row["doc"],
                "Concepto_pago": payment_row["concepto"]
            }

            # Generate suggestion for why it wasn't matched
            suggestion = generate_unmatched_suggestions(
                pd.Series(unmatched_row),
                self.open_invoices,
                recent_history=None  # Could be enhanced with payment history
            )

            # Add suggestion to the row
            unmatched_row["Suggestion"] = suggestion.get("message", "")
            unmatched_row["SuggestedAction"] = suggestion.get("action", "")
            unmatched_row["SuggestionConfidence"] = suggestion.get("confidence", 0)

            self.out_rows.append(unmatched_row)
            
        # Check if set is closed (no open invoices and no running payment)
        # In this row-by-row logic, we check if we are "clean".
        # Actually, SetID logic in original code was based on running sum being 0.
        # Here, we increment SetID if we have no open invoices.
        # But wait, if we have unallocated payment, we are not "clean".
        # Let's keep it simple: if no open invoices, we bump SetID. 
        # (This might split related groups if payment comes before invoice, but standard accounting usually has inv first)
        if not self.open_invoices:
            self.set_id += 1

    def flush_remaining(self, tercero):
        # Output remaining open invoices as unallocated
        for inv in self.open_invoices:
            self.out_rows.append({
                "SetID": self.set_id,
                "Tercero": tercero,
                "Fecha_doc": inv["fecha"],
                "Fecha_pago": pd.NaT,
                "DocKey": inv["doc_key"],
                "PagoKey": None,
                "Asignado": 0.0,
                "ResidualFacturaTras": inv["remaining"],
                "Hoja_doc": inv["original_row"]["hoja"],
                "Hoja_pago": None,
                "MatchMethod": "Open",
                "Confidence": 0,  # 0% confidence for open invoices
                # Invoice original fields
                "Cuenta_doc": inv["original_row"]["cuenta"],
                "Documento_doc": inv["original_row"]["doc"],
                "Concepto_doc": inv["original_row"]["concepto"],
                # Payment fields - empty for open invoices
                "Cuenta_pago": None,
                "Documento_pago": None,
                "Concepto_pago": None
            })

def reconcile_fifo(df: pd.DataFrame, tol: float = 0.01) -> pd.DataFrame:
    all_rows = []

    # Check if pre_reconciled column exists
    has_pre_reconciled = "pre_reconciled" in df.columns

    # Work per tercero
    # Sort by date to ensure chronological processing
    for tercero, g in df.sort_values(["tercero", "fecha", "idx"]).groupby(["tercero"], dropna=False):
        reconciler = Reconciler(tol=tol)
        pre_reconciled_rows = []  # Store pre-reconciled movements separately

        # Collect all movements for this tercero
        invoices = []
        payments = []

        for _, row in g.iterrows():
            # Check if this movement is pre-reconciled
            is_pre_reconciled = has_pre_reconciled and row.get("pre_reconciled", False)

            amount = float(row["neto_norm"] or 0.0)
            if is_pre_reconciled:
                # Don't process pre-reconciled items - just record them
                pre_reconciled_rows.append({
                    "row": row,
                    "amount": amount,
                    "is_invoice": amount > 0
                })
            elif amount > 0:
                invoices.append(row)
            elif amount < 0:
                payments.append(row)

        # Process in chronological order but with awareness of future movements
        # This helps with split payments and advance payments
        all_movements = sorted(invoices + payments, key=lambda x: (x["fecha"], x["idx"]))

        for row in all_movements:
            amount = float(row["neto_norm"] or 0.0)
            if amount > 0:
                reconciler.add_invoice(row)
            elif amount < 0:
                reconciler.process_payment(row, tercero)

        reconciler.flush_remaining(tercero)

        # Post-processing: Try to match unallocated payments with open invoices
        # This handles cases where payments come before invoices
        rows_df = pd.DataFrame(reconciler.out_rows)
        if not rows_df.empty:
            unallocated = rows_df[rows_df["MatchMethod"] == "Unallocated"]

            if not unallocated.empty:
                for _, payment in unallocated.iterrows():
                    payment_amount = abs(payment["Asignado"])

                    # Re-query open invoices each iteration to avoid stale data
                    open_invs = rows_df[rows_df["MatchMethod"] == "Open"]
                    if open_invs.empty:
                        break

                    # Find best matching open invoice
                    for _, invoice in open_invs.iterrows():
                        invoice_amount = invoice["ResidualFacturaTras"]
                        if pd.isna(invoice_amount) or invoice_amount <= tol:
                            continue

                        # Check if payment matches invoice (exact match within tolerance)
                        if abs(payment_amount - invoice_amount) < tol:
                            # Update the rows to show they're matched
                            pay_idx = rows_df.index[rows_df["PagoKey"] == payment["PagoKey"]].tolist()
                            inv_idx = rows_df.index[rows_df["DocKey"] == invoice["DocKey"]].tolist()

                            if pay_idx and inv_idx:
                                rows_df.loc[pay_idx[0], "MatchMethod"] = "PostProcessed"
                                rows_df.loc[pay_idx[0], "Confidence"] = 60
                                rows_df.loc[pay_idx[0], "Asignado"] = -payment_amount
                                rows_df.loc[inv_idx[0], "MatchMethod"] = "PostProcessed"
                                rows_df.loc[inv_idx[0], "Confidence"] = 60
                                rows_df.loc[inv_idx[0], "ResidualFacturaTras"] = 0.0
                                break

            all_rows.extend(rows_df.to_dict('records'))
        else:
            all_rows.extend(reconciler.out_rows)

        # Add pre-reconciled rows (they were already matched in previous periods)
        # These don't participate in new reconciliation but are recorded for completeness
        for pre_rec in pre_reconciled_rows:
            row = pre_rec["row"]
            amount = pre_rec["amount"]
            is_invoice = pre_rec["is_invoice"]

            if is_invoice:
                # Pre-reconciled invoice
                all_rows.append({
                    "SetID": reconciler.set_id,
                    "Tercero": tercero,
                    "Fecha_doc": row["fecha"],
                    "Fecha_pago": pd.NaT,
                    "DocKey": row["doc_key"],
                    "PagoKey": None,
                    "Asignado": amount,  # Fully assigned (matched in previous period)
                    "ResidualFacturaTras": 0.0,  # No residual
                    "Hoja_doc": row.get("hoja", ""),
                    "Hoja_pago": None,
                    "MatchMethod": "PreReconciled",  # Special status for pre-reconciled
                    "Confidence": 100,
                    "Cuenta_doc": row.get("cuenta", ""),
                    "Documento_doc": row.get("doc", ""),
                    "Concepto_doc": row.get("concepto", ""),
                    "Cuenta_pago": None,
                    "Documento_pago": None,
                    "Concepto_pago": None
                })
            else:
                # Pre-reconciled payment
                all_rows.append({
                    "SetID": reconciler.set_id,
                    "Tercero": tercero,
                    "Fecha_doc": pd.NaT,
                    "Fecha_pago": row["fecha"],
                    "DocKey": None,
                    "PagoKey": row["doc_key"],
                    "Asignado": amount,  # Negative (payment already matched)
                    "ResidualFacturaTras": None,
                    "Hoja_doc": None,
                    "Hoja_pago": row.get("hoja", ""),
                    "MatchMethod": "PreReconciled",
                    "Confidence": 100,
                    "Cuenta_doc": None,
                    "Documento_doc": None,
                    "Concepto_doc": None,
                    "Cuenta_pago": row.get("cuenta", ""),
                    "Documento_pago": row.get("doc", ""),
                    "Concepto_pago": row.get("concepto", "")
                })

    return pd.DataFrame(all_rows)

def build_pendientes(det: pd.DataFrame, tol: float) -> pd.DataFrame:
    if det.empty:
        return pd.DataFrame(columns=["Tercero", "DocKey", "ImportePendiente", "Fecha", "Dias"])
    
    # Get last status of each doc
    # Filter only invoice allocations or open invoices
    inv_allocs = det[det["DocKey"].notna()].copy()
    if inv_allocs.empty:
        return pd.DataFrame(columns=["Tercero", "DocKey", "ImportePendiente", "Fecha", "Dias"])
        
    inv_allocs.sort_values(["SetID", "Fecha_pago"], inplace=True, na_position='last')
    last_status = inv_allocs.drop_duplicates(subset=["DocKey"], keep="last")
    
    pend = last_status[last_status["ResidualFacturaTras"] > tol].copy()
    
    if pend.empty:
        return pd.DataFrame(columns=["Tercero", "DocKey", "ImportePendiente", "Fecha", "Dias"])

    today = pd.Timestamp.today().normalize()
    pend["Dias"] = (today - pend["Fecha_doc"]).dt.days.clip(lower=0)
    
    # Select and rename columns as requested
    pend = pend.rename(columns={
        "ResidualFacturaTras": "ImportePendiente",
        "Fecha_doc": "Fecha"
    })
    
    return pend[["Tercero", "DocKey", "ImportePendiente", "Fecha", "Dias"]]

def generate_unmatched_suggestions(payment_row: pd.Series, open_invoices: List[Dict], recent_history: List[Dict] = None) -> Dict[str, Any]:
    """
    Generate intelligent suggestions for why a payment wasn't matched and what to do about it.

    Args:
        payment_row: The unmatched payment row
        open_invoices: List of currently open invoices for this tercero
        recent_history: Recent payment patterns for this tercero (optional)

    Returns:
        Dictionary with suggestion type and details
    """
    suggestions = []
    payment_amount = abs(float(payment_row.get("Asignado", 0)))
    payment_date = payment_row.get("Fecha_pago")
    payment_concept = str(payment_row.get("Concepto_pago", "")).lower()
    tercero = payment_row.get("Tercero", "")

    # Check if payment amount is very small (likely bank fees or rounding)
    if payment_amount < 50:
        suggestions.append({
            "type": "small_amount",
            "confidence": 90,
            "message": f"Import petit ({payment_amount:.2f}€) - Possible comissió bancària o arrodoniment",
            "action": "Classificar com a despesa bancària"
        })

    # Check for possible advance payment based on concept
    advance_keywords = ["anticipo", "avance", "adelanto", "a cuenta", "provisió", "bestreta"]
    if any(keyword in payment_concept for keyword in advance_keywords):
        suggestions.append({
            "type": "advance_payment",
            "confidence": 85,
            "message": "El concepte suggereix un pagament anticipat",
            "action": "Marcar com a pagament a compte"
        })

    # Check if payment might be for future invoices
    if open_invoices:
        # Sort invoices by date
        sorted_invoices = sorted(open_invoices, key=lambda x: x.get("fecha", pd.NaT))

        # Check if payment amount is close to sum of upcoming invoices
        upcoming_sum = sum(inv["remaining"] for inv in sorted_invoices[:3])
        if abs(upcoming_sum - payment_amount) < payment_amount * 0.05:  # Within 5%
            suggestions.append({
                "type": "future_invoices",
                "confidence": 75,
                "message": f"Import similar a factures pendents futures ({upcoming_sum:.2f}€)",
                "action": "Revisar factures del proper trimestre"
            })

    # Check for possible digit transposition errors
    if open_invoices:
        for inv in open_invoices:
            inv_amount = inv.get("remaining", 0)
            # Check if digits might be transposed (e.g., 123.45 vs 132.45)
            amount_str = f"{payment_amount:.2f}".replace(".", "")
            inv_str = f"{inv_amount:.2f}".replace(".", "")

            if len(amount_str) == len(inv_str):
                differences = sum(1 for a, b in zip(amount_str, inv_str) if a != b)
                if differences == 2:  # Exactly two digits different (possible transposition)
                    suggestions.append({
                        "type": "digit_error",
                        "confidence": 60,
                        "message": f"Possible error de digitació - Similar a factura de {inv_amount:.2f}€",
                        "action": "Verificar import amb el banc",
                        "invoice_ref": inv.get("doc_key", "")
                    })
                    break

    # Check payment patterns if history is provided
    if recent_history and len(recent_history) >= 3:
        # Calculate average payment amount for this tercero
        avg_payment = sum(abs(p.get("amount", 0)) for p in recent_history) / len(recent_history)

        # Check if this payment is unusual
        if payment_amount > avg_payment * 2:
            suggestions.append({
                "type": "unusual_amount",
                "confidence": 50,
                "message": f"Import inusualment alt (mitjana: {avg_payment:.2f}€)",
                "action": "Verificar si inclou múltiples períodes"
            })
        elif payment_amount < avg_payment * 0.5:
            suggestions.append({
                "type": "partial_payment",
                "confidence": 65,
                "message": f"Possible pagament parcial (mitjana: {avg_payment:.2f}€)",
                "action": "Esperar resta del pagament"
            })

    # Check for credit note indicators
    credit_keywords = ["abono", "devolución", "credit", "nota", "nc", "reembolso", "retorn"]
    if any(keyword in payment_concept for keyword in credit_keywords):
        suggestions.append({
            "type": "credit_note",
            "confidence": 80,
            "message": "El concepte suggereix una nota de crèdit",
            "action": "Buscar nota de crèdit corresponent"
        })

    # Sort suggestions by confidence
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)

    # Return the best suggestion or a default one
    if suggestions:
        return suggestions[0]
    else:
        return {
            "type": "unknown",
            "confidence": 0,
            "message": "No s'ha pogut determinar el motiu",
            "action": "Revisar manualment amb documentació bancària"
        }

def translate_match_method(method: str) -> str:
    """Translate match method to Spanish"""
    translations = {
        "Reference": "Referència",
        "Exact": "Import exacte",
        "CombinedAmount": "Import combinat",
        "DateProximity": "Proximitat dates",
        "FIFO": "FIFO",
        "Open": "Pendent",
        "Unallocated": "Sense factura",
        "PreReconciled": "Ja conciliat",
        "PostProcessed": "Post-processat"
    }
    return translations.get(method, method)

def get_row_status(row: pd.Series, tol: float) -> str:
    """Determine the status of a reconciliation row for coloring"""
    method = row.get("MatchMethod", "")
    asignado = row.get("Asignado", 0)
    residual = row.get("ResidualFacturaTras", 0)

    # Blue: Pre-reconciled (already matched in previous period)
    if method == "PreReconciled":
        return "blue"

    # Red: Pending or unallocated payments
    if method == "Open" or method == "Unallocated":
        return "red"

    # Orange: Partial payment (has allocation but residual remains)
    if asignado > tol and residual > tol:
        return "orange"

    # Green: Fully reconciled
    if asignado > tol and (pd.isna(residual) or residual <= tol):
        return "green"

    return "white"

def get_punt_symbol(row: pd.Series, tol: float) -> str:
    """Get the Punt. symbol based on reconciliation status"""
    status = get_row_status(row, tol)
    if status == "blue":  # Pre-reconciled (from previous period)
        return "Sí"  # Keep original marking
    elif status == "green":
        return "✓"
    elif status == "orange":
        return "⚠"
    elif status == "red":
        return "✗"
    return ""

def build_cuentas_corrientes_sheet(det_df: pd.DataFrame, tol: float, tipo: str) -> pd.DataFrame:
    """
    Transform reconciliation detail DataFrame into original 'Cuentas corrientes' structure
    with additional reconciliation columns.

    Args:
        det_df: Reconciliation detail DataFrame (Clientes_Detalle or Proveedores_Detalle)
        tol: Tolerance for comparisons
        tipo: "AR" or "AP" to determine account type

    Returns:
        DataFrame with original structure + reconciliation info
    """
    if det_df.empty:
        return pd.DataFrame()

    # Create working copy
    df = det_df.copy()

    # Translate match methods
    df["Metodo"] = df["MatchMethod"].apply(translate_match_method)

    # Add Punt. column
    df["Punt."] = df.apply(lambda row: get_punt_symbol(row, tol), axis=1)

    # Calculate Debe and Haber from original neto values
    # For AR: Invoice (Haber), Payment (Debe)
    # For AP: Invoice (Debe), Payment (Haber)
    df["Debe"] = 0.0
    df["Haber"] = 0.0

    for idx, row in df.iterrows():
        asignado = row.get("Asignado", 0)

        if asignado > 0:  # Invoice allocation
            if tipo == "AR":
                df.at[idx, "Haber"] = asignado
            else:  # AP
                df.at[idx, "Debe"] = asignado
        elif asignado < 0:  # Unallocated payment
            if tipo == "AR":
                df.at[idx, "Debe"] = -asignado
            else:  # AP
                df.at[idx, "Haber"] = -asignado
        else:  # Open invoice
            residual = row.get("ResidualFacturaTras", 0)
            if residual > tol:
                if tipo == "AR":
                    df.at[idx, "Haber"] = residual
                else:  # AP
                    df.at[idx, "Debe"] = residual

    # Calculate running Saldo (cumulative balance)
    df = df.sort_values(["Cuenta_doc", "Fecha_pago"]).copy()

    # Group by account and calculate running balance
    df["Saldo"] = 0.0
    for cuenta, group in df.groupby("Cuenta_doc", dropna=False):
        group_sorted = group.sort_values(["Fecha_pago"])
        if tipo == "AR":
            # AR: Debe increases, Haber decreases
            running = (group_sorted["Debe"] - group_sorted["Haber"]).cumsum()
        else:  # AP
            # AP: Haber increases, Debe decreases
            running = (group_sorted["Haber"] - group_sorted["Debe"]).cumsum()
        df.loc[group_sorted.index, "Saldo"] = running

    # Prepare final columns with Spanish names
    output_rows = []

    # Group by account
    for cuenta, group in df.groupby("Cuenta_doc", dropna=False):
        # Get tercero (description) from first row
        tercero = group["Tercero"].iloc[0] if not group.empty else ""
        # Ensure tercero is a string, not a tuple or other type
        if isinstance(tercero, (tuple, list)):
            tercero = str(tercero[0]) if len(tercero) > 0 else ""
        else:
            tercero = str(tercero) if pd.notna(tercero) else ""

        # Add account header row
        header_row = {
            "Cuenta": cuenta,
            "Descripción": tercero,
            "Punt.": "",
            "Fecha": None,
            "Concepto": "",
            "Documento": "",
            "Debe": None,
            "Haber": None,
            "Saldo": None,
            "SetID": "",
            "Método": "",
            "Conciliat": None,
            "Pendent": None,
            "Confiança %": None,
            "_row_type": "header",
            "_status": "header"
        }
        output_rows.append(header_row)

        # Add detail rows
        for idx, row in group.iterrows():
            # Determine which date to show (payment date preferred, fallback to doc date)
            fecha = row["Fecha_pago"] if pd.notna(row["Fecha_pago"]) else row["Fecha_doc"]

            # Get concepto from original data
            concepto = row.get("Concepto_pago", "") if pd.notna(row.get("Concepto_pago")) else row.get("Concepto_doc", "")

            # Get documento
            documento = row.get("Documento_pago", "") if pd.notna(row.get("Documento_pago")) else row.get("Documento_doc", "")

            detail_row = {
                "Cuenta": "",  # Empty for detail rows
                "Descripción": "",  # Empty for detail rows
                "Punt.": row["Punt."],
                "Fecha": fecha,
                "Concepto": concepto,
                "Documento": documento,
                "Debe": row["Debe"] if row["Debe"] != 0 else None,
                "Haber": row["Haber"] if row["Haber"] != 0 else None,
                "Saldo": row["Saldo"],
                "SetID": int(row["SetID"]) if pd.notna(row["SetID"]) else "",
                "Método": row["Metodo"],
                "Conciliat": row["Asignado"] if row["Asignado"] != 0 else None,
                "Pendent": row["ResidualFacturaTras"] if pd.notna(row["ResidualFacturaTras"]) and row["ResidualFacturaTras"] > tol else None,
                "Confiança %": f"{row['Confidence']:.0f}%" if pd.notna(row.get("Confidence")) and row.get("Confidence", 0) > 0 else "",
                "_row_type": "detail",
                "_status": get_row_status(row, tol)
            }
            output_rows.append(detail_row)

        # Add total row for this account
        total_debe = group["Debe"].sum()
        total_haber = group["Haber"].sum()
        final_saldo = group["Saldo"].iloc[-1] if not group.empty else 0

        total_row = {
            "Cuenta": "",
            "Descripción": "",
            "Punt.": "",
            "Fecha": None,
            "Concepto": "Total cuenta",
            "Documento": "",
            "Debe": total_debe if total_debe != 0 else None,
            "Haber": total_haber if total_haber != 0 else None,
            "Saldo": final_saldo,
            "SetID": "",
            "Método": "",
            "Conciliat": None,
            "Pendent": None,
            "Confiança %": "",
            "_row_type": "total",
            "_status": "total"
        }
        output_rows.append(total_row)

        # Add blank row
        blank_row = {col: "" if col not in ["Debe", "Haber", "Saldo", "Conciliat", "Pendent"] else None
                     for col in header_row.keys()}
        blank_row["_row_type"] = "blank"
        blank_row["_status"] = "blank"
        output_rows.append(blank_row)

    return pd.DataFrame(output_rows)


def build_human_format_excel(
    original_df: pd.DataFrame,
    pending_ar: pd.DataFrame,
    pending_ap: pd.DataFrame,
    company_name: Optional[str],
    period: Optional[str],
    header_row_idx: int,
    schema: Dict[str, Optional[str]],
    ar_prefix: str = "43",
    ap_prefix: str = "40,41",
    tol: float = 0.01
) -> List[Dict]:
    """
    Generate Excel output in EXACT human format - indistinguishable from manual reconciliation.

    Shows ONLY pending items (identified by reconciliation) with the same structure as the original input:
    - Single sheet "Cuentas corrientes"
    - Same columns: Cuenta, Descripción, Punt., Fecha, Concepto, Documento, Debe, Haber, Saldo, Contrapartida
    - Account headers, "Saldos anteriores", "Total cuenta" rows
    - Grouped by account
    """
    from datetime import datetime

    output_rows = []

    # Collect all pending document numbers (only these should be in output)
    pending_docs_ar = set()
    pending_docs_ap = set()

    if not pending_ar.empty:
        for _, r in pending_ar.iterrows():
            doc_key = str(r.get('DocKey', ''))
            # Extract document number from DocKey (format: "tercero | doc | cuenta | amount")
            parts = doc_key.split('|')
            if len(parts) >= 2:
                doc_num = parts[1].strip()
                # Remove .0 suffix if present
                if doc_num.endswith('.0'):
                    doc_num = doc_num[:-2]
                pending_docs_ar.add(doc_num)

    if not pending_ap.empty:
        for _, r in pending_ap.iterrows():
            doc_key = str(r.get('DocKey', ''))
            parts = doc_key.split('|')
            if len(parts) >= 2:
                doc_num = parts[1].strip()
                if doc_num.endswith('.0'):
                    doc_num = doc_num[:-2]
                pending_docs_ap.add(doc_num)

    # Get column names from schema
    cuenta_col = schema.get('cuenta', 'Cuenta')
    tercero_col = schema.get('tercero', 'Descripción')
    punt_col = schema.get('punt', 'Punt.')
    fecha_col = schema.get('fecha', 'Fecha')
    concepto_col = schema.get('concepto', 'Concepto')
    doc_col = schema.get('documento', 'Documento')
    debe_col = schema.get('debe', 'Debe')
    haber_col = schema.get('haber', 'Haber')
    saldo_col = schema.get('saldo', 'Saldo')

    # Group original data by account
    current_account = None
    current_tercero = None
    account_movements = {}  # {(account, tercero): [movements]}

    for idx, row in original_df.iterrows():
        cuenta_val = row.get(cuenta_col)
        tercero_val = row.get(tercero_col)
        concepto_val = str(row.get(concepto_col, '')) if pd.notna(row.get(concepto_col)) else ''

        # Skip total rows
        if concepto_val == 'Total cuenta':
            continue

        # Handle "Saldos anteriores" — include if they have amounts
        if concepto_val == 'Saldos anteriores':
            debe = row.get(debe_col, 0) if pd.notna(row.get(debe_col)) else 0
            haber = row.get(haber_col, 0) if pd.notna(row.get(haber_col)) else 0
            if (debe or haber) and current_account:
                account_movements[(current_account, current_tercero)].append({
                    'fecha': row.get(fecha_col) if pd.notna(row.get(fecha_col)) else pd.Timestamp("1900-01-01"),
                    'concepto': 'Saldos anteriores',
                    'documento': row.get(doc_col),
                    'debe': float(debe),
                    'haber': float(haber),
                    'is_saldo_anterior': True,
                })
            continue

        # Check if this is an account header row (has account number)
        if pd.notna(cuenta_val) and str(cuenta_val).strip():
            current_account = str(cuenta_val).strip()
            current_tercero = str(tercero_val).strip() if pd.notna(tercero_val) else ''
            if (current_account, current_tercero) not in account_movements:
                account_movements[(current_account, current_tercero)] = []
        elif current_account and pd.notna(row.get(fecha_col)):
            # This is a movement row - check if its document is in pending list
            doc_val = row.get(doc_col)
            doc_num = str(doc_val).strip() if pd.notna(doc_val) else ''
            # Remove .0 suffix if present
            if doc_num.endswith('.0'):
                doc_num = doc_num[:-2]

            # Check if this specific document is pending
            is_pending = False
            ap_prefixes_list = [p.strip() for p in ap_prefix.split(",")]
            if current_account.startswith(ar_prefix):  # AR - Clients
                is_pending = doc_num in pending_docs_ar
            elif any(current_account.startswith(p) for p in ap_prefixes_list):  # AP - Suppliers
                is_pending = doc_num in pending_docs_ap

            # Also detect impagados (returned direct debits) — these are always pending
            concepto_upper = concepto_val.upper()
            is_impagado = 'IMPAGAD' in concepto_upper

            if is_pending or is_impagado:
                account_movements[(current_account, current_tercero)].append({
                    'fecha': row.get(fecha_col),
                    'concepto': row.get(concepto_col),
                    'documento': row.get(doc_col),
                    'debe': row.get(debe_col, 0) if pd.notna(row.get(debe_col)) else 0,
                    'haber': row.get(haber_col, 0) if pd.notna(row.get(haber_col)) else 0,
                })

    # Build output rows for accounts with pending movements
    first_account = True
    for (account, tercero), movements in sorted(account_movements.items()):
        if not movements:
            continue

        # Check if this account is fully reconciled (saldo = 0 within tolerance)
        total_balance = sum(float(m.get('debe', 0)) - float(m.get('haber', 0)) for m in movements)
        if abs(total_balance) <= tol:
            continue  # Fully reconciled account, skip

        # Add blank row between accounts (and before first)
        if not first_account:
            output_rows.append({
                'Cuenta': None, 'Descripción': None, 'Punt.': None, 'Fecha': None,
                'Concepto': None, 'Documento': None, 'Debe': None, 'Haber': None,
                'Saldo': None, 'Contrapartida': None, '_row_type': 'blank'
            })
        first_account = False

        # Clean account number (remove .0 suffix)
        clean_account = str(account)
        if clean_account.endswith('.0'):
            clean_account = clean_account[:-2]

        # Account header row
        output_rows.append({
            'Cuenta': clean_account,
            'Descripción': tercero,
            'Punt.': None,
            'Fecha': None,
            'Concepto': None,
            'Documento': None,
            'Debe': None,
            'Haber': None,
            'Saldo': None,
            'Contrapartida': None,
            '_row_type': 'account_header'
        })

        # Separate saldo anterior movements from regular movements
        saldo_anterior_movs = [m for m in movements if m.get('is_saldo_anterior')]
        regular_movs = [m for m in movements if not m.get('is_saldo_anterior')]

        # Calculate saldos anteriores total from actual data
        saldo_ant_debe = sum(float(m['debe']) for m in saldo_anterior_movs)
        saldo_ant_haber = sum(float(m['haber']) for m in saldo_anterior_movs)
        saldo_ant_saldo = saldo_ant_debe - saldo_ant_haber

        # Saldos anteriores row
        output_rows.append({
            'Cuenta': None,
            'Descripción': None,
            'Punt.': None,
            'Fecha': None,
            'Concepto': 'Saldos anteriores',
            'Documento': None,
            'Debe': saldo_ant_debe if saldo_ant_debe else 0,
            'Haber': saldo_ant_haber if saldo_ant_haber else 0,
            'Saldo': saldo_ant_saldo,
            'Contrapartida': None,
            '_row_type': 'saldos_anteriores'
        })

        # Movement rows
        running_saldo = saldo_ant_saldo
        total_debe = saldo_ant_debe
        total_haber = saldo_ant_haber

        for mov in sorted(regular_movs, key=lambda x: x['fecha'] if pd.notna(x['fecha']) else pd.Timestamp.min):
            debe = float(mov['debe']) if mov['debe'] else 0
            haber = float(mov['haber']) if mov['haber'] else 0
            running_saldo += debe - haber
            total_debe += debe
            total_haber += haber

            output_rows.append({
                'Cuenta': None,
                'Descripción': None,
                'Punt.': None,  # Empty - not reconciled
                'Fecha': mov['fecha'],
                'Concepto': mov['concepto'],
                'Documento': mov['documento'],
                'Debe': debe if debe else 0,
                'Haber': haber if haber else 0,
                'Saldo': running_saldo,
                'Contrapartida': None,
                '_row_type': 'movement'
            })

        # Total cuenta row
        output_rows.append({
            'Cuenta': None,
            'Descripción': None,
            'Punt.': None,
            'Fecha': None,
            'Concepto': 'Total cuenta',
            'Documento': None,
            'Debe': total_debe if total_debe else 0,
            'Haber': total_haber if total_haber else 0,
            'Saldo': running_saldo,
            'Contrapartida': None,
            '_row_type': 'total'
        })

        # Note: blank row between accounts is added at the start of the next iteration

    return output_rows


def write_human_format_excel(
    output_rows: List[Dict],
    company_name: Optional[str],
    period: Optional[str]
) -> io.BytesIO:
    """
    Write the human-format Excel with exact same structure as manual reconciliation.
    """
    from datetime import datetime

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Cuentas corrientes')

        # Formats
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
        account_format = workbook.add_format({'bold': True, 'bg_color': '#E2EFDA'})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#FCE4D6'})
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})

        # Title and metadata
        worksheet.write(0, 0, 'Cuentas corrientes.', title_format)
        worksheet.write(2, 0, f'Empresa: {company_name or ""}')
        worksheet.write(3, 0, f'Período: {period or ""}')
        worksheet.write(4, 0, f'Fecha: {datetime.now().strftime("%d/%m/%Y")}')

        # Headers
        headers = ['Cuenta', 'Descripción', 'Punt.', 'Fecha', 'Concepto', 'Documento',
                   'Debe', 'Haber', 'Saldo', 'Contrapartida']
        for col, header in enumerate(headers):
            worksheet.write(6, col, header, header_format)

        # Blank row after headers (row 7 is empty)
        # Data rows start at row 8
        row_num = 8
        for data_row in output_rows:
            row_type = data_row.get('_row_type', 'movement')

            if row_type == 'blank':
                row_num += 1
                continue

            # Determine format based on row type
            if row_type == 'account_header':
                fmt = account_format
            elif row_type == 'total':
                fmt = total_format
            else:
                fmt = None

            # Write cells
            worksheet.write(row_num, 0, data_row.get('Cuenta'), fmt)
            worksheet.write(row_num, 1, data_row.get('Descripción'), fmt)
            worksheet.write(row_num, 2, data_row.get('Punt.'), fmt)

            fecha = data_row.get('Fecha')
            if pd.notna(fecha) and fecha is not None:
                worksheet.write(row_num, 3, fecha, date_format)
            else:
                worksheet.write(row_num, 3, None, fmt)

            worksheet.write(row_num, 4, data_row.get('Concepto'), fmt)
            worksheet.write(row_num, 5, data_row.get('Documento'), fmt)

            # Numbers
            debe = data_row.get('Debe')
            haber = data_row.get('Haber')
            saldo = data_row.get('Saldo')

            if debe is not None and debe != 0:
                worksheet.write(row_num, 6, debe, number_format)
            else:
                worksheet.write(row_num, 6, 0 if row_type in ['saldos_anteriores', 'total', 'movement'] else None)

            if haber is not None and haber != 0:
                worksheet.write(row_num, 7, haber, number_format)
            else:
                worksheet.write(row_num, 7, 0 if row_type in ['saldos_anteriores', 'total', 'movement'] else None)

            if saldo is not None:
                worksheet.write(row_num, 8, saldo, number_format)

            worksheet.write(row_num, 9, data_row.get('Contrapartida'), fmt)

            row_num += 1

        # Set column widths
        worksheet.set_column(0, 0, 12)   # Cuenta
        worksheet.set_column(1, 1, 30)   # Descripción
        worksheet.set_column(2, 2, 6)    # Punt.
        worksheet.set_column(3, 3, 12)   # Fecha
        worksheet.set_column(4, 4, 35)   # Concepto
        worksheet.set_column(5, 5, 12)   # Documento
        worksheet.set_column(6, 8, 12)   # Debe, Haber, Saldo
        worksheet.set_column(9, 9, 15)   # Contrapartida

    output.seek(0)
    return output


def generate_reconciliation_data(file_content: bytes, tol: float, ar_prefix: str, ap_prefix: str, sheet_filter: Optional[str] = None) -> Tuple[Dict[str, pd.DataFrame], List[Dict], Optional[str], Optional[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_content))

    ar_rows = []
    ap_rows = []
    meta_rows = []
    company_name = None
    period = None

    # Skip sheets that are generated by this system
    system_generated_sheets = {'Meta', 'Resumen', 'Clientes_Detalle', 'Proveedores_Detalle',
                              'Pendientes_Clientes', 'Pendientes_Proveedores',
                              'AR_Detalle', 'AP_Detalle', 'Pendientes_AR', 'Pendientes_AP'}

    sheets_to_process = [sheet_filter] if sheet_filter else xls.sheet_names
    # Filter out system-generated sheets
    sheets_to_process = [s for s in sheets_to_process if s not in system_generated_sheets]

    if not sheets_to_process:
        # If all sheets are system-generated, this might be an already processed file
        raise ValueError("El archivo parece ser un resultado ya procesado. Por favor, sube el archivo original de contabilidad.")

    for idx, sheet_name in enumerate(sheets_to_process):
        if sheet_name not in xls.sheet_names:
            continue

        df_head = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=30)
        header_row = find_header_row(df_head)

        # Extract company name and period from first sheet only
        if idx == 0:
            if company_name is None:
                company_name = extract_company_name(df_head, header_row)
            if period is None:
                period = extract_period(df_head, header_row)
        
        df0 = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)
        
        df = normalize_cols(df0)
        sch = detect_schema(df)
        
        meta_info = {
            "Hoja": sheet_name,
            "Header_Row": header_row,
            "Filas_Raw": len(df),
            "Columnas_Detectadas": {k: v for k, v in sch.items() if v}
        }
        
        if sch["cuenta"]:
            df[sch["cuenta"]] = df[sch["cuenta"]].ffill()
        if sch["tercero"]:
            df[sch["tercero"]] = df[sch["tercero"]].ffill()
            
        for c in [sch["debe"], sch["haber"], sch["saldo"]]:
            if c:
                df[c] = pd.to_numeric(df[c], errors="coerce")
                
        net_col = None
        if sch["debe"] and sch["haber"]:
            net_col = "_neto_"
            df[net_col] = df[sch["debe"]].fillna(0) - df[sch["haber"]].fillna(0)
        else:
            importe_cols = find_cols(df, [r"importe|monto|amount"])
            if len(importe_cols)==1:
                net_col = importe_cols[0]
                df[net_col] = pd.to_numeric(df[net_col], errors="coerce")
            else:
                net_col = None
                
        meta_info["Neto_Column"] = net_col

        if sch["cuenta"] is None or net_col is None:
            meta_info["Error"] = "Falta columna Cuenta o Neto"
            meta_rows.append(meta_info)
            continue
            
        if sch["fecha"]:
            if not np.issubdtype(df[sch["fecha"]].dtype, np.datetime64):
                df[sch["fecha"]] = pd.to_datetime(df[sch["fecha"]], dayfirst=True, errors="coerce")
            # Preserve "Saldos anteriores" rows that have amounts even if they lack a date
            saldos_mask = df[sch["concepto"]].astype(str).str.contains("Saldos anteriores", na=False) if sch["concepto"] else pd.Series(False, index=df.index)
            has_amount = df[net_col].abs() > tol if net_col else pd.Series(False, index=df.index)
            has_date = df[sch["fecha"]].notna()
            df = df[has_date | (saldos_mask & has_amount)].copy()
            # Assign a very early date to "Saldos anteriores" rows so they sort first in FIFO
            if saldos_mask.any():
                saldos_no_date = saldos_mask & df[sch["fecha"]].isna()
                df.loc[saldos_no_date, sch["fecha"]] = pd.Timestamp("1900-01-01")
            
        meta_info["Filas_Procesables"] = len(df)

        ap_prefixes = [p.strip() for p in ap_prefix.split(",")]
        df["_collective"] = df[sch["cuenta"]].astype(str).str.strip().apply(
            lambda s: "AR" if s.startswith(ar_prefix) else ("AP" if any(s.startswith(p) for p in ap_prefixes) else "OTROS")
        )
        
        counts = df["_collective"].value_counts().to_dict()
        meta_info["Filas_Clientes"] = counts.get("AR", 0)
        meta_info["Filas_Proveedores"] = counts.get("AP", 0)

        # print(f"[DEBUG] Processing sheet '{sheet_name}' with {len(df)} rows")
        # print(f"[DEBUG] AR rows: {counts.get('AR', 0)}, AP rows: {counts.get('AP', 0)}, Others: {counts.get('OTROS', 0)}")

        meta_rows.append(meta_info)

        df["_tercero"] = df[sch["tercero"]] if sch["tercero"] else np.nan
        df["_doc"] = df[sch["documento"]] if sch["documento"] else np.nan
        df["_concepto"] = df[sch["concepto"]] if sch["concepto"] else np.nan
        df["_fecha"] = df[sch["fecha"]] if sch["fecha"] else pd.NaT
        # Read the pre-reconciled column (Punt.) if available
        df["_punt"] = df[sch["punt"]] if sch.get("punt") else np.nan

        for coll, sub in df[df["_collective"].isin(["AR","AP"])].copy().groupby("_collective"):
            sub = sub.reset_index(drop=True)
            net = sub[net_col].fillna(0).astype(float)
            if coll == "AR":
                net_norm = net # AR: Invoice > 0
            else:
                net_norm = -net # AP: Invoice > 0 (usually Credit in accounting, so we invert)

            # Check if movement is pre-reconciled (has "Sí" or similar in punt column)
            pre_reconciled = sub["_punt"].astype(str).str.strip().str.lower().isin(["sí", "si", "yes", "x", "✓", "true", "1"])

            work = pd.DataFrame({
                "hoja": sheet_name,
                "fecha": sub["_fecha"],
                "tercero": sub["_tercero"].astype(str).replace({"nan": None}),
                "doc": sub["_doc"].astype(str).replace({"nan": None}),
                "concepto": sub["_concepto"].astype(str).replace({"nan": None}),
                "cuenta": sub[sch["cuenta"]].astype(str),
                "neto": net,
                "neto_norm": net_norm,
                "pre_reconciled": pre_reconciled,
            })
            work["row_id"] = work.index.values
            work["doc_key"] = work.apply(
                lambda r: (r["tercero"] or "") + " | " + (r["doc"] or f"{str(r['fecha'])[:10]}") + " | " + (r["cuenta"] or "") + " | " + f"{r['neto_norm']:+.2f}",
                axis=1
            )
            if work["fecha"].isna().all():
                work["fecha"] = pd.Timestamp("1900-01-01")

            if coll == "AR":
                ar_rows.append(work)
            else:
                ap_rows.append(work)

    out_sheets = {}

    # AR Processing
    det_ar = pd.DataFrame()
    if ar_rows:
        ar_all = pd.concat(ar_rows, ignore_index=True)
        ar_all["idx"] = np.arange(len(ar_all))
        det_ar = reconcile_fifo(ar_all, tol=tol)
        out_sheets["Clientes_Detalle"] = det_ar
        out_sheets["Pendientes_Clientes"] = build_pendientes(det_ar, tol)
        # Generate Cuentas corrientes style sheet for AR
        out_sheets["Clientes_Cuentas_Corrientes"] = build_cuentas_corrientes_sheet(det_ar, tol, "AR")

    # AP Processing
    det_ap = pd.DataFrame()
    if ap_rows:
        ap_all = pd.concat(ap_rows, ignore_index=True)
        ap_all["idx"] = np.arange(len(ap_all))
        det_ap = reconcile_fifo(ap_all, tol=tol)
        out_sheets["Proveedores_Detalle"] = det_ap
        out_sheets["Pendientes_Proveedores"] = build_pendientes(det_ap, tol)
        # Generate Cuentas corrientes style sheet for AP
        out_sheets["Proveedores_Cuentas_Corrientes"] = build_cuentas_corrientes_sheet(det_ap, tol, "AP")

    # Summary
    def quick_summary(df: pd.DataFrame, name: str, pend_sheet: str) -> Dict:
        if df.empty:
            return {
                "Bloque": name,
                "Asignado": 0.0,
                "Pagos_sin_factura": 0.0,
                "Docs_pendientes": 0
            }
        
        conciliado = df["Asignado"].where(df["Asignado"]>0, 0).sum()
        sin_factura = df["Asignado"].where(df["Asignado"]<0, 0).sum()
        pend_df = out_sheets.get(pend_sheet, pd.DataFrame())
        num_pendientes = len(pend_df)
        
        return {
            "Bloque": name,
            "Asignado": round(conciliado, 2),
            "Pagos_sin_factura": round(sin_factura, 2),
            "Docs_pendientes": int(num_pendientes)
        }

    summary_list = [
        quick_summary(det_ar, "Clientes", "Pendientes_Clientes"),
        quick_summary(det_ap, "Proveedores", "Pendientes_Proveedores")
    ]
    
    out_sheets["Resumen"] = pd.DataFrame(summary_list)
    out_sheets["Meta"] = pd.DataFrame([
        {k: str(v) if isinstance(v, dict) else v for k, v in r.items()} 
        for r in meta_rows
    ])
    
    return out_sheets, summary_list, company_name, period

def write_excel_with_formatting(out_sheets: Dict[str, pd.DataFrame], company_name: Optional[str], period: Optional[str]) -> io.BytesIO:
    """
    Write Excel file with proper formatting and colors for Cuentas corrientes sheets
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Define color formats
        green_format = workbook.add_format({
            'bg_color': '#C6EFCE',
            'font_color': '#006100'
        })
        orange_format = workbook.add_format({
            'bg_color': '#FFEB9C',
            'font_color': '#9C5700'
        })
        red_format = workbook.add_format({
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006'
        })
        header_format = workbook.add_format({
            'bg_color': '#D9E1F2',
            'font_color': '#1F4E78',
            'bold': True
        })
        total_format = workbook.add_format({
            'bg_color': '#E7E6E6',
            'bold': True
        })
        metadata_format = workbook.add_format({
            'bold': True,
            'font_size': 11
        })

        for sheet_name, df in out_sheets.items():
            # Skip empty sheets
            if df.empty:
                continue

            sheet_name_safe = sheet_name[:31]

            # Check if this is a Cuentas corrientes sheet
            if "Cuentas_Corrientes" in sheet_name:
                # Write metadata header
                worksheet = workbook.add_worksheet(sheet_name_safe)
                writer.sheets[sheet_name_safe] = worksheet

                current_row = 0

                # Add title
                worksheet.write(current_row, 0, "Cuentas corrientes conciliado.", metadata_format)
                current_row += 2

                # Add company name if available
                if company_name:
                    worksheet.write(current_row, 0, f"Empresa: {company_name}", metadata_format)
                    current_row += 1

                # Add period if available
                if period:
                    worksheet.write(current_row, 0, f"Período: {period}", metadata_format)
                    current_row += 1

                # Add date
                from datetime import datetime
                fecha_str = datetime.now().strftime("%d/%m/%Y")
                worksheet.write(current_row, 0, f"Fecha: {fecha_str}", metadata_format)
                current_row += 2

                # Get columns (excluding internal columns)
                display_columns = [col for col in df.columns if not col.startswith('_')]

                # Write column headers
                for col_num, col_name in enumerate(display_columns):
                    worksheet.write(current_row, col_num, col_name, header_format)

                current_row += 1
                header_row_excel = current_row

                # Pre-create date format cache to avoid creating formats inside the loop
                date_format_cache = {}

                # Write data rows with formatting
                for idx, row in df.iterrows():
                    status = row.get('_status', 'white')
                    row_type = row.get('_row_type', 'detail')

                    # Select format based on status
                    if row_type == 'header':
                        row_format = header_format
                    elif row_type == 'total':
                        row_format = total_format
                    elif status == 'green':
                        row_format = green_format
                    elif status == 'orange':
                        row_format = orange_format
                    elif status == 'red':
                        row_format = red_format
                    else:
                        row_format = None

                    # Write each cell
                    for col_num, col_name in enumerate(display_columns):
                        value = row[col_name]

                        # Handle different data types
                        if pd.isna(value) or value == "":
                            if row_format:
                                worksheet.write_blank(current_row, col_num, None, row_format)
                            else:
                                worksheet.write_blank(current_row, col_num, None)
                        elif isinstance(value, (int, float, np.integer, np.floating)):
                            if row_format:
                                worksheet.write_number(current_row, col_num, float(value), row_format)
                            else:
                                worksheet.write_number(current_row, col_num, float(value))
                        elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
                            # Use cached date format for this row color to avoid creating formats in a loop
                            date_fmt_key = id(row_format) if row_format else None
                            if date_fmt_key not in date_format_cache:
                                fmt = workbook.add_format({'num_format': 'dd/mm/yyyy'})
                                if row_format and hasattr(row_format, 'bg_color') and row_format.bg_color:
                                    fmt.set_bg_color(row_format.bg_color)
                                date_format_cache[date_fmt_key] = fmt
                            worksheet.write_datetime(current_row, col_num, value, date_format_cache[date_fmt_key])
                        else:
                            if row_format:
                                worksheet.write(current_row, col_num, str(value), row_format)
                            else:
                                worksheet.write(current_row, col_num, str(value))

                    current_row += 1

                # Auto-adjust column widths
                for col_num, col_name in enumerate(display_columns):
                    max_width = len(str(col_name)) + 2
                    for row in df.itertuples():
                        cell_value = getattr(row, col_name, "")
                        if pd.notna(cell_value):
                            max_width = max(max_width, len(str(cell_value)) + 2)
                    worksheet.set_column(col_num, col_num, min(max_width, 50))

            else:
                # Regular sheet without special formatting
                df.to_excel(writer, sheet_name=sheet_name_safe, index=False)

    output.seek(0)
    return output

def process_excel(file_content: bytes, tol: float, ar_prefix: str, ap_prefix: str, justifications: Optional[Dict[str, str]] = None, output_format: str = "human") -> Tuple[Dict, io.BytesIO]:
    out_sheets, summary_list, company_name, period = generate_reconciliation_data(file_content, tol, ar_prefix, ap_prefix)

    # Add justifications to detail sheets if provided
    if justifications:
        for sheet_name in ["Clientes_Detalle", "Proveedores_Detalle"]:
            if sheet_name in out_sheets and not out_sheets[sheet_name].empty:
                df = out_sheets[sheet_name]
                # Add justification column
                df["Justificacion"] = df.apply(
                    lambda row: justifications.get(f"{row['SetID']}-{row['PagoKey']}", "")
                    if row["MatchMethod"] == "Unallocated" else "",
                    axis=1
                )

    # Write Excel based on output format
    if output_format == "human":
        # Human format: single sheet identical to manual reconciliation
        # Read original file to get structure
        xls = pd.ExcelFile(io.BytesIO(file_content))
        sheet_name = 'Cuentas corrientes' if 'Cuentas corrientes' in xls.sheet_names else xls.sheet_names[0]

        # Read without header first to find header row
        original_df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        header_row_idx = find_header_row(original_df_raw)

        # Read with header
        original_df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row_idx)
        schema = detect_schema(original_df)

        # Get pending items
        pending_ar = out_sheets.get('Pendientes_Clientes', pd.DataFrame())
        pending_ap = out_sheets.get('Pendientes_Proveedores', pd.DataFrame())

        # Build and write human format
        output_rows = build_human_format_excel(
            original_df=original_df,
            pending_ar=pending_ar,
            pending_ap=pending_ap,
            company_name=company_name,
            period=period,
            header_row_idx=header_row_idx,
            schema=schema,
            ar_prefix=ar_prefix,
            ap_prefix=ap_prefix,
            tol=tol,
        )
        output = write_human_format_excel(output_rows, company_name, period)
    else:
        # Detailed format: multiple sheets with full reconciliation details
        output = write_excel_with_formatting(out_sheets, company_name, period)
    
    # Final robust sanitization for JSON
    # Final robust sanitization for JSON
    def recursive_sanitize(obj):
        if isinstance(obj, dict):
            return {k: recursive_sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [recursive_sanitize(v) for v in obj]
        elif isinstance(obj, (float, np.floating)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, (int, np.integer)):
            return int(obj)
        elif pd.isna(obj): # Catch pandas NaT/NaN/None
            return None
        return obj

    # Convert DataFrames to dict records for JSON response
    details = {}
    for name, df in out_sheets.items():
        if name in ["Clientes_Detalle", "Proveedores_Detalle", "Pendientes_Clientes", "Pendientes_Proveedores"]:
            # Create a copy to avoid SettingWithCopy warnings
            df_clean = df.copy()
            
            # Replace Infinity with NaN first (numpy types)
            df_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
            
            # Convert dates to string ISO format BEFORE replacing NaNs with None
            # because datetime columns with None might be tricky
            for col in df_clean.columns:
                if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
                    df_clean[col] = df_clean[col].dt.strftime('%Y-%m-%d')
            
            # Now replace all NaN (including those from Inf) with None
            # We use where(pd.notnull(df), None) pattern which is robust
            df_clean = df_clean.where(pd.notnull(df_clean), None)
            
            details[name] = df_clean.to_dict(orient="records")

    # Construct raw response
    raw_response = {
        "summary": summary_list,
        "meta": [],
        "details": details,
        "company_name": company_name,
        "period": period
    }
    
    # Sanitize everything
    clean_response = recursive_sanitize(raw_response)

    return clean_response, output
