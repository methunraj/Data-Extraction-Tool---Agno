#!/usr/bin/env python3

import os
import tempfile
import json
import glob
from app.services import create_code_gen_agent

test_data = {
    "company": "Test Corp",
    "revenue": 1000000
}

print("=== Testing Code Execution Fix ===")

with tempfile.TemporaryDirectory() as temp_dir:
    print(f"Temp directory: {temp_dir}")
    
    agent = create_code_gen_agent(temp_dir)
    
    # Use the same prompt format as the workflow
    plan = "Create a simple Excel report with company data"
    prompt = f"Based on the following plan, and the provided JSON data, generate the python code to create the excel report and EXECUTE it immediately.\n\nIMPORTANT: You must RUN the Python code to actually create the Excel file - don't just show the code!\n\nPlan:\n{plan}\n\nJSON Data:\n{json.dumps(test_data, indent=2)}"
    
    print("Running agent with execution prompt...")
    response = agent.run(prompt)
    print("Response:", response.content)
    
    # Check if file was created
    excel_files = glob.glob(f"{temp_dir}/*.xlsx")
    if excel_files:
        print(f"✅ SUCCESS! Excel file created: {excel_files[0]}")
        print(f"File size: {os.path.getsize(excel_files[0])} bytes")
    else:
        print("❌ FAILED! No Excel file created")
        print(f"Files in temp dir: {os.listdir(temp_dir)}")

print("=== Test completed ===") 