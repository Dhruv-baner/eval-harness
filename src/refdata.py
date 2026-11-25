# -*- coding: utf-8 -*-
"""Reference data for the synthetic accounting-firm dataset."""

# Standard chart of accounts: code -> list of synonyms (first = standard name)
SYN = {
 '1000': ['Cash - Operating', 'Checking', 'Bank - Operating Account', 'Operating Checking', 'Cash at Bank'],
 '1010': ['Cash - Savings', 'Savings', 'Money Market', 'Reserve Account'],
 '1020': ['Petty Cash', 'Cash on Hand', 'Till Float'],
 '1100': ['Accounts Receivable', 'Trade Debtors', 'A/R', 'Receivables', 'Debtors Control'],
 '1110': ['Allowance for Doubtful Accounts', 'Bad Debt Provision', 'Reserve for Bad Debts'],
 '1200': ['Inventory', 'Stock', 'Merchandise Inventory', 'Inventory Asset'],
 '1300': ['Prepaid Expenses', 'Prepayments', 'Prepaid Insurance & Other'],
 '1400': ['Other Current Assets', 'Other Receivables', 'Undeposited Funds'],
 '1500': ['Fixed Assets - Equipment', 'Equipment', 'Furniture & Equipment', 'Plant & Machinery', 'Property, Plant & Equipment'],
 '1590': ['Accumulated Depreciation', 'Less: Accum. Depreciation', 'Provision for Depreciation', 'Accum Depr - Equipment'],
 '1600': ['Intangible Assets', 'Software Development Costs', 'Goodwill & Intangibles'],
 '1700': ['Security Deposits', 'Deposits Paid', 'Rent Deposit'],
 '2000': ['Accounts Payable', 'Trade Creditors', 'A/P', 'Payables', 'Creditors Control'],
 '2100': ['Credit Card Payable', 'Company Credit Card', 'Amex Business', 'Corporate Card'],
 '2200': ['Accrued Expenses', 'Accruals', 'Accrued Liabilities'],
 '2210': ['Accrued Payroll', 'Wages Payable', 'Salaries Payable'],
 '2300': ['Sales Tax / VAT Payable', 'Sales Tax Payable', 'VAT Control', 'Sales Tax Liability', 'VAT Payable'],
 '2310': ['Payroll Taxes Payable', 'Payroll Tax Payable', 'PAYE & NI Liability', 'Payroll Liabilities'],
 '2400': ['Deferred Revenue', 'Unearned Revenue', 'Customer Deposits', 'Contract Liabilities'],
 '2500': ['Short-Term Loan', 'Line of Credit', 'Bank Overdraft Facility', 'Revolving Credit'],
 '2600': ['Long-Term Debt', 'Term Loan', 'Bank Loan', 'Notes Payable - Long Term', 'Mortgage Payable'],
 '3000': ["Owner's Capital", 'Common Stock', 'Share Capital', 'Members Capital', 'Paid-in Capital'],
 '3100': ['Retained Earnings', 'Accumulated Profits', 'Profit & Loss Account'],
 '3200': ["Owner's Draws / Distributions", "Owner's Draws", 'Distributions', 'Dividends Paid', 'Member Distributions'],
 '4000': ['Product Sales', 'Sales - Products', 'Sales', 'Merchandise Sales', 'Online Sales'],
 '4100': ['Service Revenue', 'Fees Earned', 'Professional Fees Income', 'Patient Services', 'Sales - Services'],
 '4150': ['Rental Income', 'Rent Received', 'Rents - Residential'],
 '4200': ['Subscription Revenue', 'Recurring Revenue', 'SaaS Revenue', 'Subscriptions'],
 '4300': ['Other Income', 'Miscellaneous Income', 'Sundry Income'],
 '4400': ['Interest Income', 'Bank Interest Received', 'Interest Earned'],
 '4900': ['Sales Returns & Discounts', 'Sales Returns & Allowances', 'Discounts Given', 'Refunds & Discounts', 'Contractual Adjustments'],
 '5000': ['Cost of Goods Sold', 'Cost of Sales', 'COGS', 'Purchases', 'Materials Cost'],
 '5100': ['Direct Labor', 'Direct Wages', 'Production Labour', 'Cost of Labor'],
 '5200': ['Freight & Shipping', 'Carriage Inwards', 'Freight-In', 'Shipping & Delivery Costs'],
 '5300': ['Subcontractors', 'Direct Costs - Subcontract', 'Contract Labor', 'Outsourced Services', 'Lab Fees'],
 '6000': ['Salaries & Wages', 'Wages & Salaries', 'Payroll Expenses', 'Staff Costs', 'Employee Compensation'],
 '6010': ['Payroll Taxes', 'Employer NI', 'Employer Payroll Taxes', 'Social Security Contributions'],
 '6020': ['Employee Benefits', 'Staff Benefits', 'Health Insurance', 'Pension Contributions'],
 '6100': ['Rent', 'Rent & Lease', 'Rent Expense', 'Office Rent', 'Premises Costs'],
 '6110': ['Utilities', 'Electric & Gas', 'Light, Heat & Power', 'Utilities Expense'],
 '6120': ['Telephone & Internet', 'Telecoms', 'Phone & Broadband', 'Communications'],
 '6130': ['Property Taxes', 'Council Tax & Rates', 'Real Estate Taxes'],
 '6140': ['Property Management Fees', 'Management Fees', 'Letting Agent Fees'],
 '6200': ['Office Supplies', 'Office Expenses', 'Stationery & Supplies', 'Office Supplies & Postage'],
 '6210': ['Software & Subscriptions', 'Software Subscriptions', 'Computer Software', 'IT & Software'],
 '6300': ['Legal Fees', 'Legal & Professional', 'Professional Fees - Legal', 'Solicitors Fees'],
 '6310': ['Accounting Fees', 'Accountancy', 'Bookkeeping & Accounting', 'Professional Fees - Accounting', 'Audit & Accountancy'],
 '6400': ['Advertising & Marketing', 'Marketing', 'Advertising & Promotion', 'Promotions', 'Sales & Marketing'],
 '6410': ['Travel', 'Travel Expenses', 'Travel & Accommodation', 'Business Travel'],
 '6420': ['Meals & Entertainment', 'Entertainment', 'Staff Meals', 'Client Entertaining'],
 '6500': ['Insurance', 'Insurance Expense', 'Business Insurance', 'Insurance - General'],
 '6600': ['Repairs & Maintenance', 'Repairs & Renewals', 'Maintenance', 'Building Repairs'],
 '6610': ['Vehicle & Fuel Expenses', 'Fuel & Vehicle Costs', 'Motor Expenses', 'Auto & Truck Expense'],
 '6700': ['Depreciation Expense', 'Depreciation', 'Depreciation & Amortization'],
 '6800': ['Bank Charges', 'Bank Fees & Charges', 'Bank Service Charges'],
 '6810': ['Merchant Processing Fees', 'Merchant Fees', 'Credit Card Processing Fees', 'Payment Processing Fees', 'Stripe Fees'],
 '6900': ['Bad Debt Expense', 'Bad Debts Written Off', 'Doubtful Debts'],
 '6950': ['Dues & Licenses', 'Licenses & Permits', 'Memberships & Subscriptions', 'Subs & Licences'],
 '6990': ['Miscellaneous Expense', 'General Expenses', 'Sundry Expenses', 'Other Expenses'],
 '7000': ['Interest Expense', 'Loan Interest', 'Finance Charges', 'Interest Paid'],
 '7100': ['Foreign Exchange Gain/Loss', 'Realised Currency Gains/Losses', 'Exchange Differences'],
 '7900': ['Income Tax Expense', 'Corporation Tax', 'Provision for Taxes'],
}

HIGH = {'1000','1010','1100','1200','2000','2100','2300','2310','2400','2500','2600','3000','3100','3200',
        '4000','4100','4150','4200','5000','6000','7900'}
LOW = {'1020','6200','6800','6990','6950','6420','6120','1700','6410','4300'}

def coa_rows():
    rows = []
    for code, syn in SYN.items():
        c = int(code)
        cls = ('Asset' if c < 2000 else 'Liability' if c < 3000 else 'Equity' if c < 4000 else
               'Revenue' if c < 5000 else 'COGS' if c < 6000 else 'Operating Expense' if c < 7000 else 'Other')
        normal = 'Credit' if cls in ('Liability', 'Equity', 'Revenue') else 'Debit'
        if code in ('1110', '1590', '4900') and code != '4900':
            normal = 'Credit'
        if code == '3200' or code == '4900':
            normal = 'Debit'
        tier = 'High' if code in HIGH else 'Low' if code in LOW else 'Medium'
        w = {'High': 3, 'Medium': 2, 'Low': 1}[tier]
        rows.append([code, syn[0], cls, normal, tier, w])
    return rows

# German labels (partial: some codes deliberately left in English at the client)
DE = {
 '1000': 'Bank', '1010': 'Tagesgeldkonto', '1020': 'Kasse', '1100': 'Forderungen aus Lieferungen und Leistungen',
 '1300': 'Aktive Rechnungsabgrenzung', '1500': 'Fuhrpark und Betriebsausstattung', '1590': 'Kumulierte Abschreibungen',
 '2000': 'Verbindlichkeiten aus Lieferungen und Leistungen', '2100': 'Kreditkartenabrechnung',
 '2200': 'Sonstige Rückstellungen', '2210': 'Lohn- und Gehaltsverbindlichkeiten', '2300': 'Umsatzsteuer',
 '2310': 'Verbindlichkeiten Lohnsteuer und Sozialversicherung', '2600': 'Darlehen langfristig',
 '3000': 'Gezeichnetes Kapital', '3100': 'Gewinnvortrag', '3200': 'Privatentnahmen',
 '4100': 'Frachterlöse', '4300': 'Sonstige betriebliche Erträge', '4400': 'Zinserträge', '4900': 'Erlösschmälerungen',
 '5100': 'Fahrerlöhne', '5200': 'Maut und Frachtkosten', '5300': 'Fremdleistungen Subunternehmer',
 '6000': 'Löhne und Gehälter', '6010': 'Soziale Abgaben', '6100': 'Miete und Pacht', '6110': 'Strom, Gas, Wasser',
 '6120': 'Telefon und Internet', '6200': 'Bürobedarf', '6300': 'Rechtsberatungskosten', '6310': 'Steuerberatungskosten',
 '6400': 'Werbekosten', '6410': 'Reisekosten', '6420': 'Bewirtungskosten', '6500': 'Versicherungen',
 '6600': 'Reparaturen und Instandhaltung', '6610': 'Kfz-Kosten und Kraftstoff', '6700': 'Abschreibungen auf Sachanlagen',
 '6800': 'Nebenkosten des Geldverkehrs', '6990': 'Sonstige betriebliche Aufwendungen', '7000': 'Zinsaufwendungen',
}

# Fake SKR-style account numbering for the German client (others fall back to code*10+3)
SKR = {'1000': '1200', '1010': '1210', '1020': '1000', '1100': '1400', '1500': '0320', '1590': '0329',
       '2000': '1600', '2100': '1700', '2300': '1776', '2310': '1740', '2600': '0630', '3000': '0800',
       '3100': '0860', '3200': '1800', '4100': '8400', '4400': '2650', '5100': '4100', '5200': '3100',
       '5300': '3100', '6000': '4120', '6100': '4210', '6500': '4360', '6610': '4530', '6700': '4830'}

UNCAT_LABELS = ['Uncategorized Expense', 'Ask My Accountant', 'Suspense', 'Unallocated Expense', 'Uncategorised']
ABBREV = [('Expenses', 'Exp.'), ('Expense', 'Exp.'), ('&', 'and'), (' and ', ' & '), ('Maintenance', 'Maint.'),
          ('Professional', 'Prof.'), ('Equipment', 'Equip.'), ('Subscriptions', 'Subs'), ('Telephone', 'Tel.'),
          ('Advertising', 'Advert.'), ('Insurance', 'Ins.'), ('Accounts', 'Acc.'), ('Receivable', 'Rec.')]

# Vendor pools by category and region (US fallback)
def _v(us, uk=None, de=None):
    return {'US': us, 'UK': uk or us, 'DE': de or us}

VEND = {
 'dental_supply': _v(['Henry Schein', 'Patterson Dental', 'Benco Dental', 'Darby Dental', 'Dentsply Sirona']),
 'lab': _v(['Glidewell Laboratories', 'Bay Dental Lab', 'Precision Ceramics Lab', 'NDX Nobilium', 'Smile Arts Lab']),
 'office': _v(['Staples', 'Office Depot', 'Amazon Business', 'Costco Business', 'Uline'],
              ['Staples UK', 'Viking Direct', 'Amazon Business', 'Ryman'],
              ['Büro Schäfer', 'Amazon Business DE', 'Staples DE', 'Viking Direct DE']),
 'software': _v(['Microsoft 365', 'Google Workspace', 'Zoom', 'Adobe', 'Dropbox', 'Slack', 'Intuit QuickBooks', 'Salesforce', 'Atlassian', 'GitHub', 'Notion']),
 'telecom': _v(['Verizon Business', 'AT&T', 'Comcast Business', 'Spectrum Business', 'T-Mobile'],
               ['BT Business', 'Vodafone UK', 'O2 Business', 'Virgin Media Business', 'Sky Business'],
               ['Deutsche Telekom', 'Vodafone GmbH', 'O2 Telefónica', '1&1 Versatel']),
 'utility': _v(['PG&E', 'Con Edison', 'Duke Energy', 'National Grid', 'Waste Management', 'City Water Dept'],
               ['British Gas Business', 'Octopus Energy', 'Thames Water', 'Veolia', 'E.ON Next'],
               ['E.ON Energie', 'Stadtwerke Hamburg', 'Vattenfall', 'RWE Energie']),
 'insurance': _v(['The Hartford', 'Travelers', 'Chubb', 'State Farm Business', 'Liberty Mutual', 'Hiscox'],
                 ['Aviva', 'Hiscox UK', 'AXA UK', 'Zurich UK'], ['Allianz', 'HUK-Coburg', 'AXA Versicherung', 'Gothaer']),
 'legal': _v(['Baker & Lowell LLP', 'Meridian Legal Group', 'Okafor Law PC', 'Hale Pruitt LLP'],
             ['Harcourt & Pryce Solicitors', 'Mason Rowe LLP'], ['Kanzlei Brandt & Voss', 'Rechtsanwälte Lindner']),
 'accounting': _v(['Whitmore & Cho CPAs', 'Brightstone Advisory', 'Lakeview CPA Group'],
                  ['Hartley Moss Accountants', 'Penrose & Co'], ['Steuerberatung Hoffmann', 'Wagner & Partner StB']),
 'marketing': _v(['Google Ads', 'Meta Ads', 'Yelp Ads', 'Mailchimp', 'Canva', 'Vistaprint', 'LinkedIn Ads', 'Local Mag Media'],
                 ['Google Ads', 'Meta Ads', 'Klaviyo', 'Mailchimp', 'Instagram Ads', 'Canva'],
                 ['Google Ads', 'LinkedIn Ads', 'XING Werbung', 'Messebau Nord']),
 'travel': _v(['Delta Air Lines', 'United Airlines', 'Marriott', 'Hilton', 'Uber', 'Lyft', 'Hertz', 'Southwest Airlines', 'Expedia'],
              ['Trainline', 'Premier Inn', 'British Airways', 'easyJet', 'Uber UK'],
              ['Deutsche Bahn', 'Lufthansa', 'Ibis Hotels', 'Sixt']),
 'meals': _v(['Chipotle', 'Starbucks', 'Panera Bread', 'Olive Garden', 'Local Bistro', 'DoorDash', 'Grubhub', "Joe's Pizza"],
             ['Pret A Manger', 'Greggs', 'Costa Coffee', 'Wagamama', 'Deliveroo'],
             ['Bäckerei Kamps', 'Subway', 'Lieferando', 'Café Extrablatt']),
 'repairs': _v(['Home Depot', "Lowe's", 'ServiceMaster', 'ABC Plumbing', 'Allied HVAC', 'Metro Electric', 'Handy Hands Maintenance'],
               ['Screwfix', 'Toolstation', 'Checkatrade Plumber', 'Kwik Fit'],
               ['ATU Autoteile', 'Bosch Car Service', 'Würth', 'Hornbach']),
 'bank': _v(['Chase Business', 'Wells Fargo', 'Bank of America', 'Mercury', 'Silicon Valley Bank'],
            ['Barclays Business', 'HSBC UK', 'Lloyds Bank', 'Starling Business', 'Tide'],
            ['Deutsche Bank', 'Commerzbank', 'Sparkasse Hamburg', 'N26 Business']),
 'freight': _v(['FedEx', 'UPS', 'USPS', 'DHL', 'XPO Logistics'], ['Royal Mail', 'DPD UK', 'Evri', 'Parcelforce', 'DHL Express UK'],
               ['DHL', 'DPD', 'Hermes', 'GLS']),
 'materials': _v(['84 Lumber', 'Ferguson Supply', 'Graybar Electric', 'Cemex', 'Home Depot Pro', 'Sherwin-Williams', 'Builders FirstSource']),
 'subcontract': _v(['Apex Electric', 'Ridgeline Plumbing', 'Summit Concrete', 'Pinnacle Drywall', 'Evergreen Landscaping',
                    'Coastal Roofing', 'Keystone Steel Erectors', 'Delta Excavating'],
                   None, ['Spedition Ahrens', 'Transport Peters', 'Fahrdienst Nordost', 'Kurier Express Müller', 'Frachtkontor Lübeck']),
 'fuel': _v(['Shell', 'Chevron', 'BP', 'Exxon', 'Sunoco', 'Pilot Flying J', 'Wawa'], ['Shell UK', 'BP', 'Esso', 'Tesco Fuel'],
            ['Aral', 'Shell Deutschland', 'Total', 'Jet Tankstelle', 'DKV Card']),
 'food': _v(['Sysco', 'US Foods', 'Restaurant Depot', 'Performance Food Group', 'Local Produce Co-op', 'Fresh Direct Wholesale']),
 'beverage': _v(["Southern Glazer's", 'Republic National', 'Coca-Cola Beverages', 'Local Brewery Distribution']),
 'rent': _v(['Landmark Properties', 'Westfield Realty', 'Parkside Management'], ['Grosvenor Estates', 'Landsec Lettings'],
            ['Hanse Immobilien', 'Nordlicht Gewerbe']),
 'research': _v(['Westlaw', 'LexisNexis', 'PACER', 'Bloomberg Law']),
 'cloud': _v(['AWS', 'Google Cloud', 'Microsoft Azure', 'Datadog', 'Snowflake', 'Twilio', 'Cloudflare', 'MongoDB Atlas']),
 'packaging': _v(['Uline', 'Packhelp', 'Noissue', 'EcoEnclose'], ['Packhelp UK', 'Noissue', 'Raja Pack', 'EcoEnclose']),
 'wholesale': _v(['Green Valley Growers Co-op', 'Harvest Moon Suppliers', 'Wildflower Organics', 'Fenland Farms',
                  "Nature's Pantry Wholesale", 'Pure Pantry Imports']),
 'toll': _v(['E-ZPass', 'SunPass'], None, ['Toll Collect']),
 'repairs_prop': _v(['ABC Plumbing', 'Allied HVAC', 'Metro Electric', 'Handy Hands Maintenance', 'Home Depot', 'Sparkle Cleaning Co']),
 'propmgmt': _v(['Cornerstone Property Mgmt']),
 'payers': _v(['Delta Dental', 'Aetna Dental', 'Cigna Dental', 'MetLife Dental', 'Guardian Dental', 'United Concordia', 'BCBS Dental', 'Humana Dental']),
}

CITIES = {'US': ['AUSTIN TX', 'DENVER CO', 'CHICAGO IL', 'SEATTLE WA', 'BOSTON MA', 'MIAMI FL', 'PORTLAND OR'],
          'UK': ['LONDON', 'MANCHESTER', 'BRISTOL', 'LEEDS', 'EDINBURGH'],
          'DE': ['HAMBURG', 'BERLIN', 'KIEL', 'BREMEN', 'LUEBECK']}

ADJ = ['Northern', 'Summit', 'Blue', 'Pioneer', 'Atlas', 'Evergreen', 'Harbor', 'Iron', 'Crescent', 'Redwood', 'Keystone',
       'Lakeside', 'Beacon', 'Falcon', 'Granite', 'Sterling', 'Meridian', 'Orchard', 'Cobalt', 'Juniper']
NOUN = ['Logistics', 'Holdings', 'Partners', 'Builders', 'Foods', 'Systems', 'Industries', 'Realty', 'Medical', 'Energy',
        'Capital', 'Labs', 'Group', 'Supply', 'Developments', 'Trading', 'Solutions', 'Networks']
SUF = {'US': ['LLC', 'Inc', 'Corp', 'Co', 'LLP'], 'UK': ['Ltd', 'PLC', 'LLP', 'Limited'], 'DE': ['GmbH', 'AG', 'KG', 'GmbH & Co. KG']}
FIRST = ['James', 'Maria', 'Chen', 'Aisha', 'Tomas', 'Priya', 'Liam', 'Sofia', 'Omar', 'Hannah', 'Diego', 'Yuki', 'Grace', 'Ivan']
LAST = ['Patel', 'Nguyen', 'Garcia', 'Okafor', 'Kowalski', 'Silva', 'Murphy', 'Rossi', 'Haddad', 'Larsen', 'Brooks', 'Tanaka', 'Weber', 'Lindqvist']

# Hand-typed cash-book categories (Sunrise Property)
CB_LABELS = {
 '4150': ['Rent', 'Rent received', 'Rental income', 'rent', 'RENT', 'Rent - unit'],
 '4300': ['Late fee', 'Late fees', 'Other income', 'Misc income', 'Pet fee / late'],
 '6600': ['Repairs', 'R&M', 'repairs & maint', 'Repair + maintenance', 'Maintenance - unit', 'Repairs/Maint.'],
 '6110': ['Utilities', 'Water/sewer', 'Elec', 'Gas & electric', 'utilities - common'],
 '6500': ['Insurance', 'Landlord insurance', 'Ins premium', 'Property insurance'],
 '6130': ['Property tax', 'Prop tax', 'Real estate tax', 'Taxes - county'],
 '6140': ['Management fee', 'Mgmt fee', 'PM fee', 'Property mgmt'],
 '6310': ['Accounting', 'Tax prep', 'CPA fee', 'Accountant'],
 '6800': ['Bank charges', 'Bank fee', 'bank'],
 '2600': ['Mortgage principal', 'Mortgage - capital', 'Mtge principal', 'Loan principal'],
 '7000': ['Mortgage interest', 'Mtge int', 'Interest', 'Loan interest'],
 '6990': ['Misc', 'Other', 'Sundry', 'Misc expense'],
 '1500': ['Capex - appliances', 'New water heater', 'Capital improvement', 'Appliance purchase'],
 '6200': ['Supplies', 'Office', 'Postage & supplies'],
 '6000': ['Maintenance wages', 'Handyman wages', 'Caretaker'],
}
