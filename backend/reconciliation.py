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
    
    schema = {
        "fecha": date_col, "cuenta": cuenta_col, "debe": debe_col, "haber": haber_col,
        "saldo": saldo_col, "tercero": tercero_col, "documento": doc_col, "concepto": concepto_col
    }
    
    # Fallback for headless sheets
    if not (schema["fecha"] and schema["cuenta"] and (schema["debe"] or schema["haber"])):
        # print(f"[DEBUG] Schema detection failed, using fallback. Detected schema: {schema}")
        if len(df.columns) >= 9:
            cols = list(df.columns)
            schema = {
                "cuenta": cols[0],
                "tercero": cols[1],
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

                if max_score > 0.7:  # Threshold for considering a reference match
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
        if payment_left > self.tol:
            for idx, inv in enumerate(self.open_invoices):
                if inv["remaining"] <= self.tol:
                    continue

                take = min(inv["remaining"], payment_left)

                # Calculate dynamic confidence for FIFO matches
                confidence = 40  # Base confidence for FIFO

                # Factor 1: Amount coverage ratio (does payment cover invoice well?)
                if inv["remaining"] > 0:
                    coverage_ratio = take / inv["remaining"]
                    if 0.90 <= coverage_ratio <= 1.10:
                        confidence += 10  # Payment covers 90-110% of invoice
                    elif 0.80 <= coverage_ratio <= 1.20:
                        confidence += 5   # Payment covers 80-120% of invoice

                # Factor 2: Date proximity (is payment close to invoice date?)
                if payment_date and payment_date != pd.NaT and inv["fecha"] and inv["fecha"] != pd.NaT:
                    days_diff = (payment_date - inv["fecha"]).days
                    if 0 <= days_diff <= 30:
                        confidence += 15  # Within 30 days
                    elif 0 <= days_diff <= 60:
                        confidence += 10  # Within 60 days
                    elif 0 <= days_diff <= 90:
                        confidence += 5   # Within 90 days

                # Factor 3: Position in queue (is this the first/oldest invoice?)
                if idx == 0:
                    confidence += 5  # First invoice in FIFO queue

                # Cap confidence at reasonable max for FIFO
                confidence = min(confidence, 70)

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
    
    # Work per tercero
    # Sort by date to ensure chronological processing
    for tercero, g in df.sort_values(["tercero", "fecha", "idx"]).groupby(["tercero"], dropna=False):
        reconciler = Reconciler(tol=tol)
        
        for _, row in g.iterrows():
            amount = float(row["neto_norm"] or 0.0)
            if amount > 0:
                reconciler.add_invoice(row)
            elif amount < 0:
                reconciler.process_payment(row, tercero)
        
        reconciler.flush_remaining(tercero)
        all_rows.extend(reconciler.out_rows)
            
    return pd.DataFrame(all_rows)

def build_pendientes(det: pd.DataFrame, tol: float) -> pd.DataFrame:
    if det.empty:
        return pd.DataFrame(columns=["Tercero", "DocKey", "ImportePendiente", "Fecha", "Dias"])
    
    # Get last status of each doc
    # Filter only invoice allocations or open invoices
    inv_allocs = det[det["DocKey"].notna()].copy()
    if inv_allocs.empty:
        return pd.DataFrame(columns=["Tercero", "DocKey", "ImportePendiente", "Fecha", "Dias"])
        
    inv_allocs.sort_values(["SetID", "Fecha_pago"], inplace=True)
    last_status = inv_allocs.drop_duplicates(subset=["DocKey"], keep="last")
    
    pend = last_status[last_status["ResidualFacturaTras"] > tol].copy()
    
    if pend.empty:
        return pd.DataFrame(columns=["Tercero", "DocKey", "ImportePendiente", "Fecha", "Dias"])

    today = pd.Timestamp.today().normalize()
    pend["Dias"] = (today - pend["Fecha_doc"]).dt.days
    
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
        "Unallocated": "Sense factura"
    }
    return translations.get(method, method)

def get_row_status(row: pd.Series, tol: float) -> str:
    """Determine the status of a reconciliation row for coloring"""
    method = row.get("MatchMethod", "")
    asignado = row.get("Asignado", 0)
    residual = row.get("ResidualFacturaTras", 0)

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
    if status == "green":
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
            df = df[df[sch["fecha"]].notna()].copy()
            
        meta_info["Filas_Procesables"] = len(df)

        df["_collective"] = df[sch["cuenta"]].astype(str).str.strip().apply(
            lambda s: "AR" if s.startswith(ar_prefix) else ("AP" if s.startswith(ap_prefix) else "OTROS")
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

        for coll, sub in df[df["_collective"].isin(["AR","AP"])].copy().groupby("_collective"):
            sub = sub.reset_index(drop=True)
            net = sub[net_col].fillna(0).astype(float)
            if coll == "AR":
                net_norm = net # AR: Invoice > 0
            else:
                net_norm = -net # AP: Invoice > 0 (usually Credit in accounting, so we invert)

            work = pd.DataFrame({
                "hoja": sheet_name,
                "fecha": sub["_fecha"],
                "tercero": sub["_tercero"].astype(str).replace({"nan": None}),
                "doc": sub["_doc"].astype(str).replace({"nan": None}),
                "concepto": sub["_concepto"].astype(str).replace({"nan": None}),
                "cuenta": sub[sch["cuenta"]].astype(str),
                "neto": net,
                "neto_norm": net_norm,
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
                            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
                            if row_format:
                                date_format.set_bg_color(row_format.bg_color if hasattr(row_format, 'bg_color') else None)
                            worksheet.write_datetime(current_row, col_num, value, date_format)
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

def process_excel(file_content: bytes, tol: float, ar_prefix: str, ap_prefix: str, justifications: Optional[Dict[str, str]] = None) -> Tuple[Dict, io.BytesIO]:
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

    # Write Excel with formatting
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
