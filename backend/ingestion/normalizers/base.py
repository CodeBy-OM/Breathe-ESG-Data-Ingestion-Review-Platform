import pandas as pd
from datetime import datetime, date
from dateutil import parser as dateparser
from typing import Optional
import re


class BaseNormalizer:
    """
    Base class for all data source normalizers.
    Handles common transformations: dates, units, currencies, quality scoring.
    """

    # German->English column name mappings for SAP exports
    GERMAN_COLUMN_MAP = {
        'buchungsdatum': 'posting_date',
        'menge': 'quantity',
        'mengeneinheit': 'unit',
        'werk': 'plant',
        'material': 'material',
        'lieferant': 'supplier',
        'betrag': 'amount',
        'waehrung': 'currency',
        'kostenstelle': 'cost_center',
        'buchungskreis': 'company_code',
        'bezeichnung': 'description',
        'verbrauch': 'consumption',
        'kraftstoff': 'fuel_type',
        'datum': 'date',
        'periode': 'period',
        'maßeinheit': 'unit_of_measure',
        'einheit': 'unit',
        'liter': 'liters',
        'kilowattstunde': 'kwh',
    }

    # Unit normalization mappings
    UNIT_MAP = {
        # Volume
        'l': 'liters', 'ltr': 'liters', 'litre': 'liters', 'litres': 'liters',
        'liter': 'liters', 'liters': 'liters',
        'gal': 'gallons', 'gallon': 'gallons', 'gallons': 'gallons',
        'gals': 'gallons',
        'm3': 'cubic_meters', 'cubic meter': 'cubic_meters',

        # Energy
        'kwh': 'kwh', 'kilowatt hour': 'kwh', 'kilowatt-hour': 'kwh',
        'kw/h': 'kwh', 'kw·h': 'kwh',
        'mwh': 'mwh', 'megawatt hour': 'mwh',
        'gj': 'gj', 'gigajoule': 'gj',
        'mmbtu': 'mmbtu',

        # Distance
        'km': 'km', 'kilometer': 'km', 'kilometres': 'km', 'kilometers': 'km',
        'mi': 'miles', 'mile': 'miles', 'miles': 'miles',

        # Weight
        'kg': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
        't': 'tonnes', 'ton': 'tonnes', 'tonne': 'tonnes', 'tonnes': 'tonnes',
        'mt': 'tonnes',

        # Count
        'nights': 'nights', 'night': 'nights',
        'trips': 'trips', 'trip': 'trips',
        'pax': 'passengers',
    }

    # Conversion factors to base units
    UNIT_CONVERSIONS = {
        'gallons_to_liters': 3.78541,
        'miles_to_km': 1.60934,
        'mwh_to_kwh': 1000.0,
        'gj_to_kwh': 277.778,
        'mmbtu_to_kwh': 293.071,
        'cubic_meters_to_liters': 1000.0,
    }

    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize German/mixed column names to standard English snake_case"""
        renamed = {}
        for col in df.columns:
            clean = col.strip().lower()
            clean = re.sub(r'[^a-z0-9äöüß_]', '_', clean)
            clean = re.sub(r'_+', '_', clean).strip('_')
            english = self.GERMAN_COLUMN_MAP.get(clean, clean)
            renamed[col] = english
        df = df.rename(columns=renamed)
        return df

    def normalize_date(self, value) -> Optional[date]:
        """Parse various date formats to Python date"""
        if pd.isna(value) or value == '' or value is None:
            return None
        if isinstance(value, (datetime, date)):
            return value.date() if isinstance(value, datetime) else value
        str_val = str(value).strip()
        # SAP date formats
        for fmt in ['%d.%m.%Y', '%Y%m%d', '%d/%m/%Y', '%m/%d/%Y',
                    '%Y-%m-%d', '%d-%m-%Y', '%b %Y', '%B %Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(str_val, fmt).date()
            except ValueError:
                continue
        try:
            return dateparser.parse(str_val, dayfirst=True).date()
        except Exception:
            return None

    def normalize_unit(self, unit_str: str) -> str:
        """Map unit string to canonical unit name"""
        if not unit_str:
            return 'unknown'
        clean = str(unit_str).strip().lower()
        return self.UNIT_MAP.get(clean, clean)

    def normalize_quantity_to_base(self, quantity: float, unit: str) -> tuple:
        """Convert quantity to base unit, return (normalized_qty, base_unit)"""
        if unit == 'gallons':
            return quantity * self.UNIT_CONVERSIONS['gallons_to_liters'], 'liters'
        if unit == 'miles':
            return quantity * self.UNIT_CONVERSIONS['miles_to_km'], 'km'
        if unit == 'mwh':
            return quantity * self.UNIT_CONVERSIONS['mwh_to_kwh'], 'kwh'
        if unit == 'gj':
            return quantity * self.UNIT_CONVERSIONS['gj_to_kwh'], 'kwh'
        if unit == 'mmbtu':
            return quantity * self.UNIT_CONVERSIONS['mmbtu_to_kwh'], 'kwh'
        if unit == 'cubic_meters':
            return quantity * self.UNIT_CONVERSIONS['cubic_meters_to_liters'], 'liters'
        return quantity, unit

    def score_quality(self, record: dict, required_fields: list) -> tuple:
        """Return (score 0-1, list of issue strings)"""
        issues = []
        score = 1.0
        deduction = 1.0 / max(len(required_fields), 1)

        for field in required_fields:
            val = record.get(field)
            if val is None or val == '' or (isinstance(val, float) and pd.isna(val)):
                issues.append(f"Missing required field: {field}")
                score -= deduction

        # Check for suspicious values
        qty = record.get('quantity', 0)
        if isinstance(qty, (int, float)):
            if qty < 0:
                issues.append("Negative quantity value")
                score -= 0.2
            if qty == 0:
                issues.append("Zero quantity - possibly missing data")
                score -= 0.1

        return max(0.0, round(score, 2)), issues

    def safe_float(self, value, default=0.0) -> float:
        """Safely convert value to float"""
        try:
            if pd.isna(value):
                return default
        except (TypeError, ValueError):
            pass
        try:
            clean = str(value).replace(',', '').replace(' ', '').strip()
            return float(clean)
        except (ValueError, TypeError):
            return default

    def calculate_co2e(self, category: str, subcategory: str, quantity: float, unit: str) -> float:
        """Calculate CO2e in kg based on emission factors"""
        from django.conf import settings
        ef = settings.EMISSION_FACTORS

        if category == 'scope1_fuel':
            if subcategory in ('diesel', 'diesel_liter'):
                return quantity * ef.get('diesel_liter', 2.68)
            elif subcategory in ('petrol', 'gasoline'):
                return quantity * ef.get('petrol_liter', 2.31)

        elif category == 'scope2_electricity':
            if unit == 'kwh':
                return quantity * ef.get('electricity_kwh', 0.233)
            elif unit == 'mwh':
                return quantity * 1000 * ef.get('electricity_kwh', 0.233)

        elif category == 'scope3_travel':
            if subcategory == 'flight':
                return quantity * ef.get('flight_km_economy', 0.255)
            elif subcategory == 'hotel':
                return quantity * ef.get('hotel_night', 31.0)
            elif subcategory in ('car', 'taxi', 'cab'):
                return quantity * ef.get('car_km', 0.171)

        return 0.0
