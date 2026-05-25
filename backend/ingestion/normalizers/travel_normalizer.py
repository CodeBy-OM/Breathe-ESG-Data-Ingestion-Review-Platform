import pandas as pd
import io
import re
import math
from datetime import date
from .base import BaseNormalizer


# IATA airport coordinate lookup (subset for distance estimation)
AIRPORT_COORDS = {
    'LHR': (51.477, -0.461), 'LGW': (51.148, -0.190), 'MAN': (53.354, -2.275),
    'EDI': (55.950, -3.373), 'GLA': (55.872, -4.433), 'BHX': (52.454, -1.748),
    'JFK': (40.640, -73.779), 'LAX': (33.943, -118.408), 'ORD': (41.975, -87.908),
    'ATL': (33.640, -84.427), 'DFW': (32.899, -97.040), 'DEN': (39.856, -104.674),
    'CDG': (49.013, 2.550), 'AMS': (52.308, 4.764), 'FRA': (50.026, 8.543),
    'MAD': (40.472, -3.561), 'FCO': (41.804, 12.251), 'BCN': (41.297, 2.078),
    'ZRH': (47.458, 8.548), 'MUC': (48.354, 11.786), 'VIE': (48.110, 16.570),
    'DXB': (25.253, 55.364), 'SIN': (1.359, 103.989), 'HKG': (22.309, 113.915),
    'NRT': (35.765, 140.386), 'SYD': (-33.947, 151.179), 'MEL': (-37.673, 144.843),
    'BOM': (19.089, 72.868), 'DEL': (28.556, 77.100), 'BLR': (13.199, 77.706),
    'JNB': (-26.134, 28.242), 'CPT': (-33.965, 18.602),
    'YYZ': (43.677, -79.631), 'YVR': (49.194, -123.184),
    'GRU': (-23.432, -46.469), 'MEX': (19.436, -99.072),
}


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Calculate great-circle distance between two points in km"""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def estimate_flight_distance(origin: str, destination: str) -> tuple:
    """Estimate flight distance from IATA codes. Returns (km, method)"""
    o = origin.strip().upper()
    d = destination.strip().upper()
    if o in AIRPORT_COORDS and d in AIRPORT_COORDS:
        lat1, lon1 = AIRPORT_COORDS[o]
        lat2, lon2 = AIRPORT_COORDS[d]
        dist = haversine_km(lat1, lon1, lat2, lon2)
        # Add 5% for actual flight paths being non-direct
        return dist * 1.05, 'calculated_haversine'
    return None, 'unknown'


class TravelNormalizer(BaseNormalizer):
    """
    Normalizes corporate travel data from Concur/Navan/Egencia exports.

    Handles:
    - Flight segments (IATA codes, class of service)
    - Hotel stays (nights, city)
    - Ground transport (car hire, taxi, rail)
    - Missing distance data (estimated from IATA)
    - Multi-leg journeys
    - Expense categories vs travel categories
    - Multiple currencies
    """

    # Travel category detection
    FLIGHT_KEYWORDS = {'flight', 'air', 'airline', 'aviation', 'fly', 'plane',
                       'economy', 'business class', 'first class', 'airfare'}
    HOTEL_KEYWORDS = {'hotel', 'accommodation', 'lodging', 'stay', 'b&b',
                      'inn', 'motel', 'hostel', 'resort', 'bnb'}
    CAR_KEYWORDS = {'car hire', 'car rental', 'rental car', 'vehicle hire', 'taxi',
                    'cab', 'uber', 'lyft', 'chauffeur', 'minicab', 'ground transport'}
    RAIL_KEYWORDS = {'rail', 'train', 'eurostar', 'amtrak', 'thalys', 'intercity',
                     'bus', 'coach'}

    # Class of service
    BUSINESS_CLASS_KEYWORDS = {'business', 'first', 'premium', 'club', 'j class', 'c class'}

    DATE_COLS = {'date', 'travel_date', 'departure_date', 'booking_date',
                 'transaction_date', 'check_in', 'checkin_date', 'trip_date'}
    CATEGORY_COLS = {'category', 'type', 'expense_type', 'travel_type',
                     'transaction_type', 'service_type', 'segment_type'}
    ORIGIN_COLS = {'origin', 'from', 'departure', 'origin_code', 'from_airport',
                   'departure_airport', 'departure_city'}
    DEST_COLS = {'destination', 'to', 'arrival', 'dest_code', 'to_airport',
                 'arrival_airport', 'destination_city', 'arrival_city'}
    DIST_COLS = {'distance', 'distance_km', 'km', 'miles', 'dist', 'route_km'}
    NIGHTS_COLS = {'nights', 'num_nights', 'number_of_nights', 'duration_nights', 'stay_nights'}
    COST_COLS = {'cost', 'amount', 'total', 'fare', 'price', 'spend', 'total_cost',
                 'transaction_amount', 'amount_gbp', 'amount_usd', 'amount_eur'}
    CURRENCY_COLS = {'currency', 'curr', 'currency_code'}
    TRAVELER_COLS = {'traveler', 'employee', 'passenger', 'person', 'name',
                     'traveller_name', 'employee_id', 'emp_id'}
    CLASS_COLS = {'class', 'cabin', 'service_class', 'fare_class', 'ticket_class'}
    SUPPLIER_COLS = {'supplier', 'vendor', 'airline', 'hotel_name', 'carrier'}

    def detect_column(self, df_cols, target_cols):
        for col in df_cols:
            if col.lower().strip() in target_cols:
                return col
        for col in df_cols:
            for target in target_cols:
                if target in col.lower():
                    return col
        return None

    def detect_travel_category(self, cat_str: str) -> str:
        """Map raw category string to canonical travel type"""
        if not cat_str or pd.isna(cat_str):
            return 'other'
        s = str(cat_str).lower()
        if any(k in s for k in self.FLIGHT_KEYWORDS):
            return 'flight'
        if any(k in s for k in self.HOTEL_KEYWORDS):
            return 'hotel'
        if any(k in s for k in self.CAR_KEYWORDS):
            return 'car'
        if any(k in s for k in self.RAIL_KEYWORDS):
            return 'rail'
        return 'other'

    def detect_class_of_service(self, class_str: str) -> str:
        if not class_str or pd.isna(class_str):
            return 'economy'
        s = str(class_str).lower()
        if any(k in s for k in self.BUSINESS_CLASS_KEYWORDS):
            return 'business'
        return 'economy'

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
                return {'records': [], 'errors': ['Cannot parse travel file'], 'warnings': [], 'stats': {}}

            original_rows = len(df)
            df = df.dropna(how='all')
            df = self.normalize_column_names(df)
            cols = list(df.columns)

            date_col = self.detect_column(cols, self.DATE_COLS)
            cat_col = self.detect_column(cols, self.CATEGORY_COLS)
            origin_col = self.detect_column(cols, self.ORIGIN_COLS)
            dest_col = self.detect_column(cols, self.DEST_COLS)
            dist_col = self.detect_column(cols, self.DIST_COLS)
            nights_col = self.detect_column(cols, self.NIGHTS_COLS)
            cost_col = self.detect_column(cols, self.COST_COLS)
            currency_col = self.detect_column(cols, self.CURRENCY_COLS)
            class_col = self.detect_column(cols, self.CLASS_COLS)
            supplier_col = self.detect_column(cols, self.SUPPLIER_COLS)
            traveler_col = self.detect_column(cols, self.TRAVELER_COLS)

            for idx, row in df.iterrows():
                row_num = idx + 2
                notes = []
                row_warnings = []

                # Date
                activity_date = self.normalize_date(row.get(date_col)) if date_col else None
                if activity_date is None:
                    row_warnings.append(f"Row {row_num}: No travel date found")

                # Category
                cat_raw = str(row.get(cat_col, '')).strip() if cat_col else ''
                travel_type = self.detect_travel_category(cat_raw)

                # Origin / Destination
                origin = str(row.get(origin_col, '')).strip().upper() if origin_col else ''
                destination = str(row.get(dest_col, '')).strip().upper() if dest_col else ''

                # Distance
                distance_km = None
                distance_method = 'provided'

                if dist_col:
                    raw_dist = self.safe_float(row.get(dist_col))
                    if raw_dist > 0:
                        # Check if it's miles
                        if dist_col and 'mile' in dist_col.lower():
                            distance_km = raw_dist * self.UNIT_CONVERSIONS['miles_to_km']
                            notes.append(f"Distance converted from miles: {raw_dist} mi → {distance_km:.0f} km")
                        else:
                            distance_km = raw_dist

                if (distance_km is None or distance_km == 0) and travel_type == 'flight':
                    if origin and destination:
                        calc_dist, method = estimate_flight_distance(origin, destination)
                        if calc_dist:
                            distance_km = calc_dist
                            distance_method = method
                            notes.append(f"Distance estimated: {origin}→{destination} = {distance_km:.0f} km (haversine)")
                        else:
                            row_warnings.append(f"Row {row_num}: Cannot estimate distance for {origin}→{destination}")
                            distance_km = 0
                    else:
                        row_warnings.append(f"Row {row_num}: Missing origin/destination for flight distance")
                        distance_km = 0

                # Nights (for hotels)
                nights = self.safe_float(row.get(nights_col, 1)) if nights_col else 1

                # Class of service
                svc_class = self.detect_class_of_service(row.get(class_col)) if class_col else 'economy'

                # Cost
                cost = self.safe_float(row.get(cost_col)) if cost_col else None
                currency = str(row.get(currency_col, 'GBP')).strip() if currency_col else 'GBP'

                # FX to GBP (approximate)
                fx_rates = {'USD': 0.79, 'EUR': 0.85, 'GBP': 1.0, 'INR': 0.0095}
                cost_gbp = cost * fx_rates.get(currency.upper(), 1.0) if cost else None

                supplier = str(row.get(supplier_col, '')).strip() if supplier_col else ''

                # Quantity and CO2e
                if travel_type == 'flight':
                    quantity = distance_km or 0
                    unit = 'km'
                    emission_sub = 'flight_business' if svc_class == 'business' else 'flight'
                    ef_key = 'flight_km_business' if svc_class == 'business' else 'flight_km_economy'
                    from django.conf import settings
                    co2e = quantity * settings.EMISSION_FACTORS.get(ef_key, 0.255)
                    if svc_class == 'business':
                        notes.append("Business class: higher emission factor applied (2x economy)")

                elif travel_type == 'hotel':
                    quantity = nights
                    unit = 'nights'
                    co2e = self.calculate_co2e('scope3_travel', 'hotel', nights, 'nights')

                elif travel_type in ('car', 'taxi'):
                    quantity = distance_km or 0
                    unit = 'km'
                    co2e = self.calculate_co2e('scope3_travel', 'car', quantity, 'km')

                elif travel_type == 'rail':
                    quantity = distance_km or 0
                    unit = 'km'
                    co2e = quantity * 0.041  # UK rail average kgCO2e/km

                else:
                    quantity = 1
                    unit = 'trips'
                    co2e = 0
                    row_warnings.append(f"Row {row_num}: Unknown travel type '{cat_raw}' - CO2e set to 0")

                # Quality
                required = ['activity_date', 'quantity']
                if travel_type == 'flight':
                    required.append('origin')
                quality_score, quality_issues = self.score_quality(
                    {'activity_date': activity_date, 'quantity': quantity,
                     'origin': origin if travel_type == 'flight' else 'ok'},
                    required
                )
                if distance_method != 'provided' and travel_type == 'flight':
                    quality_score = max(0, quality_score - 0.15)
                    quality_issues.append("Distance estimated, not provided")

                quality_issues.extend(row_warnings)

                location = destination or origin

                records.append({
                    'category': 'scope3_travel',
                    'subcategory': travel_type,
                    'activity_date': activity_date,
                    'quantity': quantity,
                    'unit': unit,
                    'co2e_kg': co2e,
                    'location': location,
                    'supplier': supplier,
                    'cost_original': cost,
                    'currency_original': currency,
                    'cost_gbp': cost_gbp,
                    'raw_data': {
                        k: (str(v) if not pd.isna(v) else None)
                        for k, v in row.items()
                    },
                    'normalization_notes': ' | '.join(notes + [
                        f"travel_type={travel_type}",
                        f"class={svc_class}",
                        f"origin={origin}",
                        f"destination={destination}",
                        f"distance_method={distance_method}",
                    ]),
                    'quality_score': quality_score,
                    'quality_issues': quality_issues,
                    'is_suspicious': quality_score < 0.6,
                    'row_errors': [],
                })

        except Exception as e:
            errors.append(f"Fatal error: {str(e)}")

        return {
            'records': records,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_input_rows': original_rows if 'original_rows' in dir() else 0,
                'parsed_records': len(records),
            }
        }
