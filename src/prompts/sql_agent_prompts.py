"""
Centralized prompts for SQL Agent components
"""

INTENT_PARSER_PROMPT = """
You are an expert at analyzing Hong Kong housing-related questions and extracting structured information for database queries.

DATABASE SCHEMA SUMMARY:
{schema_summary}

Given this user query about Hong Kong housing data: "{query}"

Extract the following information and return it as a valid JSON object:

{{
    "tables": ["array", "of", "table", "names", "needed"],
    "columns": ["array", "of", "column", "names", "mentioned"],
    "filters": ["array", "of", "filter", "conditions", "like", "estate_name_en = 'Lohas Park'"],
    "aggregation": "aggregation function needed (avg, sum, count, max, min, or null if none)",
    "group_by": ["array", "of", "columns", "to", "group", "by", "or", "empty", "array"],
    "order_by": ["array", "of", "columns", "to", "order", "by", "or", "empty", "array"],
    "limit": "number for LIMIT clause or null if none"
}}

Guidelines:
- Tables should be actual table names from the schema above
- Columns should be actual column names from the schema above
- For Hong Kong-specific concepts:
  - "school nets" refers to estate_school_nets table
  - "MTR lines" refers to estate_mtr_lines table
  - "facilities" refers to estate_facilities and facilities tables
  - "regions" can be districts, subregions, or regions tables
- Filters should be in SQL-like syntax but don't include table prefixes yet
- Aggregation should be the function name in lowercase or null
- Be specific and accurate - use the schema information provided
- If something is not mentioned, use empty arrays or null

Return only the JSON object, no additional text.
"""

SCHEMA_SUMMARY = """
KEY TABLES AND COLUMNS:

estates: estate_id, estate_name_zh, estate_name_en, region_id, subregion_id, district_id, address_zh, address_en, latitude, longitude
buildings: building_id, building_name_zh, building_name_en, estate_id, phase_id
units: unit_id, floor, flat, area, net_area, bedroom, sitting_room, building_id
transactions: tx_id, tx_date, price, last_tx_date, gain, net_ft_price, unit_id
estate_school_nets: estate_id, school_net_id, school_net_name_zh, school_net_name_en
estate_mtr_lines: estate_id, mtr_line_name_zh, mtr_line_name_en
estate_facilities: estate_id, facility_id
facilities: facility_id, facility_name_zh, facility_name_en
districts: district_id, district_name_zh, district_name_en, subregion_id
subregions: subregion_id, subregion_name_zh, subregion_name_en, region_id
regions: region_id, region_name_zh, region_name_en
phases: phase_id, phase_name_zh, phase_name_en, estate_id
estate_monthly_market_info: estate_id, record_date, avg_ft_price, avg_net_ft_price, etc.
"""