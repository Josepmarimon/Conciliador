#!/usr/bin/env python3
import argparse
import sys
import pandas as pd
from pathlib import Path
from reconciliation import generate_reconciliation_data

def main():
    parser = argparse.ArgumentParser(description="Conciliador FIFO AR/AP")
    parser.add_argument("input", help="Ruta al Excel de entrada")
    parser.add_argument("-o", "--output", help="Ruta al Excel de salida")
    parser.add_argument("--sheet", help="Procesar solo una hoja")
    parser.add_argument("--ar-prefix", default="43", help="Prefijo Clientes (AR)")
    parser.add_argument("--ap-prefix", default="40,41", help="Prefijo Proveedores (AP), separados por comas")
    parser.add_argument("--tol", type=float, default=0.01, help="Tolerancia")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: No se encuentra el archivo {input_path}")
        sys.exit(1)
        
    print(f"Procesando {input_path}...")
    
    try:
        content = input_path.read_bytes()
        out_sheets, summary, company_name, period = generate_reconciliation_data(
            content,
            args.tol,
            args.ar_prefix,
            args.ap_prefix,
            sheet_filter=args.sheet
        )
        
        output_path = args.output
        if not output_path:
            output_path = input_path.with_name(input_path.stem + "_conciliado.xlsx")
            
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            for name, data in out_sheets.items():
                data.to_excel(writer, sheet_name=name[:31], index=False)
                
        print(f"Conciliación completada. Guardado en: {output_path}")
        print("\nResumen:")
        print(pd.DataFrame(summary))
        
    except Exception as e:
        print(f"Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
