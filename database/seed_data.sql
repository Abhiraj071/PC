-- ScanShield Initial Seed Data

-- Default Seed Users
INSERT INTO users (id, email, password_hash, full_name, role, badge_number)
VALUES 
('usr_consumer_01', 'consumer@scanshield.gov.in', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Standard Consumer', 'CONSUMER', NULL),
('usr_inspector_01', 'inspector@scanshield.gov.in', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Inspector Rajesh Sharma', 'INSPECTOR', 'LM-INSP-2026-884'),
('usr_admin_01', 'admin@scanshield.gov.in', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'System Administrator', 'ADMIN', 'LM-ADM-001');

-- Legal Metrology Rules (Packaged Commodities Rules, 2011)
INSERT INTO rules (id, rule_code, name, category, requirement, validation_logic, severity, version, active)
VALUES
('rule_01', 'LM-NAME-001', 'Manufacturer/Packer Details', 'packaged_commodity', 'Name and complete address of manufacturer, packer, or importer must be declared', 'check_manufacturer_exists', 'high', '1.0', TRUE),
('rule_02', 'LM-GENERIC-002', 'Generic Name of Commodity', 'packaged_commodity', 'Common or generic name describing product contents must be present', 'check_generic_name_exists', 'medium', '1.0', TRUE),
('rule_03', 'LM-QTY-003', 'Net Quantity Declaration', 'packaged_commodity', 'Net quantity must be declared in standard unit of weight or measure (g, kg, ml, L, count)', 'check_net_quantity_standard', 'high', '1.0', TRUE),
('rule_04', 'LM-MRP-004', 'Maximum Retail Price (MRP)', 'packaged_commodity', 'MRP must be declared as Maximum Retail Price ... Inclusive of all taxes with currency symbol', 'check_mrp_format', 'high', '1.0', TRUE),
('rule_05', 'LM-DATE-005', 'Manufacture / Packing Date', 'packaged_commodity', 'Month and year of manufacture, packing, or import must be declared (MM/YYYY)', 'check_mfg_date_format', 'high', '1.0', TRUE),
('rule_06', 'LM-CC-006', 'Consumer Care Details', 'packaged_commodity', 'Name, address, phone number, and email for consumer care must be declared', 'check_consumer_care_exists', 'high', '1.0', TRUE),
('rule_07', 'LM-ORIGIN-007', 'Country of Origin', 'packaged_commodity', 'Country of origin must be declared for imported commodities', 'check_country_origin', 'medium', '1.0', TRUE),
('rule_08', 'LM-EXP-008', 'Best Before / Expiry Date', 'packaged_commodity', 'Best Before / Expiry date must be declared for food, cosmetics, or perishable items', 'check_expiry_date', 'high', '1.0', TRUE),
('rule_09', 'LM-USP-009', 'Unit Sale Price', 'packaged_commodity', 'Price per standard unit (₹/kg, ₹/liter, ₹/100g) must be declared where applicable', 'check_unit_sale_price', 'low', '1.0', TRUE),
('rule_10', 'LM-FONT-010', 'Font Size & Readability', 'packaged_commodity', 'Mandatory declarations must satisfy minimum font height based on PDP surface area', 'check_font_readability', 'medium', '1.0', TRUE);

-- Demo Approved Product (Lay's Classic Potato Chips)
INSERT INTO products (id, product_name, brand_name, category, manufacturer, net_quantity, mrp, mfg_date, best_before, consumer_care, fssai_license, country_of_origin, barcode)
VALUES (
    'prd_lays_classic_01',
    'Lay''s Classic Potato Chips',
    'Lay''s',
    'Snacks & Namkeen',
    'PepsiCo India Holdings Pvt. Ltd., Village Channo, Patiala - 147 105, India',
    '52 g',
    '₹ 20.00 (Inclusive of all taxes)',
    '15 Jun 2024',
    '14 Dec 2024',
    'Consumer Care: 1800 22 4020, consumercare@pepsico.com',
    '10014063000346',
    'India',
    '8901499007567'
);
