"""
Test script for AI client and NMTC agents integration
Run this to verify your OpenAI setup and agent functionality
"""

import os
import sys
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_client import get_ai_client, AIProvider, AIClientError
from app.services.nmtc_agents import process_nmtc_document

# Sample allocation agreement text for testing
SAMPLE_DOCUMENT_TEXT = """
ALLOCATION AGREEMENT

Community Development Entity: ABC Capital Development Corp
Allocation Year: 2024
Total Allocation Amount: $5,200,000

Date: January 15, 2024

This Allocation Agreement ("Agreement") is entered into between the Community Development
Financial Institutions Fund ("CDFIS Fund") and ABC Capital Development Corp ("CDE").

TERMS AND CONDITIONS:

1. ALLOCATION AMOUNT
The CDE is hereby allocated New Markets Tax Credits in the amount of Five Million Two
Hundred Thousand Dollars ($5,200,000) for the 2024 allocation year.

2. QUALIFIED LOW-INCOME COMMUNITY INVESTMENT (QLICI) REQUIREMENTS
The CDE must invest substantially all of the allocation amount in Qualified Low-Income
Community Investments within 12 months of the allocation date.

Minimum QLICI loan amount: $100,000
Maximum QLICI loan amount: $2,000,000
Interest rate: Minimum 2% below market rate
Loan term: Minimum 5 years

3. GEOGRAPHIC FOCUS
The CDE must focus investments in qualified low-income communities within the following areas:
- Detroit, Michigan Metropolitan Area
- Rural counties in Michigan with poverty rates exceeding 20%

4. COMPLIANCE REQUIREMENTS
- Annual reporting deadline: March 31st of each year
- Annual compliance certification required
- On-site monitoring by CDFIS Fund staff
- Penalty for non-compliance: Potential recapture of tax credits

5. COMMUNITY IMPACT REQUIREMENTS
Target population: Low-income individuals and families
Job creation requirement: Minimum 50 full-time equivalent jobs
Community benefits: Affordable housing, community facilities, and small business development

6. CDE OBLIGATIONS
Capital deployment timeline: 100% within 12 months
Asset management: Professional management of QLICI loans required
Reporting: Quarterly progress reports and annual compliance reports
Recapture provisions: Credits subject to recapture for 7 years

This Agreement shall be governed by federal regulations and CDFIS Fund policies.

Signed this 15th day of January, 2024.

ABC Capital Development Corp
Community Development Entity
"""

def test_ai_client():
    """Test the AI client functionality"""
    print("🤖 Testing AI Client Setup...")
    print("-" * 50)

    try:
        # Test OpenAI client
        client = get_ai_client(AIProvider.OPENAI)
        print(f"✅ AI Client initialized: {client.provider_name}")

        # Simple test request
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Hello! Respond with just 'AI client working'"}],
            model="gpt-3.5-turbo",
            max_tokens=10
        )

        print(f"✅ AI Response: {response.content}")
        print(f"✅ Tokens used: {response.usage.total_tokens}")
        print(f"✅ Response time: {response.response_time_seconds:.2f}s")

        return True

    except AIClientError as e:
        print(f"❌ AI Client Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

def test_nmtc_agents():
    """Test the NMTC agents processing pipeline"""
    print("\n📋 Testing NMTC Agents Pipeline...")
    print("-" * 50)

    try:
        # Process the sample document
        print("🔄 Processing sample allocation agreement...")
        results = process_nmtc_document(SAMPLE_DOCUMENT_TEXT)

        # Check results
        print(f"\n📊 Processing Results:")
        print(f"Agents completed: {len([r for r in results.values() if hasattr(r, 'success')])}")

        # Agent 1: Classification
        if 'classification' in results:
            classification = results['classification']
            print(f"\n🔍 Agent 1 - Classification:")
            print(f"  Success: {'✅' if classification.success else '❌'}")
            print(f"  Confidence: {classification.confidence_score:.2f}")
            print(f"  Processing time: {classification.processing_time_seconds:.2f}s")

            if classification.success:
                data = classification.data
                print(f"  CDE Name: {data.get('cde_name', 'Not found')}")
                print(f"  Allocation Year: {data.get('allocation_year', 'Not found')}")
                print(f"  Total Amount: ${data.get('total_allocation_amount', 'Not found'):,}")

        # Agent 2: Extraction
        if 'extraction' in results:
            extraction = results['extraction']
            print(f"\n📝 Agent 2 - Data Extraction:")
            print(f"  Success: {'✅' if extraction.success else '❌'}")
            print(f"  Confidence: {extraction.confidence_score:.2f}")
            print(f"  Processing time: {extraction.processing_time_seconds:.2f}s")

            if extraction.success:
                data = extraction.data
                financial = data.get('financial_details', {})
                print(f"  Max QLICI: ${financial.get('maximum_qlici_loan_amount', 'Not found'):,}")
                print(f"  Min QLICI: ${financial.get('minimum_qlici_loan_amount', 'Not found'):,}")

        # Agent 3: Analysis
        if 'analysis' in results:
            analysis = results['analysis']
            print(f"\n🎯 Agent 3 - Compliance Analysis:")
            print(f"  Success: {'✅' if analysis.success else '❌'}")
            print(f"  Confidence: {analysis.confidence_score:.2f}")
            print(f"  Processing time: {analysis.processing_time_seconds:.2f}s")

            if analysis.success:
                data = analysis.data
                risk = data.get('risk_assessment', {})
                print(f"  Risk Score: {risk.get('overall_risk_score', 'Not found')}/10")
                success_prob = data.get('success_probability', {})
                print(f"  Success Probability: {success_prob.get('overall_success_probability', 0):.1%}")

        # Pipeline summary
        if 'pipeline_summary' in results:
            summary = results['pipeline_summary']
            print(f"\n⏱️  Pipeline Summary:")
            print(f"  Total time: {summary['total_processing_time']:.2f}s")
            print(f"  Success rate: {summary['agents_successful']}/3 agents")
            print(f"  Overall success: {'✅' if summary['overall_success'] else '❌'}")

        return True

    except Exception as e:
        print(f"❌ NMTC Agents Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 NMTC Platform AI Integration Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print()

    # Check environment
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please copy .env.example to .env and add your OpenAI API key")
        return

    # Run tests
    ai_test_passed = test_ai_client()

    if ai_test_passed:
        agents_test_passed = test_nmtc_agents()

        print("\n" + "=" * 60)
        if ai_test_passed and agents_test_passed:
            print("🎉 ALL TESTS PASSED! Your AI integration is working correctly.")
            print("\nNext steps:")
            print("1. ✅ AI client is configured and working")
            print("2. ✅ NMTC agents are processing documents")
            print("3. 🔄 Ready to implement workflow orchestration")
            print("\nTo switch to Azure OpenAI later:")
            print("- Set AI_PROVIDER=azure_openai in .env")
            print("- Add AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT")
        else:
            print("❌ Some tests failed. Please check the errors above.")
    else:
        print("\n❌ AI client test failed. Cannot proceed to agent testing.")
        print("Please check your OpenAI API key and internet connection.")

if __name__ == "__main__":
    main()