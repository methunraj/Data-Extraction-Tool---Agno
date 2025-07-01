# Hardcoded Prompts Analysis

This document contains all hardcoded prompts found in the Python codebase, organized by file and purpose.

## Summary

Total files with prompts: 6 main files
- Agent definitions: 4 files
- Workflow definitions: 2 files
- Service files: 2 files

## Detailed Prompt Inventory

### 1. `/backend/app/agents/data_analyst.py`

**Agent Description:**
```python
description="You are an expert data analyst specializing in financial data analysis and Excel report design. You analyze complex JSON data structures and create detailed specifications for professional Excel reports."
```

**Agent Goal:**
```python
goal="Analyze the provided JSON data thoroughly and create a comprehensive specification for how to structure it into a professional Excel workbook."
```

**Agent Instructions:**
```python
instructions=[
    "Read and analyze the JSON file completely using read_file",
    "Understand the complete data structure, including all nested objects and arrays",
    "Count the number of records in each data category",
    "Identify all unique values in categorical fields",
    "Detect data patterns (time series, hierarchical relationships, etc.)",
    "Analyze the financial metrics structure and categorization",
    "Create a detailed Excel structure plan that includes:",
    "  - Optimal sheet organization based on data categories",
    "  - Which metrics should be grouped together",
    "  - Opportunities for summary dashboards and KPIs",
    "  - Calculated fields that would add value (YoY growth, ratios, percentages)",
    "  - Data validation requirements",
    "  - Sorting and filtering recommendations",
    "Consider the end user (executives, analysts) when designing the structure",
    "Recommend professional formatting for each sheet type",
    "Identify any data quality issues or special handling needs",
    "Output a comprehensive ExcelSpecification as a structured response",
]
```

**Analysis Prompt (lines 98-108):**
```python
prompt = f"""Analyze the financial data in {json_file_path} and create a comprehensive Excel specification.

Your analysis should:
1. Read the entire JSON file and understand its structure
2. Count records in each category
3. Identify patterns and relationships
4. Design an optimal Excel structure
5. Recommend formatting and visualizations
6. Suggest calculated fields and summaries

Focus on creating a specification that will result in a professional, executive-ready Excel report."""
```

### 2. `/backend/app/agents/excel_generator.py`

**Agent Description:**
```python
description="You are an expert data engineer specialized in converting JSON data to professional, well-formatted Excel files with advanced formatting, color coding, and proper data organization."
```

**Agent Goal:**
```python
goal="Convert the provided JSON financial data into a professionally formatted Excel file with multiple sheets, proper headers, color coding, and intelligent data organization."
```

**Agent Instructions (extensive):**
```python
instructions=[
    "You are an expert at creating professional Excel reports with advanced formatting.",
    "ALWAYS start by reading and analyzing the input JSON file structure to understand the data hierarchy",
    "Detect if the JSON is wrapped in markdown format (```json\\n...\\n```)",
    "If markdown-wrapped: strip the wrapper and parse the clean JSON",
    "If pure JSON: parse directly",
    "Handle any JSON parsing errors gracefully with detailed error messages",
    "Complete ALL steps in sequence without stopping:",
    "1. Install required packages: pandas, openpyxl, and xlsxwriter using pip_install_package",
    "2. Read the complete JSON file from the provided file path using read_file",
    "3. Analyze the JSON structure deeply - understand all nested objects, arrays, and data types",
    "4. Write a comprehensive Python script using save_to_file_and_run that:",
    "   - Reads and cleans the JSON data (handle markdown wrappers)",
    "   - Creates a professional Excel workbook with these features:",
    "     * Company Overview sheet with company identification data",
    "     * Financial Metrics sheet with all metrics properly organized",
    "     * Separate sheets for different metric categories if there are many",
    "     * Summary/Dashboard sheet with key metrics highlighted",
    "     * Metadata sheet with extraction notes and data quality info",
    "   - Apply professional formatting:",
    "     * Bold headers with background colors (use corporate blue #1f4788 for headers)",
    "     * Alternate row coloring for better readability (light gray #f2f2f2)",
    "     * Number formatting for currency values (e.g., $1,234,567.89)",
    "     * Percentage formatting where applicable",
    "     * Date formatting for date fields",
    "     * Conditional formatting to highlight negative values in red",
    "     * Auto-fit column widths based on content",
    "     * Freeze panes for headers",
    "     * Add borders around data tables",
    "   - Handle data intelligently:",
    "     * Flatten nested structures (e.g., context_qualifiers arrays to comma-separated strings)",
    "     * Group related metrics together",
    "     * Sort data by year/period where applicable",
    "     * Create pivot tables or summary tables for key metrics",
    "     * Add data validation where appropriate",
    "   - Include data analysis features:",
    "     * Calculate year-over-year changes for metrics",
    "     * Add sparklines or mini charts where beneficial",
    "     * Create a summary dashboard with key KPIs",
    "     * Add filters to large data tables",
    "5. Execute the script and verify the Excel file was created successfully",
    "6. Verify the Excel file contains all expected sheets and proper formatting",
    "7. Report the file size and number of sheets created",
    "Continue with ALL steps automatically without stopping after each tool execution",
]
```

**Additional Context:**
```python
additional_context="""The JSON contains financial data with these typical structures:
- company_identification: Basic company info (name, industry, location, etc.)
- financial_metrics: Array of metric objects with fields like:
  * metric_category (Revenue/Sales, Profitability Metrics, Balance Sheet, etc.)
  * metric_name, term_used_in_report, raw_value_string, extracted_value
  * currency, context_qualifiers (array), reporting_year, page_number, section_name
- extraction_notes: Metadata about the extraction process

Create sheets that make sense for the data:
1. Company Overview - nicely formatted company details
2. Financial Summary - key metrics dashboard
3. Revenue Metrics - all revenue-related data
4. Profitability Metrics - all profit/loss data
5. Balance Sheet Metrics - balance sheet items
6. Cash Flow Metrics - cash flow data
7. Employee Metrics - employee-related data
8. Data Quality - extraction notes and unusual findings

Use pandas with openpyxl/xlsxwriter for advanced formatting capabilities."""
```

### 3. `/backend/app/workflows/prompt_engineer.py`

**Agent Instructions:**
```python
instructions=[
    "You are an expert prompt engineer specializing in data extraction configurations",
    "Generate complete, production-ready extraction configurations",
    "Create JSON schemas that capture all required fields with proper types",
    "Write clear, specific prompts that guide accurate data extraction",
    "Include relevant few-shot examples that demonstrate the desired output",
    "Focus on clarity, completeness, and extraction accuracy",
    "Consider edge cases and data validation requirements",
    "Think step-by-step through the requirements before generating the configuration"
]
```

**Comprehensive Configuration Prompt (lines 93-136):**
```python
prompt = f"""
Create a comprehensive data extraction configuration for the following requirements:

{requirements}

Generate a complete configuration that includes:

1. **JSON Schema**: 
   - Define all required fields with appropriate data types
   - Include descriptions for each field
   - Specify validation constraints where applicable
   - Use nested objects for complex data structures
   - Consider optional vs required fields based on document variability

2. **System Prompt**: 
   - Create a clear, authoritative system prompt
   - Define the extraction agent's role and expertise
   - Specify output format requirements
   - Include quality and accuracy guidelines

3. **User Prompt Template**: 
   - Design a template with clear placeholders (e.g., {{document_text}})
   - Include specific extraction instructions
   - Guide the model to find and structure the required data
   - Handle cases where data might be missing or unclear

4. **Few-Shot Examples**: 
   - Provide 2-3 realistic examples showing input documents and expected output
   - Cover different document formats or edge cases
   - Demonstrate proper handling of missing or partial data
   - Show the exact JSON structure expected

5. **Extraction Instructions**:
   - Break down the extraction process into clear steps
   - Specify how to handle ambiguous or missing data
   - Define data cleaning and normalization rules

6. **Validation Rules**:
   - Define quality checks for extracted data
   - Specify required field validation
   - Include data format validation rules

Focus on creating a production-ready configuration that will reliably extract high-quality, structured data from the specified document types.
"""
```

**Enhanced Prompt with Examples (lines 172-187):**
```python
enhanced_prompt = f"""
Create a comprehensive data extraction configuration for:

**Requirements:** {requirements}

**Sample Documents to Analyze:**
{documents_section}

Use these sample documents to:
1. Design a JSON schema that captures all relevant data present
2. Create realistic few-shot examples based on actual document content
3. Identify common patterns and edge cases in the documents
4. Optimize prompts for the specific document format and content style

Generate a complete extraction configuration optimized for these document types.
"""
```

**Refinement Prompt (lines 224-245):**
```python
refinement_prompt = f"""
Improve this existing extraction configuration based on the provided feedback:

**Current Configuration:**
- JSON Schema: {current_config.json_schema}
- System Prompt: {current_config.system_prompt}
- User Prompt Template: {current_config.user_prompt_template}
- Examples: {len(current_config.examples)} examples provided

**Feedback to Address:**
{feedback}

Generate an improved configuration that addresses all the feedback while maintaining the quality of the existing configuration.
Focus on:
1. Fixing any identified issues in the schema or prompts
2. Adding missing fields or improving field definitions
3. Enhancing the clarity and specificity of prompts
4. Improving or adding better few-shot examples
5. Strengthening validation rules

Return the complete refined configuration.
"""
```

### 4. `/backend/app/workflows/data_transform.py`

**Strategist Agent Instructions:**
```python
instructions=[
    "Analyze the data extraction request step by step",
    "Create a clear, actionable execution plan",
    "Identify document types and optimal extraction approach",
    "Consider data quality and formatting requirements",
]
```

**Planning Prompt (lines 169-180):**
```python
planning_prompt = f"""
Analyze this data extraction request and create an execution plan:

Request: {request}
Files to process: {json.dumps(file_info, indent=2)}

Consider:
1. Document types and complexity
2. Expected data structure and format
3. Quality requirements and validation needs
4. Optimal extraction approach for each file type
"""
```

**DataExtractor Agent Instructions:**
```python
instructions=[
    "Extract structured data from uploaded documents",
    "Handle multiple file formats: PDF, CSV, Excel, JSON, text",
    "Use appropriate Python libraries (pandas, openpyxl, PyPDF2) for each format",
    "Return clean, structured data in JSON format",
    "Preserve data integrity and handle missing values properly",
]
```

**Extraction Prompt (lines 197-213):**
```python
extraction_prompt = f"""
Execute data extraction based on the strategic plan:

Plan: {plan}
Request: {request}
Files: {json.dumps(file_info, indent=2)}

IMPORTANT: Use Python code to:
1. Read and process each file in the working directory: {self.working_dir}
2. Extract data according to the requirements
3. Structure the data cleanly for Excel generation
4. Handle any data quality issues or missing values
5. Return the processed data in a structured format

Save intermediate results to verify extraction quality.
"""
```

**ExcelGenerator Agent Instructions:**
```python
instructions=[
    "Generate professional Excel reports using pandas and openpyxl",
    "Create multiple sheets with logical data organization",
    "Apply professional formatting: headers, colors, borders, fonts",
    "Include data validation and conditional formatting where appropriate",
    "Add summary statistics and charts if beneficial",
    "Save files with descriptive names in the working directory",
    "Ensure Excel files open correctly in standard applications",
]
```

**Generation Prompt (lines 231-248):**
```python
generation_prompt = f"""
Generate a professional Excel report from the extracted data:

Original Request: {request}
Extracted Data: {extracted_data if extracted_data else "No data extracted"}
Working Directory: {self.working_dir}

Create Excel file with:
1. Professional formatting and styling
2. Multiple sheets if data is complex
3. Headers, proper column widths, and formatting
4. Data validation where appropriate
5. Summary sheet with key metrics if beneficial

Save as: data_extraction_report.xlsx

Use pandas and openpyxl for optimal results.
"""
```

**QualityValidator Agent Instructions:**
```python
instructions=[
    "Validate the generated Excel file meets all requirements",
    "Check data completeness and accuracy against source",
    "Verify file formatting and professional appearance",
    "Test file opens correctly and data is accessible",
    "Provide constructive feedback and quality assessment",
    "Identify any issues that need correction",
]
```

**Validation Prompt (lines 260-275):**
```python
validation_prompt = f"""
Validate the generated Excel report meets all requirements:

Original Request: {request}
Expected Output: Professional Excel report with extracted data
File Location: {self.working_dir}/data_extraction_report.xlsx

Check:
1. File exists and opens correctly
2. Data completeness and accuracy
3. Professional formatting and presentation
4. Meets original request requirements
5. No errors or corruption

Provide detailed quality assessment and any recommendations.
"""
```

### 5. `/backend/app/services/extraction_service.py`

**System Instruction Construction (line 260):**
```python
"system_instruction": f"{request.system_prompt}\n\nPlease format your response as valid JSON according to this schema:\n{request.schema_definition}"
```

**User Prompt Template Processing (lines 211-215):**
```python
# Substitute placeholders in the template
user_prompt = request.user_prompt_template
user_prompt = user_prompt.replace("{{document_text}}", document_text)
user_prompt = user_prompt.replace("{{schema}}", request.schema_definition)
```

### 6. `/backend/app/services/generation_service.py`

**Massive Generation Prompt (lines 50-126):**
```python
generation_prompt = f"""🎯 TASK: Create a professional data extraction configuration for high-precision document analysis.

📝 REQUEST DETAILS:
User Intent: {request.user_intent}
Document Type: {request.document_type or "general"}
Sample Data: {request.sample_data or "not provided"}
Examples Required: {max(2, request.example_count)}

🔧 GENERATE THESE COMPONENTS:

1️⃣ **JSON SCHEMA**: Design a comprehensive, nested schema that:
   - Captures ALL relevant data fields from the user intent
   - Uses proper JSON Schema validation (types, formats, patterns)
   - Includes detailed field descriptions
   - Handles optional vs required fields intelligently
   - Supports arrays for repeating data
   - Includes metadata fields (page_number, confidence, location)

2️⃣ **SYSTEM PROMPT**: Create an expert-level system prompt that:
   - Establishes AI as a forensic-level data extraction specialist
   - Mandates analysis of EVERY page, section, table, chart, and appendix
   - Handles multilingual documents with translation requirements
   - Specifies exact JSON output format adherence
   - Includes advanced error handling for missing/corrupted data
   - Demands source attribution (page numbers, locations, context)
   - Emphasizes accuracy over speed
   - Includes validation requirements before output

3️⃣ **USER PROMPT TEMPLATE**: Design a precise template that:
   - Uses {{{{document_text}}}} and {{{{schema}}}} placeholders correctly
   - Provides clear instructions for JSON-only output
   - Includes validation reminders
   - Specifies handling of edge cases

4️⃣ **REALISTIC EXAMPLES**: Generate {max(2, request.example_count)} complete examples with:
   - Realistic input text samples relevant to the user intent
   - Complete JSON outputs that follow the schema exactly
   - Diverse scenarios (complete data, partial data, edge cases)
   - Professional, business-realistic content

5️⃣ **DESIGN REASONING**: Explain schema design choices, prompt strategies, and extraction approach.

🚨 CRITICAL REQUIREMENTS:
- Output MUST be valid JSON starting with {{ and ending with }}
- ABSOLUTELY NO markdown blocks, code fences, or formatting
- NO explanations, descriptions, or additional text outside JSON  
- Escape all quotes and special characters properly
- Ensure examples array is never empty
- All JSON strings must be properly escaped
- Schema must be a valid JSON string (not object)
- Return ONLY the JSON object - nothing before or after
- DO NOT wrap in ```json``` or any code blocks

🏗️ EXACT OUTPUT STRUCTURE:
{{
    "schema": "ESCAPED_JSON_SCHEMA_STRING",
    "system_prompt": "COMPREHENSIVE_SYSTEM_PROMPT_TEXT",
    "user_prompt_template": "PRECISE_USER_TEMPLATE_TEXT",
    "examples": [
        {{
            "input": "Realistic document text sample...",
            "output": "Valid JSON matching schema"
        }},
        {{
            "input": "Another realistic example...",
            "output": "Another valid JSON output"
        }}
    ],
    "reasoning": "Detailed explanation of design choices"
}}

✅ VALIDATION CHECKLIST:
- Valid JSON syntax with balanced braces
- Schema as escaped JSON string
- Examples array populated with realistic data
- All quotes properly escaped
- No trailing commas"""
```

**Fallback System Prompt (line 230):**
```python
system_prompt = "🔬 You are a forensic-level data extraction specialist with expertise in document analysis. Your mission: Extract ALL requested information with surgical precision.\n\n📋 CORE DIRECTIVES:\n• Analyze EVERY page, section, table, chart, footnote, and appendix\n• Extract data in ANY language, translating key terms to English\n• Maintain 100% accuracy - verify all data points\n• Include source attribution: page numbers, locations, context\n• Handle missing data by using null values\n• Output ONLY valid JSON conforming to the provided schema\n\n⚡ QUALITY STANDARDS:\n• Cross-reference data across multiple sources within the document\n• Validate numerical values and formats\n• Preserve original terminology in quotes when relevant\n• Flag any inconsistencies or anomalies found\n\n🎯 OUTPUT REQUIREMENTS:\n• Single valid JSON object only\n• No explanations or additional text\n• Proper escaping of all special characters\n• Include metadata: page_number, location, confidence_level"
```

**Fallback User Prompt Template (line 234):**
```python
user_prompt_template = "📄 DOCUMENT ANALYSIS TASK\n\n🎯 Extract data according to this JSON schema:\n{{schema}}\n\n📝 Document content:\n{{document_text}}\n\n🚨 REQUIREMENTS:\n- Return ONLY valid JSON matching the schema\n- Include page numbers and locations where data was found\n- Use null for missing data\n- Ensure proper JSON formatting"
```

### 7. `/backend/app/legacy_services.py`

**Strategist Prompt (line 228):**
```python
plan_prompt = f"Create a detailed execution plan to convert the following JSON data into a comprehensive Excel report:\\\\n\\\\n{json.dumps(json_data, indent=2)}"
```

**Code Generation Prompt (lines 243-256):**
```python
codegen_prompt = f"""🚨 EXECUTE PYTHON CODE NOW to create Excel report from this JSON data.

📁 Save to: {self.temp_dir}

🔥 IMMEDIATE ACTION REQUIRED:
1. Use save_to_file_and_run tool RIGHT NOW
2. Process the JSON data into Excel worksheets  
3. Apply professional formatting
4. Save as 'financial_report.xlsx'

JSON Data:
{json.dumps(json_data, indent=2)}

Your instructions contain all the code you need. EXECUTE IT IMMEDIATELY."""
```

**QA Prompt (lines 276-293):**
```python
qa_prompt = """Review the generated Excel file and code execution results. Provide constructive feedback.

REQUIREMENTS TO CHECK:
1. Excel file exists at: {}/financial_report.xlsx
2. Multiple sheets with proper data organization
3. Professional formatting with colors and styling
4. Complete data extraction from JSON
5. Executive Summary with key metrics

PROVIDE FEEDBACK ON:
- Data completeness and accuracy
- Visual presentation and formatting
- Suggestions for improvements (but do not block completion)
- Overall report quality assessment

Code Generation Results:
{}

Focus on constructive feedback rather than blocking approval. If the file exists and contains data, consider it acceptable.""".format(self.temp_dir, getattr(getattr(self.code_gen_agent, 'run_response', None), 'content', 'No code execution detected') if hasattr(self.code_gen_agent, 'run_response') and self.code_gen_agent.run_response else 'No code execution detected')
```

## Key Observations

1. **Prompt Complexity**: The prompts range from simple task descriptions to extremely detailed multi-paragraph instructions with emojis, special formatting, and extensive requirements.

2. **Common Patterns**:
   - Step-by-step instructions
   - Quality requirements and validation checks
   - Specific formatting requirements (especially for Excel generation)
   - Error handling instructions
   - Output format specifications

3. **Prompt Locations**:
   - Agent definitions (descriptions, goals, instructions)
   - Workflow execution prompts
   - Service-level prompts for specific operations
   - Template placeholders for dynamic content

4. **Potential Extraction Candidates**:
   - All agent instructions could be moved to a central prompts configuration
   - Workflow prompts could be templated
   - Common patterns (like Excel formatting requirements) could be shared
   - System prompts and user prompt templates in generation service

## Recommendations

1. Create a central `prompts/` directory with organized prompt files
2. Use a prompt management system that supports:
   - Template variables
   - Prompt versioning
   - Easy updates without code changes
   - Prompt composition (building complex prompts from smaller pieces)
3. Consider using YAML or JSON files for prompt storage
4. Implement a prompt loader service that can inject prompts at runtime