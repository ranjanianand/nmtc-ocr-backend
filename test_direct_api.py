#!/usr/bin/env python3
"""
Direct API test without server - test the functions directly
"""

import sys
import os
sys.path.append('.')

async def test_allocation_api_direct():
    """Test allocation years API functions directly"""
    try:
        print("Testing Allocation Years API functions directly...")
        print("=" * 60)

        # Import the API functions
        from app.api.allocation_years import (
            get_organization_allocation_years,
            get_allocation_year_dashboard,
            test_allocation_workflow
        )

        org_id = "test-org-123"

        # Test 1: Get allocation years
        print("1. Testing get_organization_allocation_years function")
        try:
            result = await get_organization_allocation_years(org_id)
            print(f"SUCCESS: {result.get('success')}")
            print(f"Years count: {result.get('total_years')}")
            if result.get('allocation_years'):
                for year in result['allocation_years'][:3]:
                    print(f"  - {year['year']}: {year['status']} (${year['total_amount']:,.2f})")
        except Exception as e:
            print(f"ERROR: {e}")

        print()

        # Test 2: Get dashboard
        print("2. Testing get_allocation_year_dashboard function")
        try:
            result = await get_allocation_year_dashboard(org_id, 2024)
            print(f"SUCCESS: {result.get('success')}")
            dashboard = result.get('dashboard_summary', {})
            print(f"2024 Status: {dashboard.get('status')}")
            print(f"Total Amount: ${dashboard.get('total_amount', 0):,.2f}")
            print(f"Has Allocation: {dashboard.get('has_allocation_agreement')}")
            print(f"QLICB Count: {dashboard.get('qalicb_count')}")
        except Exception as e:
            print(f"ERROR: {e}")

        print()

        # Test 3: Test workflow
        print("3. Testing test_allocation_workflow function")
        try:
            result = await test_allocation_workflow(org_id)
            print(f"SUCCESS: {result.get('success')}")
            print(f"Database: {result.get('database_connectivity')}")
            print(f"Years Function: {result.get('predefined_years_function')}")
            print(f"Dashboard Function: {result.get('dashboard_function')}")
        except Exception as e:
            print(f"ERROR: {e}")

        print()
        print("=" * 60)
        print("Direct API Testing Complete!")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_allocation_api_direct())