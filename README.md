# Breathe ESG — Data Ingestion & Review Platform

A prototype ESG data platform for collecting, normalising, reviewing, and audit-locking emissions data from three real-world business systems.

---
# Live Link - https://breathe-esg-data-ingestion-review-p.vercel.app/
---
## Quick Start

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend (separate terminal)
cd frontend
npm install
npm start
```

---

## What's Built

### Three data source normalizers

| Source | Real-world format modelled | Key challenges handled |
|--------|---------------------------|------------------------|
| **SAP** | SAP CSV flat file export | German column headers, mixed L/GAL units, plant codes (DE01, UK_PLANT_03), material codes (DIES-001), EUR/GBP currencies, negative reversal entries, YYYYMM period fields |
| **Utility / Electricity** | UK utility portal CSV (Octopus, British Gas style) | MPAN meter IDs, estimated vs actual reads, kWh/MWh/GJ unit detection from column headers, billing periods, multi-site |
| **Corporate Travel** | Concur/Navan expense export | IATA airport codes, haversine distance estimation when distance missing, business vs economy class CO₂ factor, hotel nights, multi-currency FX |

### Backend (Django + DRF)

```
backend/
├── breathe_esg/         Django project settings, URLs
├── core/                Tenant model, middleware
│   ├── models.py        Tenant, TenantUser
│   └── middleware.py    X-Tenant-Slug header → request.tenant
├── ingestion/
│   ├── models.py        DataImport, NormalizedRecord
│   ├── views.py         Upload, approve, reject, bulk actions
│   ├── serializers.py
│   ├── sample_data.py   Realistic messy CSVs for demo
│   └── normalizers/
│       ├── base.py      Unit maps, date parsing, CO₂e calc, quality scoring
│       ├── sap_normalizer.py
│       ├── utility_normalizer.py
│       └── travel_normalizer.py
└── audit/               AuditTrail model, read-only view
```

### Frontend (React)

```
frontend/src/
├── App.js               Navigation shell, stats refresh
├── api.js               Axios client with tenant header
└── pages/
    ├── Dashboard.js     Stats cards, bar/pie charts, recent imports
    ├── ImportPage.js    Source selector, file drop zone, sample loader
    ├── ReviewPage.js    Filterable table, modal detail, bulk approve
    └── AuditPage.js     Lock workflow, emissions summary table
```

## Data Modelling Decisions

### NormalizedRecord — the canonical record

Every record from every source normalises into the same shape:

```python
category        # scope1_fuel | scope2_electricity | scope3_travel | scope3_procurement
subcategory     # diesel | electricity | flight | hotel | car | ...
activity_date   # Python date — always resolved even from SAP period fields
quantity        # float in canonical unit
unit            # liters | kwh | km | nights
co2e_kg         # calculated at ingest time using DEFRA emission factors
quality_score   # 0–1, computed from field completeness + value sanity
quality_issues  # JSON list of human-readable issue strings
is_suspicious   # bool — score < 0.6 or has row errors
review_status   # pending | approved | rejected | flagged
is_locked       # bool — immutable once locked for audit
raw_data        # JSON snapshot of original row (for traceability)
normalization_notes  # what was changed: "Unit normalized: GAL → liters"
```

**Why this shape?** GHG Protocol requires Scope 1/2/3 separation. Normalising at ingest means the analyst sees clean data, not raw source rows. The `raw_data` JSON preserves the full paper trail for auditors who need to verify.

### Multi-tenancy

Each request carries `X-Tenant-Slug: breathe-demo` (or similar) in the HTTP header. The `TenantMiddleware` resolves this to a `Tenant` object attached to `request.tenant`. Every queryset filters on `tenant=request.tenant` — complete data isolation between companies.

### Quality scoring

The `score_quality()` method in `base.py` deducts points for:
- Missing required fields (proportional deduction)
- Negative quantities (possible reversal entries)
- Zero quantities (likely missing data)
- Estimated meter reads (utility)
- Flight distance estimated rather than provided

Records with score < 0.6 are automatically set to `review_status='flagged'` and `is_suspicious=True`.

### CO₂e calculation

Uses DEFRA 2023 emission factors at ingest time:

| Activity | Factor |
|----------|--------|
| Diesel | 2.68 kgCO₂e/litre |
| Petrol | 2.31 kgCO₂e/litre |
| UK electricity | 0.233 kgCO₂e/kWh |
| Flight economy | 0.255 kgCO₂e/passenger-km |
| Flight business | 0.510 kgCO₂e/passenger-km (2× economy) |
| Hotel stay | 31.0 kgCO₂e/night |
| Car/taxi | 0.171 kgCO₂e/km |

### Travel distance estimation

When flight distance is missing (common in Concur exports), the normalizer uses a haversine calculation from a built-in IATA airport coordinate lookup (50+ airports) with a 5% path-deviation premium. The method is recorded in `normalization_notes` and the quality score is reduced by 0.15.

---

## Real-World Messiness Handled

### SAP CSV
- **German headers**: `Buchungsdatum` → `posting_date`, `Menge` → `quantity`, `Werk` → `plant`, etc.
- **Mixed encodings**: tries utf-8, latin-1, windows-1252 (SAP exports vary by locale)
- **Period fields**: `202403` → inferred as `2024-03-01`
- **Negative entries**: Flagged as suspicious (likely cancellation/reversal)
- **Unknown material codes**: Logged in notes, categorised as procurement
- **Unit inconsistency**: Some plants report in GAL, others in L

### Utility CSV
- **Estimated reads**: Flagged, quality score reduced, analyst notified
- **Unit in column header**: `Consumption (kWh)` parsed to detect kWh vs MWh
- **Zero consumption**: Flagged — likely a missing read, not a real zero
- **MPAN/meter IDs**: Preserved in normalization_notes for traceability

### Travel CSV
- **Missing distances**: Calculated via haversine from IATA codes
- **Multi-currency**: USD, EUR, INR, SGD → approximate GBP conversion
- **Missing traveler name**: Allowed, not flagged
- **Unknown categories**: Set to `other` with CO₂e = 0 and warning
