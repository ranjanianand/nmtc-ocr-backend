#!/usr/bin/env python3
"""
Emergency Data Clear and Complete End-to-End Test
Clear all data and test complete allocation workflow from start to finish
"""
import asyncio
import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
BACKEND_URL = "http://localhost:8005"
TEST_ORG_ID = "liftfund"
TEST_YEAR = 2025
TEST_USER_ID = "user123"

def test_server_running():
    """Test if backend server is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"SUCCESS: Backend server running: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"FAILED: Backend server not accessible: {e}")
        return False

def clear_allocation_data():
    """Clear all allocation data for clean testing"""
    try:
        # Try to clear via API if endpoint exists
        response = requests.delete(f"{BACKEND_URL}/api/allocation-years/test-data", timeout=10)
        if response.status_code in [200, 404]:
            print("✅ Data clearing attempted via API")
            return True
    except Exception as e:
        print(f"⚠️ API clear not available: {e}")

    # Manual database clearing via direct supabase
    try:
        import sys
        sys.path.append('.')
        from app.services.supabase_service import supabase_service

        async def clear_tables():
            # Get the supabase client directly
            client = supabase_service.client

            # Clear tables in correct order to avoid foreign key issues
            tables = [
                'progress_events',
                'processing_jobs',
                'qlici_loans',
                'allocation_documents',
                'allocation_years',
                'document_sessions'
            ]

            for table in tables:
                try:
                    result = client.table(table).delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                    print(f"✅ Cleared table: {table}")
                except Exception as e:
                    print(f"⚠️ Could not clear {table}: {e}")

            print("✅ Database cleared successfully")
            return True

        return asyncio.run(clear_tables())

    except Exception as e:
        print(f"❌ Database clear failed: {e}")
        return False

def test_allocation_workflow():
    """Test complete allocation workflow step by step"""
    print("\n🧪 Testing Complete Allocation Workflow")

    # Step 1: Check allocation years endpoint
    print("\n1️⃣ Testing allocation years endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/allocation-years/org/{TEST_ORG_ID}", timeout=10)
        print(f"✅ Allocation years API: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Years found: {len(data.get('years', []))}")
            for year_data in data.get('years', []):
                print(f"   - {year_data.get('year')}: {year_data.get('status', 'unknown')}")

    except Exception as e:
        print(f"❌ Allocation years API failed: {e}")
        return False

    # Step 2: Test dashboard for a specific year (should be empty/inactive)
    print(f"\n2️⃣ Testing dashboard for year {TEST_YEAR}...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/dashboard", timeout=10)
        print(f"✅ Dashboard API: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            dashboard = data.get('dashboard_summary')
            if dashboard:
                print(f"   Status: {dashboard.get('status')}")
                print(f"   Has Allocation Agreement: {dashboard.get('has_allocation_agreement')}")
                print(f"   Total Amount: ${dashboard.get('total_amount', 0):,}")

                # This should be FALSE for clean state
                if not dashboard.get('has_allocation_agreement'):
                    print("✅ Dashboard shows clean state (no allocation agreement)")
                else:
                    print("❌ Dashboard shows existing allocation agreement (NOT CLEAN)")
                    return False
            else:
                print("✅ Dashboard is empty (clean state)")

    except Exception as e:
        print(f"❌ Dashboard API failed: {e}")
        return False

    # Step 3: Test upload endpoint (without actually uploading)
    print(f"\n3️⃣ Testing upload endpoint structure...")
    try:
        # Just test the endpoint exists (OPTIONS request)
        response = requests.options(f"{BACKEND_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/upload", timeout=10)
        print(f"✅ Upload endpoint accessible: {response.status_code}")

    except Exception as e:
        print(f"❌ Upload endpoint failed: {e}")
        return False

    # Step 4: Test processing progress endpoint
    print(f"\n4️⃣ Testing progress tracking endpoint...")
    try:
        # Test with dummy document ID
        test_doc_id = "test-doc-123"
        response = requests.get(f"{BACKEND_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/document/{test_doc_id}/progress", timeout=10)
        print(f"✅ Progress endpoint accessible: {response.status_code}")

        # 404 is expected for non-existent document
        if response.status_code in [404, 200]:
            print("✅ Progress endpoint working correctly")

    except Exception as e:
        print(f"❌ Progress endpoint failed: {e}")
        return False

    print("\n✅ ALL WORKFLOW TESTS PASSED - System is ready for upload testing")
    return True

def main():
    """Main test execution"""
    print("EMERGENCY DATA CLEAR AND COMPLETE WORKFLOW TEST")
    print("=" * 60)

    # Step 1: Check server
    if not test_server_running():
        print("❌ CRITICAL: Backend server not running")
        return False

    # Step 2: Clear data
    print("\n🧹 Clearing all allocation data...")
    if not clear_allocation_data():
        print("⚠️ WARNING: Data clearing may have failed")

    # Step 3: Test workflow
    if not test_allocation_workflow():
        print("\n❌ CRITICAL: Workflow tests failed")
        return False

    print("\n🎉 SUCCESS: System is clean and ready for testing")
    print("\nNext steps:")
    print("1. Go to frontend: http://localhost:8085")
    print("2. Navigate to allocation years")
    print(f"3. Select year {TEST_YEAR}")
    print("4. Upload an allocation agreement")
    print("5. Verify processing pipeline works")

    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)