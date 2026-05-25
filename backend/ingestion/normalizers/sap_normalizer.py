import pandas as pd
import io
import re
from .base import BaseNormalizer


class SAPNormalizer(BaseNormalizer):
    """
    Normalizes SAP fuel/procurement CSV exports.

    Real-world SAP exports commonly have:
    - German column headers (Buchungsdatum, Menge, Werk, etc.)
    - Mixed units (liters, gallons, m3)
    - Plant codes like DE01, UK_PLANT_03, PLANT-GB01
    - SAP material codes instead of readable names
    - Period columns in YYYYMM format (e.g., 202403)
    - Negative entries for reversals/corrections
    - Empty rows between sections
    - Multiple company codes (Buchungskreis)
    """

    # SAP material codes to fuel type mapping
    SAP_MATERIAL_MAP = {
        # Diesel variants
        'DIES-001': 'diesel', 'DIES001': 'diesel', 'D-100': 'diesel',
        'DIESEL': 'diesel', 'B7': 'diesel', 'HVO': 'diesel_hvo',
        'GASOIL': 'diesel', 'GO-001': 'diesel',
        # Petrol
        'PETR-001': 'petrol', 'PETROL': 'petrol', 'PETRL001': 'petrol',
        'E5': 'petrol', 'E10': 'petrol', 'RON95': 'petrol',
        # Gas
        'LPG-001': 'lpg', 'LPG': 'lpg', 'CNG': 'cng',
        'NATGAS': 'natural_gas',
        # Procurement categories
        'CHEM-001': 'chemicals', 'PACK-001': 'packaging',
    }

    # Column detection patterns
    DATE_COLS = {'buchungsdatum', 'posting_date', 'date', 'datum', 'belegdatum',
                 'document_date', 'budat', 'bldat'}
    QTY_COLS = {'menge', 'quantity', 'qty', 'verbrauch', 'consumption', 'amount_qty'}
    UNIT_COLS = {'mengeneinheit', 'bme', 'unit', 'uom', 'einheit', 'meins'}
    PLANT_COLS = {'werk', 'plant', 'werks', 'plant_code', 'standort', 'location'}
    MATERIAL_COLS = {'material', 'matnr', 'material_number', 'mat_nr', 'kraftstoff'}
    COST_COLS = {'betrag', 'amount', 'kosten', 'cost', 'wrbtr', 'value'}
    CURRENCY_COLS = {'waehrung', 'currency', 'waers', 'curr'}
    SUPPLIER_COLS = {'lieferant', 'vendor', 'supplier', 'lief', 'lifnr'}
    PERIOD_COLS = {'periode', 'period', 'monat', 'geschaeftsjahr', 'fiscal_period'}

    def detect_column(self, df_cols: list, target_cols: set) -> str | None:
        """Find first matching column from a set of candidates"""
        for col in df_cols:
            if col.lower().strip() in target_cols:
                return col
        # Fuzzy: partial match
        for col in df_cols:
            for target in target_cols:
                if target in col.lower():
                    return col
        return None

    def normalize_plant_code(self, plant: str) -> str:
        """Clean plant codes: DE01, UK_PLANT_03 → DE01, UK_PLANT_03"""
        if not plant or pd.isna(plant):
            return 'UNKNOWN'
        clean = str(plant).strip().upper()
        # Remove leading zeros in numeric part: 0001 → 1
        # But keep meaningful codes like DE01
        return re.sub(r'\s+', '_', clean)

    def parse_period(self, period_val) -> tuple:
        """Parse SAP period YYYYMM into (year, month) or return None"""
        if pd.isna(period_val):
            return None, None
        s = str(int(period_val)) if isinstance(period_val, float) else str(period_val).strip()
        if len(s) == 6:  # YYYYMM
            try:
                return int(s[:4]), int(s[4:])
            except ValueError:
                pass
        return None, None

    def resolve_material(self, mat_code: str) -> str:
        """Map SAP material code to human-readable fuel/material type"""
        if not mat_code or pd.isna(mat_code):
            return 'unknown'
        code = str(mat_code).strip().upper()
        return self.SAP_MATERIAL_MAP.get(code, code.lower())

    def normalize(self, file_content: bytes, filename: str) -> dict:
        """
        Main normalization entry point.
        Returns dict with: records, errors, warnings, stats
        """
        records = []
        errors = []
        warnings = []

        try:
            # Try multiple encodings (SAP often exports in Latin-1/Windows-1252)
            df = None
            for encoding in ['utf-8', 'latin-1', 'windows-1252', 'utf-8-sig']:
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding=encoding,
                                     sep=None, engine='python', skip_blank_lines=True,
                                     on_bad_lines='warn')
                    break
                except Exception:
                    continue

            if df is None:
                return {'records': [], 'errors': ['Could not parse file'], 'warnings': [], 'stats': {}}

            original_rows = len(df)

            # Drop fully empty rows
            df = df.dropna(how='all')

            # Normalize column names
            df = self.normalize_column_names(df)
            cols = list(df.columns)

            # Detect key columns
            date_col = self.detect_column(cols, self.DATE_COLS)
            qty_col = self.detect_column(cols, self.QTY_COLS)
            unit_col = self.detect_column(cols, self.UNIT_COLS)
            plant_col = self.detect_column(cols, self.PLANT_COLS)
            material_col = self.detect_column(cols, self.MATERIAL_COLS)
            cost_col = self.detect_column(cols, self.COST_COLS)
            currency_col = self.detect_column(cols, self.CURRENCY_COLS)
            supplier_col = self.detect_column(cols, self.SUPPLIER_COLS)
            period_col = self.detect_column(cols, self.PERIOD_COLS)

            if not qty_col:
                errors.append(f"Could not find quantity column. Found columns: {cols}")
                return {'records': [], 'errors': errors, 'warnings': warnings, 'stats': {}}

            for idx, row in df.iterrows():
                row_num = idx + 2  # 1-based, skip header
                row_errors = []
                row_warnings = []
                notes = []

                # --- Date ---
                activity_date = None
                if date_col:
                    activity_date = self.normalize_date(row.get(date_col))
                if activity_date is None and period_col:
                    yr, mo = self.parse_period(row.get(period_col))
                    if yr and mo:
                        from datetime import date
                        activity_date = date(yr, mo, 1)
                        notes.append(f"Date inferred from period {row.get(period_col)}")
                if activity_date is None:
                    row_errors.append(f"Row {row_num}: Cannot parse date")

                # --- Quantity ---
                qty = self.safe_float(row.get(qty_col))
                original_qty = qty
                original_unit_str = str(row.get(unit_col, '')).strip() if unit_col else ''
                raw_unit = self.normalize_unit(original_unit_str)
                qty, unit = self.normalize_quantity_to_base(qty, raw_unit)

                if original_qty < 0:
                    row_warnings.append(f"Row {row_num}: Negative quantity ({original_qty}) - possible reversal")
                if original_unit_str and raw_unit != original_unit_str.lower():
                    notes.append(f"Unit normalized: '{original_unit_str}' → '{unit}'")

                # --- Material/Fuel type ---
                material_raw = str(row.get(material_col, '')) if material_col else ''
                subcategory = self.resolve_material(material_raw)
                if subcategory == material_raw.lower() and material_raw:
                    notes.append(f"Unknown material code: {material_raw}")

                # Determine if fuel or procurement
                fuel_types = {'diesel', 'petrol', 'lpg', 'cng', 'natural_gas', 'diesel_hvo'}
                if subcategory in fuel_types:
                    category = 'scope1_fuel'
                else:
                    category = 'scope3_procurement'

                # --- Cost ---
                cost = self.safe_float(row.get(cost_col)) if cost_col else None
                currency = str(row.get(currency_col, 'EUR')).strip() if currency_col else 'EUR'

                # --- Plant/Location ---
                plant = self.normalize_plant_code(row.get(plant_col)) if plant_col else ''

                # --- Supplier ---
                supplier = str(row.get(supplier_col, '')).strip() if supplier_col else ''

                # Calculate CO2e
                co2e = self.calculate_co2e(category, subcategory, qty, unit)
                if co2e == 0 and category == 'scope1_fuel':
                    row_warnings.append(f"Row {row_num}: CO2e is 0 - missing emission factor for {subcategory}")

                # Quality scoring
                quality_score, quality_issues = self.score_quality(
                    {'quantity': qty, 'activity_date': activity_date, 'unit': unit},
                    ['quantity', 'activity_date', 'unit']
                )
                quality_issues.extend(row_errors + row_warnings)

                record = {
                    'category': category,
                    'subcategory': subcategory,
                    'activity_date': activity_date,
                    'quantity': qty,
                    'unit': unit,
                    'co2e_kg': co2e,
                    'location': plant,
                    'supplier': supplier,
                    'cost_original': cost,
                    'currency_original': currency,
                    'cost_gbp': cost * 0.85 if cost and currency == 'EUR' else cost,
                    'raw_data': {k: (str(v) if not pd.isna(v) else None)
                                 for k, v in row.items()},
                    'normalization_notes': ' | '.join(notes) if notes else '',
                    'quality_score': quality_score,
                    'quality_issues': quality_issues,
                    'is_suspicious': quality_score < 0.6 or bool(row_errors),
                    'row_errors': row_errors,
                }
                records.append(record)

        except Exception as e:
            errors.append(f"Fatal parse error: {str(e)}")

        return {
            'records': records,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_input_rows': original_rows if 'original_rows' in dir() else 0,
                'parsed_records': len(records),
            }
        }
