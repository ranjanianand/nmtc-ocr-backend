"""
NMTC Document Processing Agents
Enterprise-grade AI agents for allocation agreement analysis
"""

from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from datetime import datetime
import json

from .ai_client import get_ai_client, AIClientError

logger = logging.getLogger(__name__)

@dataclass
class AgentResult:
    agent_name: str
    success: bool
    data: Dict[str, Any]
    confidence_score: float
    processing_time_seconds: float
    timestamp: str
    errors: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "success": self.success,
            "data": self.data,
            "confidence_score": self.confidence_score,
            "processing_time_seconds": self.processing_time_seconds,
            "timestamp": self.timestamp,
            "errors": self.errors or []
        }

class NMTCAgentError(Exception):
    """Base exception for NMTC agent errors"""
    pass

class BaseNMTCAgent:
    """Base class for all NMTC processing agents"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
        self.ai_client = get_ai_client()

    def process(self, document_text: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """
        Process document text and return structured results

        Args:
            document_text: Extracted text from allocation agreement
            context: Additional context from previous agents or metadata

        Returns:
            AgentResult with processed data and metadata
        """
        start_time = datetime.now()
        errors = []

        try:
            self.logger.info(f"Starting {self.agent_name} processing")

            # Validate input
            if not document_text or not document_text.strip():
                raise NMTCAgentError("Document text is empty")

            # Generate prompt
            prompt = self._build_prompt(document_text, context)

            # Call AI service
            ai_response = self.ai_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4",
                temperature=0.1  # Low temperature for consistent extraction
            )

            # Parse response
            parsed_data = self._parse_response(ai_response.content)

            # Calculate confidence score
            confidence_score = self._calculate_confidence(parsed_data, ai_response)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            result = AgentResult(
                agent_name=self.agent_name,
                success=True,
                data=parsed_data,
                confidence_score=confidence_score,
                processing_time_seconds=processing_time,
                timestamp=end_time.isoformat(),
                errors=errors
            )

            self.logger.info(f"{self.agent_name} completed successfully in {processing_time:.2f}s")
            return result

        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            error_msg = str(e)
            errors.append(error_msg)

            self.logger.error(f"{self.agent_name} failed: {error_msg}")

            return AgentResult(
                agent_name=self.agent_name,
                success=False,
                data={},
                confidence_score=0.0,
                processing_time_seconds=processing_time,
                timestamp=end_time.isoformat(),
                errors=errors
            )

    def _build_prompt(self, document_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build agent-specific prompt - to be implemented by subclasses"""
        raise NotImplementedError

    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        """Parse AI response into structured data - to be implemented by subclasses"""
        raise NotImplementedError

    def _calculate_confidence(self, parsed_data: Dict[str, Any], ai_response) -> float:
        """Calculate confidence score based on parsed data quality"""
        try:
            # Basic confidence calculation based on data completeness
            required_fields = self._get_required_fields()
            if not required_fields:
                return 0.8  # Default confidence if no required fields defined

            filled_fields = sum(1 for field in required_fields if parsed_data.get(field))
            confidence = filled_fields / len(required_fields)

            # Bonus for structured response
            if isinstance(parsed_data, dict) and len(parsed_data) > 0:
                confidence += 0.1

            return min(confidence, 1.0)
        except Exception:
            return 0.5

    def _get_required_fields(self) -> List[str]:
        """Get list of required fields for confidence calculation"""
        return []

class DocumentClassificationAgent(BaseNMTCAgent):
    """Agent 1: Document Classification and Structure Analysis"""

    def __init__(self):
        super().__init__("DocumentClassificationAgent")

    def _build_prompt(self, document_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        return f"""
You are an expert NMTC (New Markets Tax Credit) document analyst. Analyze the following allocation agreement document and classify its structure and type.

DOCUMENT TEXT:
{document_text[:10000]}...

ANALYSIS TASKS:
1. Identify the document type and CDE (Community Development Entity)
2. Extract basic document metadata
3. Determine the document structure and sections
4. Identify the allocation year and key dates
5. Extract total allocation amount

RESPONSE FORMAT (JSON):
{{
    "document_type": "allocation_agreement",
    "cde_name": "extracted CDE name",
    "allocation_year": "YYYY",
    "total_allocation_amount": "dollar amount as number",
    "document_structure": {{
        "has_cover_page": true/false,
        "has_terms_section": true/false,
        "has_compliance_section": true/false,
        "has_appendices": true/false,
        "total_pages_estimated": number
    }},
    "key_dates": {{
        "allocation_date": "YYYY-MM-DD or null",
        "compliance_period_start": "YYYY-MM-DD or null",
        "compliance_period_end": "YYYY-MM-DD or null"
    }},
    "document_quality": {{
        "text_clarity": "high/medium/low",
        "completeness": "complete/partial/incomplete",
        "scan_quality": "high/medium/low"
    }},
    "classification_confidence": 0.95
}}

Provide ONLY the JSON response, no additional text.
"""

    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        try:
            # Try to parse JSON directly
            return json.loads(response_content.strip())
        except json.JSONDecodeError:
            # Fallback: extract JSON from response
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response_content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"error": "Could not parse JSON response", "raw_response": response_content}

    def _get_required_fields(self) -> List[str]:
        return ["document_type", "cde_name", "allocation_year", "total_allocation_amount"]

class DataExtractionAgent(BaseNMTCAgent):
    """Agent 2: Detailed Data Extraction"""

    def __init__(self):
        super().__init__("DataExtractionAgent")

    def _build_prompt(self, document_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        # Use context from classification agent if available
        classification_data = context.get("classification", {}) if context else {}
        cde_name = classification_data.get("cde_name", "Unknown CDE")
        allocation_year = classification_data.get("allocation_year", "Unknown")

        return f"""
You are an expert NMTC data extraction specialist. Extract detailed information from this allocation agreement for {cde_name} (Year: {allocation_year}).

DOCUMENT TEXT:
{document_text[:15000]}...

EXTRACTION TASKS:
1. Extract financial information and allocation details
2. Identify QLICI loan requirements and parameters
3. Extract compliance requirements and deadlines
4. Identify community impact requirements
5. Extract CDE operational requirements

RESPONSE FORMAT (JSON):
{{
    "financial_details": {{
        "total_allocation": number,
        "maximum_qlici_loan_amount": number,
        "minimum_qlici_loan_amount": number,
        "interest_rate_requirements": "string description",
        "loan_term_requirements": "string description"
    }},
    "qlici_requirements": {{
        "qualified_business_criteria": ["list", "of", "criteria"],
        "geographic_restrictions": "string description",
        "job_creation_requirements": "string description",
        "business_type_restrictions": ["list", "of", "restrictions"]
    }},
    "compliance_requirements": {{
        "annual_reporting_deadline": "YYYY-MM-DD or description",
        "certification_requirements": ["list", "of", "certifications"],
        "monitoring_requirements": "string description",
        "penalty_provisions": "string description"
    }},
    "community_impact": {{
        "target_population": "string description",
        "geographic_focus": "string description",
        "impact_metrics": ["list", "of", "metrics"],
        "community_benefits": "string description"
    }},
    "cde_obligations": {{
        "capital_deployment_timeline": "string description",
        "asset_management_requirements": "string description",
        "reporting_obligations": "string description",
        "recapture_provisions": "string description"
    }},
    "extraction_confidence": 0.90
}}

Provide ONLY the JSON response, no additional text.
"""

    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        try:
            return json.loads(response_content.strip())
        except json.JSONDecodeError:
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response_content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"error": "Could not parse JSON response", "raw_response": response_content}

    def _get_required_fields(self) -> List[str]:
        return [
            "financial_details",
            "qlici_requirements",
            "compliance_requirements",
            "community_impact",
            "cde_obligations"
        ]

class ComplianceAnalysisAgent(BaseNMTCAgent):
    """Agent 3: Compliance Analysis and Risk Assessment"""

    def __init__(self):
        super().__init__("ComplianceAnalysisAgent")

    def _build_prompt(self, document_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        # Use context from previous agents
        classification_data = context.get("classification", {}) if context else {}
        extraction_data = context.get("extraction", {}) if context else {}

        cde_name = classification_data.get("cde_name", "Unknown CDE")
        allocation_year = classification_data.get("allocation_year", "Unknown")
        total_allocation = extraction_data.get("financial_details", {}).get("total_allocation", "Unknown")

        return f"""
You are an expert NMTC compliance analyst. Analyze this allocation agreement for {cde_name} (Year: {allocation_year}, Amount: ${total_allocation}) and assess compliance requirements and risks.

DOCUMENT TEXT:
{document_text[:15000]}...

ANALYSIS TASKS:
1. Identify critical compliance deadlines and milestones
2. Assess regulatory risk factors
3. Evaluate deployment timeline feasibility
4. Identify potential compliance challenges
5. Generate compliance recommendations

RESPONSE FORMAT (JSON):
{{
    "compliance_timeline": {{
        "critical_deadlines": [
            {{
                "deadline_type": "string",
                "date": "YYYY-MM-DD",
                "description": "string",
                "penalty_for_miss": "string"
            }}
        ],
        "deployment_milestones": [
            {{
                "milestone": "string",
                "target_date": "YYYY-MM-DD",
                "percentage_deployed": number,
                "requirements": "string"
            }}
        ]
    }},
    "risk_assessment": {{
        "high_risk_factors": ["list", "of", "high", "risks"],
        "medium_risk_factors": ["list", "of", "medium", "risks"],
        "low_risk_factors": ["list", "of", "low", "risks"],
        "overall_risk_score": number between 1-10,
        "risk_mitigation_priority": "string description"
    }},
    "compliance_recommendations": {{
        "immediate_actions": ["list", "of", "immediate", "actions"],
        "short_term_actions": ["list", "of", "short", "term", "actions"],
        "long_term_monitoring": ["list", "of", "monitoring", "activities"],
        "resource_requirements": "string description"
    }},
    "regulatory_considerations": {{
        "irs_requirements": ["list", "of", "IRS", "requirements"],
        "cdfis_requirements": ["list", "of", "CDFIS", "requirements"],
        "state_requirements": ["list", "of", "state", "requirements"],
        "local_requirements": ["list", "of", "local", "requirements"]
    }},
    "success_probability": {{
        "deployment_success_probability": number between 0-1,
        "compliance_success_probability": number between 0-1,
        "overall_success_probability": number between 0-1,
        "key_success_factors": ["list", "of", "success", "factors"]
    }},
    "analysis_confidence": 0.88
}}

Provide ONLY the JSON response, no additional text.
"""

    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        try:
            return json.loads(response_content.strip())
        except json.JSONDecodeError:
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response_content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"error": "Could not parse JSON response", "raw_response": response_content}

    def _get_required_fields(self) -> List[str]:
        return [
            "compliance_timeline",
            "risk_assessment",
            "compliance_recommendations",
            "regulatory_considerations",
            "success_probability"
        ]

class NMTCProcessingPipeline:
    """Orchestrates the 3-agent NMTC document processing pipeline"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.NMTCProcessingPipeline")
        self.classification_agent = DocumentClassificationAgent()
        self.extraction_agent = DataExtractionAgent()
        self.analysis_agent = ComplianceAnalysisAgent()

    def process_document(self, document_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, AgentResult]:
        """
        Process document through all 3 agents

        Args:
            document_text: Full extracted text from allocation agreement
            context: Additional context including allocation year configuration

        Returns:
            Dictionary with results from each agent
        """
        pipeline_start = datetime.now()
        results = {}

        try:
            self.logger.info("Starting NMTC processing pipeline")

            # Agent 1: Document Classification (with allocation year context)
            self.logger.info("Running Agent 1: Document Classification")
            classification_result = self.classification_agent.process(document_text, context)
            results["classification"] = classification_result

            if not classification_result.success:
                self.logger.error("Classification failed, stopping pipeline")
                return results

            # Agent 2: Data Extraction (with classification and allocation year context)
            self.logger.info("Running Agent 2: Data Extraction")
            extraction_context = {
                "classification": classification_result.data,
                **(context or {})  # Include allocation year configuration
            }
            extraction_result = self.extraction_agent.process(document_text, extraction_context)
            results["extraction"] = extraction_result

            if not extraction_result.success:
                self.logger.warning("Extraction failed, running analysis with limited context")

            # Agent 3: Compliance Analysis (with full context including allocation year)
            self.logger.info("Running Agent 3: Compliance Analysis")
            full_context = {
                "classification": classification_result.data,
                "extraction": extraction_result.data if extraction_result.success else {},
                **(context or {})  # Include allocation year configuration
            }
            analysis_result = self.analysis_agent.process(document_text, full_context)
            results["analysis"] = analysis_result

            pipeline_end = datetime.now()
            total_time = (pipeline_end - pipeline_start).total_seconds()

            self.logger.info(f"NMTC processing pipeline completed in {total_time:.2f}s")

            # Add pipeline summary
            results["pipeline_summary"] = {
                "total_processing_time": total_time,
                "agents_successful": sum(1 for r in results.values() if isinstance(r, AgentResult) and r.success),
                "overall_success": all(r.success for r in results.values() if isinstance(r, AgentResult)),
                "completion_timestamp": pipeline_end.isoformat()
            }

            return results

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            results["pipeline_error"] = str(e)
            return results

# Convenience function for simple usage
def process_nmtc_document(
    document_text: str,
    allocation_year: Optional[int] = None,
    document_types: Optional[List[Dict[str, Any]]] = None,
    required_sections: Optional[List[Dict[str, Any]]] = None,
    processing_instructions: Optional[Dict[str, Any]] = None
) -> Dict[str, AgentResult]:
    """
    Process NMTC allocation agreement through the complete 3-agent pipeline

    Args:
        document_text: Extracted text from allocation agreement
        allocation_year: The allocation year for context
        document_types: Expected document types configuration
        required_sections: Required sections configuration
        processing_instructions: Custom processing instructions

    Returns:
        Dictionary with results from classification, extraction, and analysis agents
    """
    pipeline = NMTCProcessingPipeline()

    # Build enhanced context from allocation year configuration
    context = {
        "allocation_year": allocation_year,
        "document_types": document_types or [],
        "required_sections": required_sections or [],
        "processing_instructions": processing_instructions or {}
    }

    return pipeline.process_document(document_text, context=context)

# Export main classes and functions
__all__ = [
    "AgentResult",
    "NMTCAgentError",
    "DocumentClassificationAgent",
    "DataExtractionAgent",
    "ComplianceAnalysisAgent",
    "NMTCProcessingPipeline",
    "process_nmtc_document"
]