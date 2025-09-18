#!/usr/bin/env python3
"""
Test the complete allocation agreement workflow:
1. Upload allocation agreement with auto-defaulted document type
2. Monitor progress through 6-stage pipeline
3. Verify dashboard auto-generation after completion
"""

import requests
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
ORG_ID = "test-org-id"
YEAR = 2024
TEST_PDF_PATH = "test_allocation_agreement.pdf"

def create_test_pdf():
    """Create a simple test PDF for upload"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    c = canvas.Canvas(TEST_PDF_PATH, pagesize=letter)
    c.drawString(100, 750, f"TREASURY ALLOCATION AGREEMENT - {YEAR}")
    c.drawString(100, 700, f"Community Development Entity: Test Organization")
    c.drawString(100, 650, f"Allocation Amount: $50,000,000")
    c.drawString(100, 600, f"Compliance Period: {YEAR} - {YEAR + 5}")
    c.drawString(100, 550, f"Geographic Targeting: Qualified census tracts")
    c.save()
    print(f"✅ Created test PDF: {TEST_PDF_PATH}")

def test_allocation_upload():
    """Test Step 1: Upload allocation agreement with auto-defaulted type"""
    print(f"\n🔄 Step 1: Uploading allocation agreement for {YEAR}...")

    url = f"{BASE_URL}/api/allocation-years/org/{ORG_ID}/year/{YEAR}/upload-allocation"

    with open(TEST_PDF_PATH, 'rb') as f:
        files = {'file': (TEST_PDF_PATH, f, 'application/pdf')}
        data = {'description': f'Test allocation agreement for {YEAR}'}

        response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   Document ID: {result['document_id']}")
        print(f"   Auto-defaulted type: {result['document_type']}")
        print(f"   Pipeline stages: {result['pipeline']['total_stages']}")
        print(f"   Current stage: {result['pipeline']['current_stage']}")
        return result['document_id']
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return None

def test_progress_tracking(document_id):
    """Test Step 2: Monitor progress through 6-stage pipeline"""
    print(f"\n🔄 Step 2: Monitoring processing pipeline...")

    url = f"{BASE_URL}/api/allocation-years/org/{ORG_ID}/year/{YEAR}/document/{document_id}/progress"

    max_attempts = 20  # Maximum 2 minutes of polling
    attempt = 0

    while attempt < max_attempts:
        response = requests.get(url)

        if response.status_code == 200:
            result = response.json()
            pipeline = result['pipeline']

            print(f"   Stage {pipeline['current_stage']}/{pipeline['total_stages']}: "
                  f"{pipeline['overall_progress']}% complete")

            # Print current stage details
            current_stage = next(
                (s for s in pipeline['stages'] if s['status'] == 'in_progress'),
                pipeline['stages'][pipeline['current_stage']-1]
            )
            print(f"   Current: {current_stage['name']} - {current_stage['description']}")

            if result['processing_complete']:
                print(f"✅ Processing completed! Dashboard ready.")
                print(f"   Next action: {result['next_action']}")
                return True

            print(f"   Estimated completion: {result['estimated_completion']}")

        else:
            print(f"❌ Progress check failed: {response.status_code}")

        attempt += 1
        time.sleep(6)  # Poll every 6 seconds

    print(f"❌ Processing did not complete within timeout")
    return False

def test_dashboard_generation():
    """Test Step 3: Verify dashboard auto-generation"""
    print(f"\n🔄 Step 3: Checking dashboard generation...")

    url = f"{BASE_URL}/api/allocation-years/org/{ORG_ID}/year/{YEAR}/dashboard"

    response = requests.get(url)

    if response.status_code == 200:
        result = response.json()

        if result.get('has_allocation_agreement'):
            print(f"✅ Dashboard generated successfully!")
            print(f"   Year: {result['year']}")
            print(f"   Total amount: ${result.get('total_amount', 0):,}")
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Has allocation agreement: {result['has_allocation_agreement']}")
            return True
        else:
            print(f"❌ Dashboard exists but no allocation agreement detected")
            return False
    else:
        print(f"❌ Dashboard generation failed: {response.status_code}")
        return False

def cleanup():
    """Clean up test files"""
    try:
        Path(TEST_PDF_PATH).unlink()
        print(f"🧹 Cleaned up test file: {TEST_PDF_PATH}")
    except:
        pass

def main():
    """Run the complete workflow test"""
    print("🧪 Testing Allocation Agreement Workflow")
    print("=" * 50)

    try:
        # Check if reportlab is available, if not, skip PDF creation
        try:
            create_test_pdf()
        except ImportError:
            print("⚠️  ReportLab not available, using placeholder PDF name")
            print("   Please ensure a test PDF file exists for upload")

        # Test upload
        document_id = test_allocation_upload()
        if not document_id:
            return False

        # Test progress tracking
        processing_success = test_progress_tracking(document_id)
        if not processing_success:
            return False

        # Test dashboard generation
        dashboard_success = test_dashboard_generation()
        if not dashboard_success:
            return False

        print("\n🎉 All tests passed! Allocation workflow is working correctly.")
        print("\nWorkflow Summary:")
        print("1. ✅ Auto-defaulted document type upload")
        print("2. ✅ 6-stage pipeline progress tracking")
        print("3. ✅ Automatic dashboard generation")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False

    finally:
        cleanup()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)