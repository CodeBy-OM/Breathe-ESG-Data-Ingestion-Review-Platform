import pandas as pd
import io
import re
from datetime import date
from .base import BaseNormalizer


class UtilityNormalizer(BaseNormalizer):
    """
    Normalizes electricity/utility CSV exports.

    Handles:
    - Utility portal CSV exports (UK Power Networks, Octopus, British Gas, etc.)
    - Smart meter data exports
    - Billing period data
    - Multiple meters per site
    - kWh, MWh, GJ units
    - Half-hourly data vs monthly billing
    - Tariff information (unit rate, standing charge)
    - Estimated vs actual reads
    """

    DATE_COLS = {'date', 'billing_date', 'invoice_date', 'period_start', 'period_end',
                 'read_date', 'start_date', 'end_date', 'from_date', 'to_date',
                 'meter_read_date', 'supply_date'}
    QTY_COLS = {'consumption', 'quantity', 'kwh', 'units', 'usage', 'energy',
                'total_kwh', 'net_kwh', 'actual_usage', 'import_kwh'}
    METER_COLS = {'meter_id', 'mpan', 'mprn', 'meter_number', 'serial_number',
                  'meter_serial', 'meter_ref', 'supply_number'}
    SITE_COLS = {'site', 'premises', 'address', 'location', 'site_name', 'property',
                 'supply_address', 'building'}
    TARIFF_COLS = {'tariff', 'rate', 'unit_rate', 'tariff_name', 'product'}
    COST_COLS = {'cost', 'total', 'amount', 'charge', 'net_cost', 'total_cost',
                 'bill_amount', 'invoice_total', 'subtotal'}
    READ_TYPE_COLS = {'read_type', 'type', 'status', 'read_status', 'estimated'}
    PERIOD_START_COLS = {'period_start', 'start_date', 'from_date', 'from', 'bill_from'}
    PERIOD_END_COLS = {'period_end', 'end_date', 'to_date', 'to', 'bill_to'}

    def detect_column(self, df_cols, target_cols):
        for col in df_cols:
            if col.lower().strip() in target_cols:
                return col
        for col in df_cols:
            for target in target_cols:
                if target in col.lower():
                    return col
        return None

    def normalize_read_type(self, read_type: str) -> str:
        """Normalize read type: estimated, actual, etc."""
        if not read_type or pd.isna(read_type):
            return 'unknown'
        rt = str(read_type).strip().lower()
        if any(e in rt for e in ['estim', 'e', 'est']):
            return 'estimated'
        if any(a in rt for a in ['actual', 'a', 'read', 'metered']):
            return 'actual'
        return rt

    def detect_unit_from_column_name(self, df: pd.DataFrame) -> str:
        """Try to detect energy unit from column header itself"""
        for col in df.columns:
            col_lower = col.lower()
            if 'mwh' in col_lower:
                return 'mwh'
            if 'kwh' in col_lower or 'kw/h' in col_lower:
                return 'kwh'
            if 'gj' in col_lower:
                return 'gj'
        return 'kwh'  # default assumption

    def normalize(self, file_content: bytes, filename: str) -> dict:
        records = []
        errors = []
        warnings = []

        try:
            df = None
            for encoding in ['utf-8', 'latin-1', 'utf-8-sig']:
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding=encoding,
                                     sep=None, engine='python', skip_blank_lines=True)
                    break
                except Exception:
                    continue

            if df is None:
                return {'records': [], 'errors': ['Cannot parse utility file'], 'warnings': [], 'stats': {}}

            original_rows = len(df)
            df = df.dropna(how='all')
            df = self.normalize_column_names(df)
            cols = list(df.columns)

            # Detect columns
            date_col = self.detect_column(cols, self.DATE_COLS)
            qty_col = self.detect_column(cols, self.QTY_COLS)
            meter_col = self.detect_column(cols, self.METER_COLS)
            site_col = self.detect_column(cols, self.SITE_COLS)
            cost_col = self.detect_column(cols, self.COST_COLS)
            read_type_col = self.detect_column(cols, self.READ_TYPE_COLS)
            period_start_col = self.detect_column(cols, self.PERIOD_START_COLS)
            period_end_col = self.detect_column(cols, self.PERIOD_END_COLS)
            tariff_col = self.detect_column(cols, self.TARIFF_COLS)

            # Detect column-level unit hint
            default_unit = self.detect_unit_from_column_name(df)

            for idx, row in df.iterrows():
                row_num = idx + 2
                notes = []
                row_warnings = []

                # Date
                activity_date = None
                period_start = None
                period_end = None

                if period_start_col:
                    period_start = self.normalize_date(row.get(period_start_col))
                if period_end_col:
                    period_end = self.normalize_date(row.get(period_end_col))
                if date_col:
                    activity_date = self.normalize_date(row.get(date_col))

                # Use period_end as activity_date if no explicit date
                if activity_date is None and period_end:
                    activity_date = period_end
                    notes.append("Activity date set from period_end")
                elif activity_date is None and period_start:
                    activity_date = period_start
                    notes.append("Activity date set from period_start")

                if activity_date is None:
                    row_warnings.append(f"Row {row_num}: No date found")

                # Quantity / Consumption
                qty = self.safe_float(row.get(qty_col, 0)) if qty_col else 0

                # Check for explicit unit in row vs column header hint
                unit_str = default_unit
                for col in cols:
                    if 'unit' in col.lower() or col.lower() in ('uom', 'unit_of_measure'):
                        unit_str = self.normalize_unit(str(row.get(col, default_unit)))
                        break

                # Normalize to kWh
                qty_kwh, unit = self.normalize_quantity_to_base(qty, unit_str)
                if unit_str != 'kwh' and qty != qty_kwh:
                    notes.append(f"Converted {qty} {unit_str} → {qty_kwh:.2f} kWh")

                # Meter ID
                meter_id = str(row.get(meter_col, '')).strip() if meter_col else ''

                # Site/Location
                site = str(row.get(site_col, '')).strip() if site_col else ''

                # Cost
                cost = self.safe_float(row.get(cost_col)) if cost_col else None

                # Read type
                read_type = self.normalize_read_type(row.get(read_type_col)) if read_type_col else 'unknown'
                if read_type == 'estimated':
                    row_warnings.append(f"Row {row_num}: Estimated meter read - may need verification")

                # Tariff
                tariff = str(row.get(tariff_col, '')).strip() if tariff_col else ''

                # CO2e
                co2e = self.calculate_co2e('scope2_electricity', 'electricity', qty_kwh, 'kwh')

                # Quality
                quality_score, quality_issues = self.score_quality(
                    {'quantity': qty_kwh, 'activity_date': activity_date},
                    ['quantity', 'activity_date']
                )
                if read_type == 'estimated':
                    quality_score = max(0, quality_score - 0.1)
                    quality_issues.append("Estimated read - lower confidence")

                quality_issues.extend(row_warnings)

                records.append({
                    'category': 'scope2_electricity',
                    'subcategory': 'electricity',
                    'activity_date': activity_date,
                    'period_start': period_start,
                    'period_end': period_end,
                    'quantity': qty_kwh,
                    'unit': 'kwh',
                    'co2e_kg': co2e,
                    'location': site,
                    'supplier': str(row.get('supplier', '')).strip() if 'supplier' in cols else '',
                    'cost_original': cost,
                    'cost_gbp': cost,
                    'currency_original': 'GBP',
                    'raw_data': {
                        k: (str(v) if not pd.isna(v) else None)
                        for k, v in row.items()
                    },
                    'normalization_notes': ' | '.join(notes + [
                        f"meter={meter_id}",
                        f"read_type={read_type}",
                        f"tariff={tariff}",
                    ]),
                    'quality_score': quality_score,
                    'quality_issues': quality_issues,
                    'is_suspicious': quality_score < 0.6,
                    'row_errors': [],
                })

        except Exception as e:
            errors.append(f"Fatal error parsing utility file: {str(e)}")

        return {
            'records': records,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_input_rows': original_rows if 'original_rows' in dir() else 0,
                'parsed_records': len(records),
            }
        }
