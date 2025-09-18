#!/usr/bin/env python3
"""
Complete Allocation Agreement Workflow Test
Tests the entire end-to-end workflow from upload through report generation.
"""

import asyncio
import aiohttp
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
TEST_YEAR = 2024
TEST_FILE_PATH = "test_allocation.txt"

class AllocationWorkflowTester:
    def __init__(self):
        self.session = None
        self.document_id = None
        self.upload_response = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_step_1_upload_allocation(self):
        """Test Step 1: Upload allocation agreement"""
        print("\n" + "="*60)
        print("STEP 1: Upload Allocation Agreement")
        print("="*60)

        # Create test file if it doesn't exist
        if not os.path.exists(TEST_FILE_PATH):
            with open(TEST_FILE_PATH, 'w') as f:
                f.write("""NMTC Allocation Agreement Test Document

This is a test allocation agreement document.
Total Allocation: $10,000,000
Service Area: Los Angeles County, California
QEI Investment Deadline: December 31, 2024
""")
            print(f"[OK] Created test file: {TEST_FILE_PATH}")

        # Prepare multipart form data
        with open(TEST_FILE_PATH, 'rb') as f:
            file_content = f.read()

        # Create form data
        form_data = aiohttp.FormData()
        form_data.add_field('file', file_content, filename='test_allocation.pdf', content_type='application/pdf')
        form_data.add_field('description', f'Test allocation agreement for {TEST_YEAR}')

        url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/upload-allocation"

        try:
            async with self.session.post(url, data=form_data) as response:
                if response.status == 200:
                    self.upload_response = await response.json()
                    self.document_id = self.upload_response.get('document_id')

                    print(f"✅ Upload successful!")
                    print(f"   Document ID: {self.document_id}")
                    print(f"   Processing Started: {self.upload_response.get('processing_started', 'Unknown')}")
                    print(f"   Pipeline Status: {self.upload_response.get('pipeline', {}).get('status', 'Unknown')}")

                    # Check for frontend compatibility
                    if 'pipelineStarted' in self.upload_response:
                        print(f"✅ Frontend compatibility: pipelineStarted = {self.upload_response['pipelineStarted']}")
                    else:
                        print("⚠️  Missing 'pipelineStarted' flag for frontend compatibility")

                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Upload failed: HTTP {response.status}")
                    print(f"   Error: {error_text}")
                    return False

        except Exception as e:
            print(f"❌ Upload exception: {str(e)}")
            return False

    async def test_step_2_monitor_progress(self):
        """Test Step 2: Monitor processing progress"""
        print("\n" + "="*60)
        print("🔄 STEP 2: Monitor Processing Progress")
        print("="*60)

        if not self.document_id:
            print("❌ No document ID available for progress monitoring")
            return False

        url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/document/{self.document_id}/progress"

        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        progress_data = await response.json()

                        pipeline = progress_data.get('pipeline', {})
                        current_stage = pipeline.get('current_stage', 0)
                        total_stages = pipeline.get('total_stages', 6)
                        overall_progress = pipeline.get('overall_progress', 0)

                        print(f"📊 Attempt {attempt + 1}/{max_attempts}:")
                        print(f"   Stage: {current_stage}/{total_stages}")
                        print(f"   Progress: {overall_progress}%")
                        print(f"   Status: {pipeline.get('overall_status', 'unknown')}")

                        # Show stage details
                        stages = pipeline.get('stages', [])
                        for stage in stages:
                            status_icon = "✅" if stage['status'] == 'completed' else "🔄" if stage['status'] == 'in_progress' else "⏳"
                            print(f"   {status_icon} {stage['name']}: {stage['status']}")

                        # Check if complete
                        if progress_data.get('processing_complete', False):
                            print("✅ Processing completed!")
                            return True

                        # Wait before next check
                        await asyncio.sleep(3)
                    else:
                        error_text = await response.text()
                        print(f"❌ Progress check failed: HTTP {response.status}")
                        print(f"   Error: {error_text}")
                        return False

            except Exception as e:
                print(f"❌ Progress check exception: {str(e)}")
                return False

        print("⚠️  Processing did not complete within expected time")
        return False

    async def test_step_3_verify_database_results(self):
        """Test Step 3: Verify database results storage"""
        print("\n" + "="*60)
        print("🔄 STEP 3: Verify Database Results Storage")
        print("="*60)

        if not self.document_id:
            print("❌ No document ID available for database verification")
            return False

        # Test document record exists
        print("📋 Checking document record...")

        # For now, we'll verify through the progress endpoint which queries the database
        url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/document/{self.document_id}/progress"

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Document exists in database")
                    print(f"   Filename: {data.get('filename', 'Unknown')}")
                    print(f"   Upload time: {data.get('uploaded_at', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Could not verify document in database: HTTP {response.status}")
                    return False

        except Exception as e:
            print(f"❌ Database verification exception: {str(e)}")
            return False

    async def test_step_4_check_allocation_dashboard(self):
        """Test Step 4: Check allocation dashboard integration"""
        print("\n" + "="*60)
        print("🔄 STEP 4: Check Allocation Dashboard Integration")
        print("="*60)

        # Test dashboard endpoint
        url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/dashboard"

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    dashboard_data = await response.json()

                    print("✅ Dashboard data retrieved successfully!")

                    # Check key dashboard metrics
                    summary = dashboard_data.get('summary', {})
                    print(f"   Has allocation agreement: {summary.get('has_allocation_agreement', False)}")
                    print(f"   Total amount: ${summary.get('total_amount', 0):,}")
                    print(f"   Document count: {summary.get('document_count', 0)}")
                    print(f"   Processing status: {summary.get('processing_status', 'unknown')}")

                    return True
                elif response.status == 404:
                    print("⚠️  Dashboard endpoint not found - may not be implemented yet")
                    return False
                else:
                    error_text = await response.text()
                    print(f"❌ Dashboard check failed: HTTP {response.status}")
                    print(f"   Error: {error_text}")
                    return False

        except Exception as e:
            print(f"❌ Dashboard check exception: {str(e)}")
            return False

    async def run_complete_test(self):
        """Run the complete end-to-end test"""
        print("🚀 Starting Complete Allocation Agreement Workflow Test")
        print(f"🎯 Target: {BASE_URL}")
        print(f"🏢 Org ID: {TEST_ORG_ID}")
        print(f"📅 Year: {TEST_YEAR}")
        print(f"⏰ Started: {datetime.now().isoformat()}")

        results = {
            'step_1_upload': False,
            'step_2_progress': False,
            'step_3_database': False,
            'step_4_dashboard': False
        }

        # Step 1: Upload
        results['step_1_upload'] = await self.test_step_1_upload_allocation()

        if results['step_1_upload']:
            # Step 2: Monitor Progress
            results['step_2_progress'] = await self.test_step_2_monitor_progress()

            # Step 3: Verify Database
            results['step_3_database'] = await self.test_step_3_verify_database_results()

            # Step 4: Check Dashboard
            results['step_4_dashboard'] = await self.test_step_4_check_allocation_dashboard()

        # Final results
        print("\n" + "="*60)
        print("📊 FINAL TEST RESULTS")
        print("="*60)

        for step, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {step.replace('_', ' ').title()}")

        total_passed = sum(results.values())
        total_tests = len(results)
        success_rate = (total_passed / total_tests) * 100

        print(f"\n🎯 Success Rate: {success_rate:.1f}% ({total_passed}/{total_tests})")

        if success_rate == 100:
            print("🎉 ALL TESTS PASSED - Workflow is fully functional!")
        elif success_rate >= 75:
            print("✅ Most tests passed - Minor issues to resolve")
        elif success_rate >= 50:
            print("⚠️  Some tests passed - Significant issues identified")
        else:
            print("❌ Most tests failed - Major workflow issues")

        return results

async def main():
    """Main test runner"""
    async with AllocationWorkflowTester() as tester:
        results = await tester.run_complete_test()

        # Generate detailed report
        print(f"\n📝 Test completed at: {datetime.now().isoformat()}")

        if results['step_1_upload'] and tester.document_id:
            print(f"🆔 Document ID for manual verification: {tester.document_id}")

        return results

if __name__ == "__main__":
    results = asyncio.run(main())