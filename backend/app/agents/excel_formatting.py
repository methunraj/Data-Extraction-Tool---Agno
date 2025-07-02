"""
Excel Formatting Constants and Utilities
Shared formatting configuration for consistent Excel output
"""

# Color Palette
EXCEL_COLORS = {
    'header_bg': '1F4788',      # Dark blue background for headers
    'header_text': 'FFFFFF',    # White text for headers
    'subheader_bg': '4472C4',   # Medium blue for subheaders
    'alt_row': 'F2F2F2',        # Light gray for alternating rows
    'border': 'B8B8B8',         # Gray for borders
    'positive': '70AD47',       # Green for positive values
    'negative': 'C5504B',       # Red for negative values
    'warning': 'FFC000',        # Orange for warnings
    'highlight': 'FFFF00',      # Yellow for highlights
}

# Font Configurations
EXCEL_FONTS = {
    'header': {
        'bold': True,
        'size': 12,
        'color': EXCEL_COLORS['header_text'],
        'name': 'Calibri'
    },
    'subheader': {
        'bold': True,
        'size': 11,
        'color': EXCEL_COLORS['header_bg'],
        'name': 'Calibri'
    },
    'data': {
        'bold': False,
        'size': 10,
        'color': '000000',
        'name': 'Calibri'
    },
    'title': {
        'bold': True,
        'size': 16,
        'color': EXCEL_COLORS['header_bg'],
        'name': 'Calibri'
    }
}

# Number Formats
EXCEL_FORMATS = {
    'currency': '$#,##0.00',
    'currency_no_cents': '$#,##0',
    'percentage': '0.0%',
    'percentage_precise': '0.00%',
    'number': '#,##0',
    'number_precise': '#,##0.00',
    'date': 'DD-MMM-YYYY',
    'datetime': 'DD-MMM-YYYY HH:MM',
    'accounting': '_($* #,##0.00_);_($* (#,##0.00);_($* "-"??_);_(@_)',
}

# Column Type Detection Keywords
COLUMN_TYPE_KEYWORDS = {
    'currency': ['amount', 'price', 'cost', 'revenue', 'value', 'salary', 'fee', 'payment', 'balance', 'total'],
    'percentage': ['percent', 'rate', 'ratio', 'margin', 'growth', 'change'],
    'date': ['date', 'time', 'created', 'updated', 'modified', 'due', 'start', 'end', 'period'],
    'id': ['id', 'code', 'number', 'ref', 'reference', 'key'],
}

# Sheet Naming Rules
SHEET_NAME_RULES = {
    'max_length': 31,
    'invalid_chars': ['\\', '/', '?', '*', '[', ']', ':'],
    'reserved_names': ['History'],
}

def clean_sheet_name(name: str) -> str:
    """Clean sheet name to comply with Excel rules."""
    # Remove invalid characters
    for char in SHEET_NAME_RULES['invalid_chars']:
        name = name.replace(char, '')
    
    # Truncate to max length
    if len(name) > SHEET_NAME_RULES['max_length']:
        name = name[:SHEET_NAME_RULES['max_length']]
    
    # Ensure not a reserved name
    if name in SHEET_NAME_RULES['reserved_names']:
        name = f"{name}_"
    
    return name.strip()

def detect_column_type(column_name: str) -> str:
    """Detect column type based on name."""
    column_lower = column_name.lower()
    
    for col_type, keywords in COLUMN_TYPE_KEYWORDS.items():
        if any(keyword in column_lower for keyword in keywords):
            return col_type
    
    return 'general'

def get_number_format(column_name: str, data_type: str = None) -> str:
    """Get appropriate number format for a column."""
    col_type = detect_column_type(column_name)
    
    if col_type == 'currency':
        return EXCEL_FORMATS['currency']
    elif col_type == 'percentage':
        return EXCEL_FORMATS['percentage']
    elif col_type == 'date':
        return EXCEL_FORMATS['date']
    elif data_type in ['int64', 'float64']:
        return EXCEL_FORMATS['number']
    
    return '@'  # General text format