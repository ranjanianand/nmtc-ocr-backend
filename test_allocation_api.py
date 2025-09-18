#!/usr/bin/env python3
"""
Test script for Allocation Years API
"""

import requests
import json
from datetime import datetime

def test_allocation_years_api():
    base_url = 'http://localhost:8000'
    org_id = 'test-org-123'

    print('Testing Allocation Years API...')
    print('=' * 50)

    try:
        # Test 1: Get allocation years for org
        print('1. Testing GET /api/allocation-years/org/{org_id}')
        response = requests.get(f'{base_url}/api/allocation-years/org/{org_id}')
        print(f'Status: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            print(f'Success: {data.get("success")}')
            print(f'Years returned: {len(data.get("allocation_years", []))}')
            for year_data in data.get('allocation_years', [])[:3]:  # Show first 3
                print(f'  - {year_data["year"]}: {year_data["status"]} (Total: ${year_data["total_amount"]:,.2f})')
        else:
            print(f'Error: {response.text}')

        print()

        # Test 2: Get dashboard for specific year
        print('2. Testing GET /api/allocation-years/org/{org_id}/year/2024/dashboard')
        response = requests.get(f'{base_url}/api/allocation-years/org/{org_id}/year/2024/dashboard')
        print(f'Status: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            dashboard = data.get('dashboard_summary', {})
            print(f'2024 Dashboard Summary:')
            print(f'  - Year: {dashboard.get("year")}')
            print(f'  - Total Amount: ${dashboard.get("total_amount", 0):,.2f}')
            print(f'  - Deployed Amount: ${dashboard.get("deployed_amount", 0):,.2f}')
            print(f'  - Available Amount: ${dashboard.get("available_amount", 0):,.2f}')
            print(f'  - Status: {dashboard.get("status")}')
            print(f'  - Processing Status: {dashboard.get("processing_status")}')
            print(f'  - Has Allocation Agreement: {dashboard.get("has_allocation_agreement")}')
            print(f'  - QLICB Count: {dashboard.get("qalicb_count")}')
            print(f'  - Document Count: {dashboard.get("document_count")}')
            print(f'  - Show QLICB Section: {data.get("show_qlicb_section")}')
        else:
            print(f'Error: {response.text}')

        print()

        # Test 3: Get QALICBs for year
        print('3. Testing GET /api/allocation-years/org/{org_id}/year/2024/qlicb')
        response = requests.get(f'{base_url}/api/allocation-years/org/{org_id}/year/2024/qlicb')
        print(f'Status: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            print(f'QLICB Entities:')
            print(f'  - Success: {data.get("success")}')
            print(f'  - Total Count: {data.get("total_count")}')
            print(f'  - Entities: {len(data.get("qalicb_entities", []))}')
        else:
            print(f'Error: {response.text}')

        print()

        # Test 4: Test endpoint
        print('4. Testing GET /api/allocation-years/test/org/{org_id}')
        response = requests.get(f'{base_url}/api/allocation-years/test/org/{org_id}')
        print(f'Status: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            print(f'Test Results:')
            print(f'  - Success: {data.get("success")}')
            print(f'  - Database Connectivity: {data.get("database_connectivity")}')
            print(f'  - Predefined Years Function: {data.get("predefined_years_function")}')
            print(f'  - Dashboard Function: {data.get("dashboard_function")}')
            print(f'  - Message: {data.get("message")}')
        else:
            print(f'Error: {response.text}')

        print()
        print('=' * 50)
        print('API Testing Complete!')

    except requests.exceptions.ConnectionError:
        print('❌ Connection Error: Backend server not running')
        print('   Start server with: uvicorn app.main:app --reload --port 8000')
    except Exception as e:
        print(f'❌ Unexpected Error: {e}')

if __name__ == '__main__':
    test_allocation_years_api()