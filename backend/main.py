from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import pandas as pd
from reconciliation import process_excel
from stats import increment_reconciliation_count, get_stats

app = FastAPI(title="Conciliador FIFO API")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  # Explicitly allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    stats = get_stats()
    return {
        "message": "Conciliador FIFO API is running",
        "total_reconciliations": stats["total_reconciliations"]
    }

@app.get("/stats")
def get_statistics():
    """Get usage statistics"""
    return get_stats()

from pydantic import BaseModel
from typing import Dict, Optional

class ConciliationRequest(BaseModel):
    justifications: Optional[Dict[str, str]] = None

@app.post("/conciliate")
async def conciliate_endpoint(
    file: UploadFile = File(...),
    tol: float = 0.01,
    ar_prefix: str = "43",
    ap_prefix: str = "40",
    justifications: Optional[str] = None,  # JSON string of justifications
    output_format: str = "human"  # "human" (single tab like manual) or "detailed" (multi-tab)
):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file (.xlsx).")

    try:
        contents = await file.read()

        # Add debug logging
        # print(f"[DEBUG] Processing file: {file.filename}")
        # print(f"[DEBUG] File size: {len(contents)} bytes")
        # print(f"[DEBUG] Tolerance: {tol}, AR prefix: {ar_prefix}, AP prefix: {ap_prefix}")

        # Parse justifications if provided
        import json
        justifications_dict = None
        if justifications:
            try:
                justifications_dict = json.loads(justifications)
            except:
                justifications_dict = None

        response_data, output_excel = process_excel(contents, tol, ar_prefix, ap_prefix, justifications_dict, output_format)

        # print(f"[DEBUG] Company name extracted: {response_data.get('company_name')}")
        # print(f"[DEBUG] Period extracted: {response_data.get('period')}")
        # print(f"[DEBUG] Summary keys: {list(response_data.get('summary', {}).keys()) if 'summary' in response_data else 'No summary'}")

        # Count total rows processed
        total_rows = 0
        if "summary" in response_data:
            for item in response_data["summary"]:
                total_rows += item.get("Movimientos", 0)

        # Increment statistics
        stats = increment_reconciliation_count(total_rows)

        import base64
        b64_file = base64.b64encode(output_excel.getvalue()).decode()
        
        return {
            "summary": response_data["summary"],
            "meta": response_data["meta"],
            "details": response_data.get("details", {}),
            "company_name": response_data.get("company_name"),
            "period": response_data.get("period"),
            "filename": file.filename.replace(".xlsx", "_conciliado.xlsx"),
            "file_b64": b64_file
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
