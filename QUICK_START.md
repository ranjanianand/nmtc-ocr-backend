# NMTC Platform - AI Integration Quick Start

## 🚀 What We've Built

You now have a **plug-and-play AI architecture** that gives you:

✅ **Generic AI Client** - Switch between OpenAI and Azure OpenAI with just environment variables
✅ **3 NMTC Agents** - Document classification, data extraction, and compliance analysis
✅ **Database Schema** - Enterprise workflow orchestration ready
✅ **Test Suite** - Verify everything works before building more

## 🛠️ Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install openai python-dotenv
```

### 2. Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# AI_PROVIDER=openai
# OPENAI_API_KEY=sk-proj-your-key-here
```

### 3. Test AI Integration
```bash
# Run the test script
python test_ai_integration.py
```

**Expected Output:**
```
🚀 NMTC Platform AI Integration Test
✅ AI Client initialized: openai
✅ AI Response: AI client working
🔍 Agent 1 - Classification: ✅ Success
📝 Agent 2 - Data Extraction: ✅ Success
🎯 Agent 3 - Compliance Analysis: ✅ Success
🎉 ALL TESTS PASSED!
```

## 🔄 Switch to Azure OpenAI (Enterprise Ready)

When you're ready for enterprise compliance:

1. **Update .env**:
```env
AI_PROVIDER=azure_openai
AZURE_OPENAI_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

2. **Test again**:
```bash
python test_ai_integration.py
```

**That's it!** Same agents, same results, enterprise compliance.

## 📋 Usage Examples

### Simple Agent Usage
```python
from app.services.nmtc_agents import process_nmtc_document

# Process any allocation agreement text
results = process_nmtc_document(document_text)

# Get classification results
classification = results['classification']
print(f"CDE: {classification.data['cde_name']}")
print(f"Amount: ${classification.data['total_allocation_amount']:,}")

# Get extracted data
extraction = results['extraction']
financial = extraction.data['financial_details']
print(f"Max QLICI: ${financial['maximum_qlici_loan_amount']:,}")

# Get compliance analysis
analysis = results['analysis']
risk_score = analysis.data['risk_assessment']['overall_risk_score']
print(f"Risk Score: {risk_score}/10")
```

### Generic AI Client Usage
```python
from app.services.ai_client import get_ai_client

# Works with any configured provider
client = get_ai_client()
response = client.chat_completion([
    {"role": "user", "content": "Analyze this NMTC document..."}
])

print(response.content)
print(f"Provider: {response.provider}")
print(f"Tokens: {response.usage.total_tokens}")
```

## 🗄️ Database Setup (Optional)

To enable workflow orchestration:

1. **Apply schema**:
```bash
# Run against your PostgreSQL database
psql -d your_database -f database/enterprise_workflow_schema.sql
```

2. **Update .env**:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/nmtc_db
```

## 🎯 What's Next

Your foundation is ready! Now you can:

1. **Test the agents** with real allocation documents
2. **Integrate with your existing FastAPI endpoints**
3. **Build the workflow orchestration engine** for fire-and-forget processing
4. **Add the frontend job monitoring** components

## 🔧 Architecture Benefits

**Plug-and-Play Design:**
- Change AI providers with 1 environment variable
- Same interface for OpenAI, Azure OpenAI, future providers
- Zero code changes needed for migration

**Enterprise Ready:**
- Comprehensive error handling and logging
- Confidence scoring for all agent results
- Structured JSON responses for reliable parsing
- Performance metrics and usage tracking

**Developer Friendly:**
- Clear separation of concerns
- Easy to test and debug
- Extensible for new document types
- Well-documented with examples

## 📞 Next Steps

Run the test script and let me know the results! Once confirmed working, we can proceed with:

1. **Core Workflow Engine** - Fire-and-forget job processing
2. **Background Processing Service** - Autonomous document processing
3. **Frontend Integration** - Real-time job monitoring

**You now have enterprise-grade AI processing that's ready to scale!** 🚀