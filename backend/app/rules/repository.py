from typing import List, Dict, Any, Optional

LEGAL_METROLOGY_RULES = [
    {
        "id": "rule_01",
        "rule_code": "LM-NAME-001",
        "name": "Manufacturer / Packer / Importer Details",
        "category": "packaged_commodity",
        "requirement": "Name and complete postal address of the manufacturer, packer, or importer must be clearly declared.",
        "validation_logic": "check_manufacturer_exists",
        "severity": "high",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_02",
        "rule_code": "LM-GENERIC-002",
        "name": "Generic Name of Commodity",
        "category": "packaged_commodity",
        "requirement": "Common or generic name describing the contents of the packaged commodity must be declared.",
        "validation_logic": "check_generic_name_exists",
        "severity": "medium",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_03",
        "rule_code": "LM-QTY-003",
        "name": "Net Quantity Declaration",
        "category": "packaged_commodity",
        "requirement": "Net quantity must be declared in standard units of weight, volume, or count (g, kg, ml, L, count).",
        "validation_logic": "check_net_quantity_standard",
        "severity": "high",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_04",
        "rule_code": "LM-MRP-004",
        "name": "Maximum Retail Price (MRP)",
        "category": "packaged_commodity",
        "requirement": "MRP must be declared in format 'Maximum Retail Price ... Inclusive of all taxes' or 'MRP ... Inclusive of all taxes' with currency symbol (₹, Rs., or INR) up to two decimal places.",
        "validation_logic": "check_mrp_format",
        "severity": "high",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_05",
        "rule_code": "LM-DATE-005",
        "name": "Month and Year of Manufacture / Packing",
        "category": "packaged_commodity",
        "requirement": "Month and year of manufacture, packing, or import must be declared (MM/YYYY or Month Year).",
        "validation_logic": "check_mfg_date_format",
        "severity": "high",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_06",
        "rule_code": "LM-CC-006",
        "name": "Consumer Care Details",
        "category": "packaged_commodity",
        "requirement": "Name, address, telephone number, and e-mail address of the person/office for consumer grievances must be declared.",
        "validation_logic": "check_consumer_care_exists",
        "severity": "high",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_07",
        "rule_code": "LM-ORIGIN-007",
        "name": "Country of Origin",
        "category": "packaged_commodity",
        "requirement": "Name of the country of manufacture, origin, or assembly must be declared for imported goods.",
        "validation_logic": "check_country_origin",
        "severity": "medium",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_08",
        "rule_code": "LM-EXP-008",
        "name": "Best Before / Expiry Date",
        "category": "packaged_commodity",
        "requirement": "Best Before, Use By, or Expiry date must be declared for commodities that may become unfit for human consumption over time.",
        "validation_logic": "check_expiry_date",
        "severity": "high",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_09",
        "rule_code": "LM-USP-009",
        "name": "Unit Sale Price",
        "category": "packaged_commodity",
        "requirement": "Price per standard unit (e.g. ₹/kg, ₹/liter, ₹/100g) must be declared where applicable.",
        "validation_logic": "check_unit_sale_price",
        "severity": "low",
        "version": "1.0",
        "active": True
    },
    {
        "id": "rule_10",
        "rule_code": "LM-FONT-010",
        "name": "Font Size & Readability Specifications",
        "category": "packaged_commodity",
        "requirement": "Declarations must be legible, definite, plain, conspicuous, and satisfy prescribed minimum font heights based on Principal Display Panel surface area.",
        "validation_logic": "check_font_readability",
        "severity": "medium",
        "version": "1.0",
        "active": True
    }
]

class RuleRepository:
    def get_all_rules(self) -> List[Dict[str, Any]]:
        return LEGAL_METROLOGY_RULES

    def get_active_rules(self) -> List[Dict[str, Any]]:
        return [r for r in LEGAL_METROLOGY_RULES if r.get("active", True)]

    def get_rule_by_code(self, rule_code: str) -> Optional[Dict[str, Any]]:
        for r in LEGAL_METROLOGY_RULES:
            if r["rule_code"] == rule_code:
                return r
        return None
