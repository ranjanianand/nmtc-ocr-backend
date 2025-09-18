#!/usr/bin/env python3
"""
Test AI Service OpenAI Integration
Simple test to verify that the OpenAI API integration is working correctly
"""

import asyncio
import json
from app.services.ai_service import ai_service

async def test_openai_integration():
    """Test the OpenAI integration with real API calls"""
    print("=== AI SERVICE OPENAI INTEGRATION TEST ===")
    print(f"Provider: {ai_service.provider}")
    print(f"Mock Mode: {ai_service.mock_mode}")
    print(f"Has API Key: {ai_service._has_api_key()}")
    print()

    # Test data (mock extracted document data)
    test_extracted_data = {
        'allocation_amount': {
            'extracted_value': '$10,000,000',
            'confidence_score': 0.95
        },
        'service_area': {
            'extracted_value': 'Los Angeles County, California',
            'confidence_score': 0.88
        },
        'qei_deadline': {
            'extracted_value': 'December 31, 2024',
            'confidence_score': 0.92
        }
    }

    # Test agent prompts (similar to what's in database)
    test_agent_prompts = [
        {
            'agent_key': 'document_analyzer',
            'system_prompt': 'You are an expert NMTC document analyzer. Analyze the document data and provide insights about completeness, quality, and compliance.',
            'prompt_text': '''Analyze the following NMTC allocation agreement data:

{extracted_data}

Please provide:
1. Document completeness assessment
2. Data quality score (0-100)
3. Compliance status
4. Any missing information
5. Recommendations for next steps

Format your response as JSON with the structure:
{
    "document_completeness": "HIGH|MEDIUM|LOW",
    "data_quality_score": 0-100,
    "compliance_assessment": "COMPLIANT|NON_COMPLIANT|NEEDS_REVIEW",
    "missing_information": [],
    "recommendations": []
}'''
        },
        {
            'agent_key': 'risk_assessor',
            'system_prompt': 'You are a NMTC compliance risk assessor. Evaluate potential risks and compliance issues.',
            'prompt_text': '''Assess the NMTC compliance risks for this allocation agreement:

{extracted_data}

Provide a risk assessment including:
1. Overall risk level
2. Risk score (0-100, where 100 is highest risk)
3. Identified risks
4. Mitigation recommendations

Format as JSON:
{
    "overall_risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "risk_score": 0-100,
    "identified_risks": [],
    "mitigation_recommendations": []
}'''
        }
    ]

    # Test each agent prompt
    for i, agent_prompt in enumerate(test_agent_prompts, 1):
        agent_key = agent_prompt['agent_key']
        print(f"=== TEST {i}: {agent_key.upper()} ===")

        try:
            print(f"Calling agent: {agent_key}")
            result = await ai_service.apply_agent_prompt(test_extracted_data, agent_prompt)

            print(f"Success: {result.get('success', False)}")

            if result.get('success'):
                print("Agent Response:")
                # Remove agent_metadata for cleaner output
                response_copy = result.copy()
                response_copy.pop('agent_metadata', None)
                print(json.dumps(response_copy, indent=2))

                # Show metadata separately
                if 'agent_metadata' in result:
                    metadata = result['agent_metadata']
                    print(f"Model Used: {metadata.get('model_used', 'unknown')}")
                    print(f"Response Length: {metadata.get('llm_response_length', 0)} characters")
            else:
                print("Failed!")
                print(json.dumps(result, indent=2))

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        print()

    print("=== SUMMARY ===")
    if ai_service.mock_mode:
        print("⚠️  AI Service is in MOCK mode - not using real OpenAI API")
        print("   Check your OPENAI_API_KEY configuration in .env file")
    elif not ai_service._has_api_key():
        print("❌ No API key configured")
        print("   Please set OPENAI_API_KEY in your .env file")
    else:
        print("✅ AI Service configured for OpenAI integration")
        print("   Real LLM calls should be working")

if __name__ == "__main__":
    asyncio.run(test_openai_integration())