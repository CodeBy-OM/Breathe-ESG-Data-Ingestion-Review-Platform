"""
Realistic sample data generators for each source type.
These mimic real-world messy exports.
"""


def get_sample_csv(source: str) -> str:
    if source == 'sap':
        return get_sap_sample()
    elif source == 'utility':
        return get_utility_sample()
    elif source == 'travel':
        return get_travel_sample()
    return ''


def get_sap_sample() -> str:
    """
    Realistic SAP fuel/procurement CSV export.
    Note: German column headers, mixed units, weird plant codes, EUR currency
    """
    return """Buchungsdatum,Werk,Material,Bezeichnung,Menge,Mengeneinheit,Betrag,Waehrung,Lieferant,Kostenstelle
01.01.2024,DE01,DIES-001,Diesel Kraftstoff,1200,L,1560.00,EUR,BP Deutschland GmbH,4100
15.01.2024,DE01,DIES-001,Diesel Kraftstoff,980,L,1274.00,EUR,BP Deutschland GmbH,4100
20.01.2024,UK_PLANT_03,DIESEL,Diesel fuel,300,GAL,1890.00,GBP,Shell UK Ltd,5200
31.01.2024,DE02,PETR-001,Benzin / Petrol,450,L,693.00,EUR,Total Energies,4200
05.02.2024,DE01,DIES-001,Diesel Kraftstoff,1100,L,1430.00,EUR,BP Deutschland GmbH,4100
10.02.2024,PLANT-GB01,DIESEL,Diesel fuel,0,,800.00,GBP,Shell UK Ltd,5200
14.02.2024,DE01,DIES-001,Diesel Kraftstoff,-200,L,-260.00,EUR,BP Deutschland GmbH,4100
28.02.2024,UK_PLANT_03,PETROL,Petrol / unleaded,180,GAL,1134.00,GBP,Shell UK Ltd,5200
01.03.2024,DE03,LPG-001,Fluessiggas LPG,800,L,640.00,EUR,Linde Gas AG,4300
15.03.2024,DE01,CHEM-001,Reinigungsmittel,50,KG,375.00,EUR,BASF SE,7100
20.03.2024,UK_PLANT_03,DIES-001,Diesel fuel,950,L,1235.00,GBP,Shell UK Ltd,5200
25.03.2024,DE01,DIES-001,Diesel Kraftstoff,99999,L,129999.00,EUR,Unknown Vendor,4100
31.03.2024,DE02,PACK-001,Verpackungsmaterial,200,KG,800.00,EUR,Smurfit Kappa,7200
05.04.2024,DE01,DIES-001,Diesel Kraftstoff,1050,L,1365.00,EUR,BP Deutschland GmbH,4100
10.04.2024,UK_PLANT_03,DIESEL,Diesel fuel,420,L,546.00,GBP,Shell UK Ltd,5200
"""


def get_utility_sample() -> str:
    """
    Realistic UK utility/electricity CSV export.
    Note: Multiple meters, estimated reads, mixed billing periods
    """
    return """Site,MPAN,Period Start,Period End,Consumption (kWh),Read Type,Unit Rate (p/kWh),Standing Charge (p/day),Total Cost (GBP),Tariff
London HQ,1200051234567,01/01/2024,31/01/2024,45230,Actual,28.5,45.2,13047.90,Business Smart Flex
London HQ,1200051234567,01/02/2024,29/02/2024,42100,Actual,28.5,45.2,12161.25,Business Smart Flex
Manchester Office,1300087654321,01/01/2024,31/01/2024,18650,Estimated,27.8,38.5,5253.95,Fixed Rate Business
Manchester Office,1300087654321,01/02/2024,29/02/2024,19200,Actual,27.8,38.5,5404.60,Fixed Rate Business
Birmingham Warehouse,1400099887766,01/01/2024,31/01/2024,67800,Actual,26.9,52.0,18372.80,HalfHourly Flex
Birmingham Warehouse,1400099887766,01/02/2024,29/02/2024,71200,Actual,26.9,52.0,19280.80,HalfHourly Flex
Edinburgh Branch,1500044332211,01/01/2024,31/01/2024,8900,Actual,29.1,42.0,2621.40,SME Fixed
Edinburgh Branch,1500044332211,01/02/2024,29/02/2024,0,Estimated,29.1,42.0,0.00,SME Fixed
Bristol Depot,1600055443322,01/01/2024,31/01/2024,23400,Actual,27.5,40.0,6493.00,Variable Business
Bristol Depot,1600055443322,01/02/2024,29/02/2024,24100,Actual,27.5,40.0,6680.00,Variable Business
Leeds Factory,1700066554433,01/01/2024,31/01/2024,95000,Actual,25.8,65.0,24771.50,Industrial Flex
Leeds Factory,1700066554433,01/02/2024,29/02/2024,98200,Actual,25.8,65.0,25597.60,Industrial Flex
"""


def get_travel_sample() -> str:
    """
    Realistic Concur/Navan corporate travel export.
    Note: Airport codes, missing distances, multiple currencies, hotel stays
    """
    return """Transaction Date,Category,Origin,Destination,Distance (km),Class,Supplier,Nights,Amount,Currency,Traveler,Department
2024-01-08,Flight,LHR,JFK,,Economy,British Airways,0,850.00,GBP,Sarah Johnson,Sales
2024-01-08,Hotel,,New York,,,,3,420.00,USD,Sarah Johnson,Sales
2024-01-10,Flight,JFK,LHR,,Economy,British Airways,0,920.00,GBP,Sarah Johnson,Sales
2024-01-15,Flight,LHR,CDG,,Business Class,Air France,0,1200.00,GBP,Marcus Chen,Executive
2024-01-15,Hotel,,Paris,,,,2,380.00,EUR,Marcus Chen,Executive
2024-01-17,Flight,CDG,LHR,,Business Class,Air France,0,1100.00,GBP,Marcus Chen,Executive
2024-01-22,Taxi,,,45,,Uber,0,85.00,GBP,James Wilson,IT
2024-01-25,Flight,MAN,LHR,,Economy,EasyJet,0,120.00,GBP,Lisa Park,Finance
2024-01-25,Train,LHR,MAN,,Standard,LNER,0,95.00,GBP,Lisa Park,Finance
2024-02-05,Flight,LHR,DXB,,Economy,Emirates,0,680.00,GBP,Ahmed Hassan,Operations
2024-02-05,Hotel,,Dubai,,,,4,720.00,USD,Ahmed Hassan,Operations
2024-02-09,Flight,DXB,LHR,,Economy,Emirates,0,650.00,GBP,Ahmed Hassan,Operations
2024-02-12,Flight,LHR,BOM,,Economy,British Airways,0,750.00,GBP,Priya Sharma,Technology
2024-02-14,Hotel,,Mumbai,,,,5,450.00,INR,Priya Sharma,Technology
2024-02-19,Flight,BOM,LHR,,Economy,British Airways,0,780.00,GBP,Priya Sharma,Technology
2024-02-20,Taxi,,,20,,Addison Lee,0,45.00,GBP,Tom Roberts,HR
2024-02-25,Flight,LHR,SIN,,Business Class,Singapore Airlines,0,3200.00,GBP,CEO Office,Executive
2024-03-01,Flight,LHR,FRA,,Economy,Lufthansa,0,280.00,GBP,Anna Mueller,Finance
2024-03-02,Hotel,,Frankfurt,,,,1,195.00,EUR,Anna Mueller,Finance
2024-03-03,Flight,FRA,LHR,,Economy,Lufthansa,0,310.00,GBP,Anna Mueller,Finance
"""
