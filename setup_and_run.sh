#!/usr/bin/env bash
# ============================================================
#  Breathe ESG — Quick Setup & Run Script
#  Usage: ./setup_and_run.sh
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}==> Breathe ESG Platform Setup${NC}"
echo ""

# ── Backend ──────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Setting up Python virtual environment...${NC}"
cd backend
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}[2/5] Installing Python dependencies...${NC}"
pip install -r requirements.txt -q

echo -e "${YELLOW}[3/5] Running Django migrations...${NC}"
python manage.py migrate --run-syncdb

echo -e "${YELLOW}[4/5] Seeding demo tenant...${NC}"
python manage.py shell -c "
from core.models import Tenant
Tenant.objects.get_or_create(slug='breathe-demo', defaults={'name':'Breathe ESG Demo','country':'GB'})
Tenant.objects.get_or_create(slug='acme-corp', defaults={'name':'ACME Corporation','country':'US'})
print('Tenants ready.')
"

echo -e "${GREEN}[✓] Backend ready.${NC}"
echo ""
echo -e "${YELLOW}Starting Django on http://localhost:8000 ...${NC}"
python manage.py runserver 8000 &
DJANGO_PID=$!
cd ..

# ── Frontend ─────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/5] Installing frontend dependencies...${NC}"
cd frontend
npm install --silent

echo -e "${GREEN}[✓] Frontend ready.${NC}"
echo ""
echo -e "${YELLOW}Starting React on http://localhost:3000 ...${NC}"
BROWSER=none npm start &
REACT_PID=$!
cd ..

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Breathe ESG is running!${NC}"
echo -e "${GREEN}  Frontend:  http://localhost:3000${NC}"
echo -e "${GREEN}  API:       http://localhost:8000/api/${NC}"
echo -e "${GREEN}  Admin:     http://localhost:8000/admin/${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Press Ctrl+C to stop both servers."
wait $DJANGO_PID $REACT_PID
