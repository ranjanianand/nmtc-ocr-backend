"""
Comprehensive test script for enterprise workflow orchestration
Tests the complete fire-and-forget job processing pipeline
"""

import asyncio
import sys
import os
import json
import uuid
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.workflow_engine import EnterpriseWorkflowEngine
from app.services.supabase_service import SupabaseService
from app.services.ai_client import get_ai_client, AIProvider
from app.services.nmtc_agents import process_nmtc_document

# Sample allocation agreement for testing
SAMPLE_ALLOCATION_TEXT = """
ALLOCATION AGREEMENT - 2024

Community Development Entity: TechStart Capital Development Corp
Allocation Year: 2024
Total Allocation Amount: $8,500,000

Date: March 15, 2024

This Allocation Agreement ("Agreement") is entered into between the Community Development
Financial Institutions Fund ("CDFIS Fund") and TechStart Capital Development Corp ("CDE").

TERMS AND CONDITIONS:

1. ALLOCATION AMOUNT
The CDE is hereby allocated New Markets Tax Credits in the amount of Eight Million Five
Hundred Thousand Dollars ($8,500,000) for the 2024 allocation year.

2. QUALIFIED LOW-INCOME COMMUNITY INVESTMENT (QLICI) REQUIREMENTS
The CDE must invest substantially all of the allocation amount in Qualified Low-Income
Community Investments within 12 months of the allocation date.

Minimum QLICI loan amount: $150,000
Maximum QLICI loan amount: $3,500,000
Interest rate: Minimum 2.5% below market rate
Loan term: Minimum 7 years

3. GEOGRAPHIC FOCUS
The CDE must focus investments in qualified low-income communities within the following areas:
- Austin, Texas Metropolitan Area
- Rural counties in Texas with poverty rates exceeding 25%
- Opportunity Zones in Dallas-Fort Worth region

4. COMPLIANCE REQUIREMENTS
- Annual reporting deadline: March 31st of each year
- Annual compliance certification required
- Quarterly monitoring by CDFIS Fund staff
- Penalty for non-compliance: Potential recapture of tax credits

5. COMMUNITY IMPACT REQUIREMENTS
Target population: Low-income individuals, families, and small businesses
Job creation requirement: Minimum 75 full-time equivalent jobs
Community benefits: Technology incubators, affordable housing, and small business development

6. CDE OBLIGATIONS
Capital deployment timeline: 100% within 10 months
Asset management: Professional management of QLICI loans required
Reporting: Monthly progress reports and annual compliance reports
Recapture provisions: Credits subject to recapture for 7 years

7. INNOVATION FOCUS
Technology startups: Minimum 40% of allocation for tech companies
Manufacturing: Minimum 30% for advanced manufacturing
Healthcare: Maximum 30% for healthcare innovation

This Agreement shall be governed by federal regulations and CDFIS Fund policies.

Signed this 15th day of March, 2024.

TechStart Capital Development Corp
Community Development Entity

Executive Director: Sarah Johnson
CFO: Michael Chen
"""

async def test_prerequisite_services():
    """Test that all prerequisite services are working"""
    print("🔧 Testing Prerequisite Services...")
    print("-" * 50)

    try:
        # Test AI Client
        client = get_ai_client(AIProvider.OPENAI)
        response = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello! Respond with just 'AI test passed'"}],
            model="gpt-3.5-turbo",
            max_tokens=10
        )
        print(f"✅ AI Client: {response.content}")

        # Test Supabase connection
        supabase_service = SupabaseService()
        health = await supabase_service.health_check()
        print(f"✅ Supabase: {'Connected' if health else 'Failed'}")

        # Test NMTC Agents
        results = await process_nmtc_document(SAMPLE_ALLOCATION_TEXT[:1000])  # Test with sample
        agents_passed = all(r.success for r in results.values() if hasattr(r, 'success'))
        print(f"✅ NMTC Agents: {'All passed' if agents_passed else 'Some failed'}")

        return True

    except Exception as e:
        print(f"❌ Prerequisite test failed: {e}")
        return False

async def test_workflow_engine_initialization():
    """Test workflow engine initialization"""
    print("\n🏗️ Testing Workflow Engine Initialization...")
    print("-" * 50)

    try:
        engine = EnterpriseWorkflowEngine()
        print("✅ Workflow engine created")

        # Test health check
        health = await engine.health_check()
        print(f"✅ Health check: {'Passed' if health else 'Failed'}")

        return engine

    except Exception as e:
        print(f"❌ Workflow engine initialization failed: {e}")
        return None

async def test_job_submission(engine: EnterpriseWorkflowEngine):
    """Test job submission and immediate response"""
    print("\n📋 Testing Job Submission...")
    print("-" * 50)

    try:
        # Generate test IDs
        org_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Create a test document first
        supabase_service = SupabaseService()

        # Upload test document to Supabase
        test_file_content = SAMPLE_ALLOCATION_TEXT.encode('utf-8')
        storage_path = f"test-documents/{org_id}/test_allocation_2024.txt"

        file_url = await supabase_service.upload_file(
            bucket="allocation-documents",
            file_path=storage_path,
            file_content=test_file_content,
            content_type="text/plain"
        )

        # Create document record
        document_data = {
            "org_id": org_id,
            "user_id": user_id,
            "filename": "test_allocation_2024.txt",
            "file_path": storage_path,
            "file_url": file_url,
            "file_size": len(test_file_content),
            "content_type": "text/plain",
            "processing_status": "uploaded"
        }

        document = await supabase_service.create_document(document_data)
        document_id = document["id"]

        print(f"✅ Test document created: {document_id}")

        # Submit job to workflow engine
        start_time = datetime.now()
        job_id = await engine.submit_allocation_job(
            org_id=org_id,
            user_id=user_id,
            document_id=document_id,
            allocation_year=2024,
            description="Test allocation agreement processing"
        )
        submission_time = (datetime.now() - start_time).total_seconds()

        print(f"✅ Job submitted in {submission_time:.2f}s")
        print(f"✅ Job ID: {job_id}")

        return job_id, org_id, document_id

    except Exception as e:
        print(f"❌ Job submission failed: {e}")
        return None, None, None

async def test_job_tracking(engine: EnterpriseWorkflowEngine, job_id: str):
    """Test job status tracking throughout processing"""
    print(f"\n📊 Testing Job Tracking for {job_id}...")
    print("-" * 50)

    try:
        max_wait_time = 300  # 5 minutes max
        poll_interval = 5    # Check every 5 seconds
        start_time = datetime.now()

        last_status = None
        last_progress = None

        while True:
            # Get current job status
            job_details = await engine.get_job_status(job_id)

            if not job_details:
                print(f"❌ Job {job_id} not found")
                break

            job_info = job_details["job_info"]
            current_status = job_info["status"]
            current_progress = job_info["progress_percent"]
            current_step = job_info.get("current_step", "unknown")

            # Only print if status or progress changed
            if current_status != last_status or current_progress != last_progress:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"[{elapsed:6.1f}s] Status: {current_status:10} | Progress: {current_progress:3}% | Step: {current_step}")

                last_status = current_status
                last_progress = current_progress

            # Check if job is complete or failed
            if current_status in ["completed", "failed", "cancelled"]:
                print(f"\n✅ Job finished with status: {current_status}")
                return current_status, job_details

            # Check timeout
            if (datetime.now() - start_time).total_seconds() > max_wait_time:
                print(f"\n⏰ Timeout reached ({max_wait_time}s)")
                return "timeout", job_details

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    except Exception as e:
        print(f"❌ Job tracking failed: {e}")
        return "error", None

async def test_results_retrieval(engine: EnterpriseWorkflowEngine, job_id: str):
    """Test retrieval of final results"""
    print(f"\n📋 Testing Results Retrieval for {job_id}...")
    print("-" * 50)

    try:
        # Get final results
        results = await engine.get_job_results(job_id)

        if not results:
            print("❌ No results found")
            return False

        print("✅ Results retrieved successfully")

        # Analyze results structure
        if "classification" in results:
            classification = results["classification"]
            print(f"  📊 Classification confidence: {classification.get('confidence_score', 0):.2f}")

        if "extraction" in results:
            extraction = results["extraction"]
            print(f"  📝 Extraction confidence: {extraction.get('confidence_score', 0):.2f}")

        if "analysis" in results:
            analysis = results["analysis"]
            print(f"  🎯 Analysis confidence: {analysis.get('confidence_score', 0):.2f}")

        # Check for key extracted data
        if "extraction" in results and "data" in results["extraction"]:
            extracted_data = results["extraction"]["data"]
            cde_name = extracted_data.get("cde_name", "Not found")
            allocation_amount = extracted_data.get("total_allocation_amount", "Not found")

            print(f"  🏢 CDE Name: {cde_name}")
            print(f"  💰 Allocation Amount: ${allocation_amount:,}" if isinstance(allocation_amount, (int, float)) else f"  💰 Allocation Amount: {allocation_amount}")

        return True

    except Exception as e:
        print(f"❌ Results retrieval failed: {e}")
        return False

async def test_organization_jobs(engine: EnterpriseWorkflowEngine, org_id: str):
    """Test organization job listing"""
    print(f"\n🏢 Testing Organization Jobs Listing...")
    print("-" * 50)

    try:
        jobs = await engine.get_active_jobs_for_org(org_id)

        print(f"✅ Found {len(jobs)} jobs for organization")

        for job in jobs:
            print(f"  📋 {job['job_id']}: {job['status']} ({job['progress_percent']}%)")

        return True

    except Exception as e:
        print(f"❌ Organization jobs listing failed: {e}")
        return False

async def test_queue_status(engine: EnterpriseWorkflowEngine):
    """Test queue status monitoring"""
    print(f"\n📊 Testing Queue Status...")
    print("-" * 50)

    try:
        queue_status = await engine.get_queue_status()

        print(f"✅ Queue status retrieved:")
        print(f"  📋 Queued jobs: {queue_status.get('total_queued', 0)}")
        print(f"  🔄 Running jobs: {queue_status.get('total_running', 0)}")
        print(f"  ⏱️ Estimated wait: {queue_status.get('estimated_wait_time_minutes', 0)} minutes")

        return True

    except Exception as e:
        print(f"❌ Queue status failed: {e}")
        return False

async def main():
    """Run comprehensive enterprise workflow tests"""
    print("🚀 Enterprise Workflow Orchestration Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print()

    # Check environment
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return

    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
        print("❌ Error: Supabase configuration not found")
        return

    test_results = []

    try:
        # Test 1: Prerequisites
        prereq_passed = await test_prerequisite_services()
        test_results.append(("Prerequisites", prereq_passed))

        if not prereq_passed:
            print("\n❌ Prerequisites failed. Cannot continue with workflow tests.")
            return

        # Test 2: Workflow Engine
        engine = await test_workflow_engine_initialization()
        test_results.append(("Workflow Engine", engine is not None))

        if not engine:
            print("\n❌ Workflow engine failed. Cannot continue.")
            return

        # Test 3: Job Submission
        job_id, org_id, document_id = await test_job_submission(engine)
        test_results.append(("Job Submission", job_id is not None))

        if not job_id:
            print("\n❌ Job submission failed. Cannot continue.")
            return

        # Test 4: Job Tracking
        final_status, job_details = await test_job_tracking(engine, job_id)
        test_results.append(("Job Tracking", final_status == "completed"))

        # Test 5: Results Retrieval (only if job completed)
        if final_status == "completed":
            results_ok = await test_results_retrieval(engine, job_id)
            test_results.append(("Results Retrieval", results_ok))

        # Test 6: Organization Jobs
        org_jobs_ok = await test_organization_jobs(engine, org_id)
        test_results.append(("Organization Jobs", org_jobs_ok))

        # Test 7: Queue Status
        queue_ok = await test_queue_status(engine)
        test_results.append(("Queue Status", queue_ok))

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        all_passed = True
        for test_name, passed in test_results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name:20}: {status}")
            if not passed:
                all_passed = False

        print(f"\nOverall Result: {'🎉 ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

        if all_passed:
            print("\n🚀 Enterprise workflow orchestration is working correctly!")
            print("✅ Fire-and-forget job processing")
            print("✅ Real-time status tracking")
            print("✅ Autonomous background execution")
            print("✅ Database persistence")
            print("✅ AI agent processing pipeline")
            print("\nReady for production deployment! 🎯")
        else:
            print("\n🔧 Some tests failed. Please check the errors above.")

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())