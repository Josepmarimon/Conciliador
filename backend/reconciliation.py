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
    keywords = [r"fecha", r"date", r"cuenta", r"account", r"debe", r"debit", r"haber", r"credit", r"saldo", r"balance"]
    
    for idx, row in df_head.iterrows():
        row_str = " ".join([str(x).lower() for x in row.values])
        score = 0
        for kw in keywords:
            if re.search(kw, row_str):
                score += 1
        if score > max_score:
            max_score = score
            best_idx = idx
            
    if max_score < 2: 
        return 0
    return best_idx

def detect_schema(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    date_col   = find_col(df, [r"fecha", r"date", r"f\.?contab", r"asiento.*fecha"])
    cuenta_col = find_col(df, [r"cuenta", r"cta", r"account", r"cod.*cta"])
    debe_col   = find_col(df, [r"debe", r"cargo", r"debit"])
    haber_col  = find_col(df, [r"haber", r"abono", r"credit"])
    saldo_col  = find_col(df, [r"saldo", r"balance"])
    tercero_col= find_col(df, [r"descripci[oó]n", r"proveedor", r"cliente", r"tercero", r"contrapartida", r"nombre", r"raz[oó]n\s*social"])
    doc_col    = find_col(df, [r"factura", r"documento", r"n[ºo]\s*doc", r"n[úu]mero", r"ref"])
    concepto_col=find_col(df, [r"concepto", r"desc", r"glosa", r"detalle", r"narr"])
    
    schema = {
        "fecha": date_col, "cuenta": cuenta_col, "debe": debe_col, "haber": haber_col,
        "saldo": saldo_col, "tercero": tercero_col, "documento": doc_col, "concepto": concepto_col
    }
    
    # Fallback for headless sheets
    if not (schema["fecha"] and schema["cuenta"] and (schema["debe"] or schema["haber"])):
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
    """Extract potential invoice references from text using common patterns"""
    if not text:
        return []

    text = str(text).upper()
    references = []

    # Common invoice patterns
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

        # --- Phase 3: Date Proximity Match (NEW) ---
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

        # --- Phase 4: FIFO Fallback ---
        if payment_left > self.tol:
            for idx, inv in enumerate(self.open_invoices):
                if inv["remaining"] <= self.tol:
                    continue

                take = min(inv["remaining"], payment_left)
                # Low confidence for FIFO matches
                confidence = 50
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
                "Confidence": round(confidence, 1)
            })

        # Cleanup fully paid invoices
        self.open_invoices = [inv for inv in self.open_invoices if inv["remaining"] > self.tol]

        # Handle Unallocated Payment
        if payment_left > self.tol:
            self.out_rows.append({
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
                "Confidence": 0  # 0% confidence for unallocated
            })
            
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
                "Confidence": 0  # 0% confidence for open invoices
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

def generate_reconciliation_data(file_content: bytes, tol: float, ar_prefix: str, ap_prefix: str, sheet_filter: Optional[str] = None) -> Tuple[Dict[str, pd.DataFrame], List[Dict], Optional[str], Optional[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_content))

    ar_rows = []
    ap_rows = []
    meta_rows = []
    company_name = None
    period = None

    sheets_to_process = [sheet_filter] if sheet_filter else xls.sheet_names

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
        meta_info["Filas_AR"] = counts.get("AR", 0)
        meta_info["Filas_AP"] = counts.get("AP", 0)
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
        out_sheets["AR_Detalle"] = det_ar
        out_sheets["Pendientes_AR"] = build_pendientes(det_ar, tol)

    # AP Processing
    det_ap = pd.DataFrame()
    if ap_rows:
        ap_all = pd.concat(ap_rows, ignore_index=True)
        ap_all["idx"] = np.arange(len(ap_all))
        det_ap = reconcile_fifo(ap_all, tol=tol)
        out_sheets["AP_Detalle"] = det_ap
        out_sheets["Pendientes_AP"] = build_pendientes(det_ap, tol)

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
        quick_summary(det_ar, "AR", "Pendientes_AR"),
        quick_summary(det_ap, "AP", "Pendientes_AP")
    ]
    
    out_sheets["Resumen"] = pd.DataFrame(summary_list)
    out_sheets["Meta"] = pd.DataFrame([
        {k: str(v) if isinstance(v, dict) else v for k, v in r.items()} 
        for r in meta_rows
    ])
    
    return out_sheets, summary_list, company_name, period

def process_excel(file_content: bytes, tol: float, ar_prefix: str, ap_prefix: str, justifications: Optional[Dict[str, str]] = None) -> Tuple[Dict, io.BytesIO]:
    out_sheets, summary_list, company_name, period = generate_reconciliation_data(file_content, tol, ar_prefix, ap_prefix)

    # Add justifications to detail sheets if provided
    if justifications:
        for sheet_name in ["AR_Detalle", "AP_Detalle"]:
            if sheet_name in out_sheets and not out_sheets[sheet_name].empty:
                df = out_sheets[sheet_name]
                # Add justification column
                df["Justificacion"] = df.apply(
                    lambda row: justifications.get(f"{row['SetID']}-{row['PagoKey']}", "")
                    if row["MatchMethod"] == "Unallocated" else "",
                    axis=1
                )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, data in out_sheets.items():
            data.to_excel(writer, sheet_name=name[:31], index=False)
    
    output.seek(0)
    
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
        if name in ["AR_Detalle", "AP_Detalle", "Pendientes_AR", "Pendientes_AP"]:
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
