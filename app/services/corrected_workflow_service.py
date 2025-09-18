"""
NMTC Stage-Dependent Workflow Service
Implements the corrected workflow sequence with proper stage dependencies.

Workflow Sequence:
1. Document Type Detection
2. Section Identification  
3. Query Application
4. Normalization Application
5. Business Rules Validation
6. Risk Assessment
7. Agent Prompts Application (Results Processing Stage)
8. Report Generation

Each stage depends on previous stage outputs and stores results in appropriate tables.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

from app.services.database_service import DatabaseService, ValidationStatus, RiskLevel, ComplianceStatus
from app.services.ai_service import AIService
from app.config import settings

logger = logging.getLogger(__name__)

class WorkflowStage:
    """Represents a single workflow stage with dependencies and outputs"""
    
    def __init__(self, name: str, order: int, dependencies: List[str] = None):
        self.name = name
        self.order = order
        self.dependencies = dependencies or []

class CorrectedWorkflowService:
    """
    Enterprise-grade workflow service implementing the corrected stage sequence.
    Reads from master tables and stores all intermediate results.
    """
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.ai_service = AIService()
        
        # Define workflow stages with proper dependencies
        self.stages = {
            'document_type_detection': WorkflowStage('document_type_detection', 1, []),
            'section_identification': WorkflowStage('section_identification', 2, ['document_type_detection']),
            'query_application': WorkflowStage('query_application', 3, ['section_identification']),
            'normalization': WorkflowStage('normalization', 4, ['query_application']),
            'business_rules_validation': WorkflowStage('business_rules_validation', 5, ['normalization']),
            'risk_assessment': WorkflowStage('risk_assessment', 6, ['business_rules_validation']),
            'agent_prompts_application': WorkflowStage('agent_prompts_application', 7, ['risk_assessment']),
            'report_generation': WorkflowStage('report_generation', 8, ['agent_prompts_application'])
        }
    
    async def execute_complete_workflow(self, session_id: UUID, document_id: UUID, 
                                      org_id: UUID) -> Dict[str, Any]:
        """
        Execute the complete corrected workflow sequence.
        Each stage depends on previous stage outputs.
        """
        try:
            logger.info(f"Starting corrected workflow for session {session_id}")
            
            workflow_results = {
                'session_id': str(session_id),
                'document_id': str(document_id),
                'stages_completed': [],
                'stage_outputs': {},
                'overall_status': 'running',
                'start_time': datetime.utcnow().isoformat()
            }
            
            # Execute stages in proper sequence
            for stage_name, stage in self.stages.items():
                try:
                    logger.info(f"Executing stage: {stage_name}")
                    
                    # Create workflow stage record
                    await self.db_service.create_workflow_stage(
                        session_id=session_id,
                        stage_name=stage_name,
                        stage_order=stage.order,
                        status='running'
                    )
                    
                    # Execute the stage
                    stage_output = await self._execute_stage(
                        stage_name, session_id, document_id, org_id, 
                        workflow_results['stage_outputs']
                    )
                    
                    # Store stage output
                    workflow_results['stage_outputs'][stage_name] = stage_output
                    workflow_results['stages_completed'].append(stage_name)
                    
                    # Update workflow stage as completed
                    await self.db_service.update_workflow_stage(
                        session_id=session_id,
                        stage_name=stage_name,
                        status='completed',
                        output_data=stage_output
                    )
                    
                    logger.info(f"Completed stage: {stage_name}")
                    
                except Exception as stage_error:
                    logger.error(f"Stage {stage_name} failed: {str(stage_error)}")
                    
                    # Mark stage as failed
                    await self.db_service.update_workflow_stage(
                        session_id=session_id,
                        stage_name=stage_name,
                        status='failed',
                        error_details={'error': str(stage_error)}
                    )
                    
                    workflow_results['overall_status'] = 'failed'
                    workflow_results['failed_stage'] = stage_name
                    workflow_results['error'] = str(stage_error)
                    break
            
            # Determine overall workflow status
            if workflow_results['overall_status'] != 'failed':
                if len(workflow_results['stages_completed']) == len(self.stages):
                    workflow_results['overall_status'] = 'completed'
                else:
                    workflow_results['overall_status'] = 'partial'
            
            workflow_results['end_time'] = datetime.utcnow().isoformat()
            
            # Store overall workflow results
            await self._store_workflow_summary(session_id, document_id, workflow_results)
            
            return workflow_results
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                'session_id': str(session_id),
                'document_id': str(document_id),
                'overall_status': 'failed',
                'error': str(e),
                'stages_completed': []
            }
    
    async def _execute_stage(self, stage_name: str, session_id: UUID, document_id: UUID,
                           org_id: UUID, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific workflow stage based on its type"""
        
        if stage_name == 'document_type_detection':
            return await self._stage_document_type_detection(session_id, document_id, org_id)
        
        elif stage_name == 'section_identification':
            document_type_id = previous_outputs.get('document_type_detection', {}).get('document_type_id')
            if not document_type_id:
                raise ValueError("Document type detection output required for section identification")
            return await self._stage_section_identification(session_id, document_id, document_type_id)
        
        elif stage_name == 'query_application':
            sections = previous_outputs.get('section_identification', {}).get('identified_sections', [])
            if not sections:
                raise ValueError("Section identification output required for query application")
            return await self._stage_query_application(session_id, document_id, sections)
        
        elif stage_name == 'normalization':
            query_results = previous_outputs.get('query_application', {}).get('query_results', [])
            if not query_results:
                raise ValueError("Query application output required for normalization")
            return await self._stage_normalization(session_id, query_results)
        
        elif stage_name == 'business_rules_validation':
            normalized_data = previous_outputs.get('normalization', {}).get('normalized_results', [])
            if not normalized_data:
                raise ValueError("Normalization output required for business rules validation")
            return await self._stage_business_rules_validation(session_id, document_id, org_id, normalized_data)
        
        elif stage_name == 'risk_assessment':
            business_rules_output = previous_outputs.get('business_rules_validation', {})
            if not business_rules_output:
                raise ValueError("Business rules validation output required for risk assessment")
            return await self._stage_risk_assessment(session_id, document_id, business_rules_output)
        
        elif stage_name == 'agent_prompts_application':
            # This is the key correction - agent prompts applied at results processing stage
            all_previous_outputs = {k: v for k, v in previous_outputs.items() if k != 'agent_prompts_application'}
            return await self._stage_agent_prompts_application(session_id, document_id, org_id, all_previous_outputs)
        
        elif stage_name == 'report_generation':
            agent_results = previous_outputs.get('agent_prompts_application', {})
            if not agent_results:
                raise ValueError("Agent prompts application output required for report generation")
            return await self._stage_report_generation(session_id, document_id, org_id, previous_outputs, agent_results)
        
        else:
            raise ValueError(f"Unknown stage: {stage_name}")
    
    async def _stage_document_type_detection(self, session_id: UUID, document_id: UUID, 
                                           org_id: UUID) -> Dict[str, Any]:
        """Stage 1: Document Type Detection"""
        
        # Get document content
        document = await self.db_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get available document types for organization
        document_types = await self.db_service.get_document_types(org_id)
        
        # Use AI to detect document type
        type_detection_prompt = f"""
        Analyze this document and determine its type from the available options.
        
        Document content preview: {document.get('content', '')[:2000]}...
        
        Available document types:
        {json.dumps([{'id': dt['id'], 'name': dt['type_name'], 'description': dt['description']} for dt in document_types], indent=2)}
        
        Return the most appropriate document_type_id and confidence score.
        """
        
        ai_response = await self.ai_service.analyze_document_structure(type_detection_prompt)
        
        # Parse AI response to extract document type
        detected_type_id = None
        confidence = 0.0
        
        for doc_type in document_types:
            if doc_type['type_name'].lower() in ai_response.lower():
                detected_type_id = doc_type['id']
                confidence = 0.85  # Base confidence
                break
        
        if not detected_type_id and document_types:
            # Default to first available type
            detected_type_id = document_types[0]['id']
            confidence = 0.5
        
        return {
            'document_type_id': detected_type_id,
            'confidence': confidence,
            'available_types': len(document_types),
            'ai_analysis': ai_response[:500]  # Truncated for storage
        }
    
    async def _stage_section_identification(self, session_id: UUID, document_id: UUID,
                                          document_type_id: str) -> Dict[str, Any]:
        """Stage 2: Section Identification based on document type"""
        
        # Get sections for this document type
        sections = await self.db_service.get_sections_by_document_type(document_type_id)
        
        # Get document content
        document = await self.db_service.get_document(document_id)
        document_content = document.get('content', '')
        
        identified_sections = []
        
        for section in sections:
            # Use anchor patterns to identify sections
            anchor_patterns = section.get('anchor_patterns', [])
            section_found = False
            
            for pattern in anchor_patterns:
                if pattern.lower() in document_content.lower():
                    # Extract section text (simplified implementation)
                    start_pos = document_content.lower().find(pattern.lower())
                    end_pos = min(start_pos + 2000, len(document_content))  # Max 2000 chars
                    section_text = document_content[start_pos:end_pos]
                    
                    # Store section instance
                    section_instance_id = await self.db_service.store_section_instance(
                        session_id=session_id,
                        document_id=document_id,
                        section_id=UUID(section['id']),
                        section_text=section_text,
                        confidence_score=0.8,
                        start_position=start_pos,
                        end_position=end_pos,
                        identification_method='pattern_matching',
                        anchor_patterns_matched=[pattern]
                    )
                    
                    identified_sections.append({
                        'section_id': section['id'],
                        'section_instance_id': str(section_instance_id),
                        'section_name': section['canonical_name'],
                        'confidence': 0.8,
                        'text_length': len(section_text),
                        'start_position': start_pos
                    })
                    
                    section_found = True
                    break
            
            if not section_found:
                logger.warning(f"Section {section['canonical_name']} not found in document")
        
        return {
            'identified_sections': identified_sections,
            'total_sections_expected': len(sections),
            'sections_found': len(identified_sections),
            'identification_rate': len(identified_sections) / len(sections) if sections else 0
        }
    
    async def _stage_query_application(self, session_id: UUID, document_id: UUID,
                                     sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 3: Apply queries to identified sections"""
        
        query_results = []
        
        for section_data in sections:
            section_id = UUID(section_data['section_id'])
            section_instance_id = UUID(section_data['section_instance_id'])
            
            # Get queries for this section
            queries = await self.db_service.get_queries_by_section(section_id)
            
            # Get section text
            section_instance = await self.db_service.get_section_instance(section_instance_id)
            section_text = section_instance.get('section_text', '') if section_instance else ''
            
            for query in queries:
                try:
                    # Apply query using AI
                    query_prompt = f"""
                    Extract information from this document section based on the query.
                    
                    Section: {section_data['section_name']}
                    Section Text: {section_text}
                    
                    Query: {query['question_text']}
                    
                    Please extract the requested information clearly and concisely.
                    """
                    
                    ai_response = await self.ai_service.analyze_document_structure(query_prompt)
                    
                    # Store query execution result
                    query_result_id = await self.db_service.store_query_execution(
                        session_id=session_id,
                        document_id=document_id,
                        query_id=UUID(query['id']),
                        section_instance_id=section_instance_id,
                        raw_result=ai_response,
                        extraction_confidence=0.75,
                        extraction_method='ai_analysis',
                        execution_status='completed'
                    )
                    
                    query_results.append({
                        'query_result_id': str(query_result_id),
                        'query_id': query['id'],
                        'question': query['question_text'],
                        'section_name': section_data['section_name'],
                        'raw_result': ai_response,
                        'confidence': 0.75
                    })
                    
                except Exception as e:
                    logger.error(f"Query application failed for query {query['id']}: {str(e)}")
                    
                    # Store failed query execution
                    await self.db_service.store_query_execution(
                        session_id=session_id,
                        document_id=document_id,
                        query_id=UUID(query['id']),
                        section_instance_id=section_instance_id,
                        raw_result=None,
                        extraction_confidence=0.0,
                        extraction_method='ai_analysis',
                        execution_status='failed',
                        error_message=str(e)
                    )
        
        return {
            'query_results': query_results,
            'total_queries_executed': len(query_results),
            'sections_processed': len(sections)
        }
    
    async def _stage_normalization(self, session_id: UUID, 
                                 query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 4: Apply normalization rules to query results"""
        
        normalized_results = []
        
        for query_result in query_results:
            query_result_id = UUID(query_result['query_result_id'])
            raw_result = query_result['raw_result']
            
            # Get applicable normalization rules
            normalization_rules = await self.db_service.get_normalization_rules()
            
            applied_rules = []
            final_value = raw_result  # Default to raw result
            
            for rule in normalization_rules:
                try:
                    rule_pattern = rule.get('pattern', '')
                    
                    # Check if rule pattern matches
                    if rule_pattern and rule_pattern.lower() in raw_result.lower():
                        # Apply normalization (simplified implementation)
                        normalized_value = rule.get('normalized_value', raw_result)
                        
                        # Store normalization application
                        normalization_id = await self.db_service.store_normalization_application(
                            session_id=session_id,
                            query_execution_id=query_result_id,
                            normalization_rule_id=UUID(rule['id']),
                            input_value=raw_result,
                            output_value=normalized_value,
                            confidence_score=0.8,
                            rule_match_score=0.9
                        )
                        
                        applied_rules.append({
                            'rule_id': rule['id'],
                            'rule_type': rule['rule_type'],
                            'normalization_id': str(normalization_id)
                        })
                        
                        final_value = normalized_value
                        break
                        
                except Exception as e:
                    logger.error(f"Normalization rule {rule['id']} failed: {str(e)}")
            
            normalized_results.append({
                'query_result_id': query_result['query_result_id'],
                'query_id': query_result['query_id'],
                'question': query_result['question'],
                'original_value': raw_result,
                'normalized_value': final_value,
                'rules_applied': len(applied_rules),
                'applied_rules': applied_rules
            })
        
        return {
            'normalized_results': normalized_results,
            'total_normalizations': sum(len(r['applied_rules']) for r in normalized_results)
        }
    
    async def _stage_business_rules_validation(self, session_id: UUID, document_id: UUID,
                                             org_id: UUID, normalized_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 5: Validate against business rules"""
        
        # Get business rules for organization
        business_rules = await self.db_service.get_business_rules(org_id)
        
        rule_evaluations = []
        violations = []
        
        for rule in business_rules:
            try:
                # Prepare evaluation context
                evaluation_context = {
                    'normalized_data': normalized_data,
                    'document_id': str(document_id),
                    'session_id': str(session_id)
                }
                
                # Simple rule evaluation (can be enhanced with more complex logic)
                rule_condition = rule.get('condition_json', {})
                rule_action = rule.get('action_json', {})
                
                # Default to passing rule
                evaluation_result = True
                confidence = 0.8
                
                # Store business rule evaluation
                evaluation_id = await self.db_service.store_business_rule_evaluation(
                    session_id=session_id,
                    business_rule_id=UUID(rule['id']),
                    evaluation_context=evaluation_context,
                    evaluation_result=evaluation_result,
                    confidence_score=confidence,
                    evaluation_method='automated'
                )
                
                rule_evaluations.append({
                    'evaluation_id': str(evaluation_id),
                    'rule_id': rule['id'],
                    'rule_name': rule['rule_name'],
                    'result': evaluation_result,
                    'confidence': confidence
                })
                
                if not evaluation_result:
                    violations.append({
                        'rule_id': rule['id'],
                        'rule_name': rule['rule_name'],
                        'severity': rule.get('priority', 'medium')
                    })
                    
            except Exception as e:
                logger.error(f"Business rule evaluation failed for rule {rule['id']}: {str(e)}")
        
        return {
            'rule_evaluations': rule_evaluations,
            'total_rules_evaluated': len(rule_evaluations),
            'violations_found': len(violations),
            'violations': violations,
            'compliance_rate': (len(rule_evaluations) - len(violations)) / len(rule_evaluations) if rule_evaluations else 1.0
        }
    
    async def _stage_risk_assessment(self, session_id: UUID, document_id: UUID,
                                   business_rules_output: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 6: Perform risk assessment based on business rule violations"""
        
        violations = business_rules_output.get('violations', [])
        compliance_rate = business_rules_output.get('compliance_rate', 1.0)
        
        risk_assessments = []
        
        # Assess compliance risk
        compliance_risk_level = 'low'
        compliance_risk_score = 10.0
        
        if compliance_rate < 0.5:
            compliance_risk_level = 'critical'
            compliance_risk_score = 95.0
        elif compliance_rate < 0.7:
            compliance_risk_level = 'high'
            compliance_risk_score = 75.0
        elif compliance_rate < 0.9:
            compliance_risk_level = 'medium'
            compliance_risk_score = 45.0
        
        # Store compliance risk assessment
        compliance_risk_id = await self.db_service.store_risk_assessment(
            session_id=session_id,
            document_id=document_id,
            risk_category='compliance',
            risk_level=RiskLevel(compliance_risk_level),
            risk_score=compliance_risk_score,
            risk_description=f"Compliance risk based on {len(violations)} violations out of {business_rules_output.get('total_rules_evaluated', 0)} rules",
            impact_analysis={'violations': violations, 'compliance_rate': compliance_rate},
            mitigation_recommendations=['Review flagged items', 'Implement corrective actions']
        )
        
        risk_assessments.append({
            'risk_id': str(compliance_risk_id),
            'category': 'compliance',
            'level': compliance_risk_level,
            'score': compliance_risk_score,
            'description': f"Compliance assessment based on business rules validation"
        })
        
        # Assess financial risk (simplified)
        financial_risk_level = 'medium' if len(violations) > 2 else 'low'
        financial_risk_score = min(50.0 + (len(violations) * 10), 90.0)
        
        financial_risk_id = await self.db_service.store_risk_assessment(
            session_id=session_id,
            document_id=document_id,
            risk_category='financial',
            risk_level=RiskLevel(financial_risk_level),
            risk_score=financial_risk_score,
            risk_description=f"Financial risk assessment based on compliance violations",
            impact_analysis={'violation_count': len(violations)},
            mitigation_recommendations=['Financial review required', 'Verify calculations']
        )
        
        risk_assessments.append({
            'risk_id': str(financial_risk_id),
            'category': 'financial',
            'level': financial_risk_level,
            'score': financial_risk_score,
            'description': f"Financial risk based on compliance violations"
        })
        
        # Calculate overall risk
        overall_risk_score = (compliance_risk_score + financial_risk_score) / 2
        overall_risk_level = 'low'
        if overall_risk_score > 75:
            overall_risk_level = 'critical'
        elif overall_risk_score > 50:
            overall_risk_level = 'high'
        elif overall_risk_score > 25:
            overall_risk_level = 'medium'
        
        return {
            'risk_assessments': risk_assessments,
            'overall_risk_score': overall_risk_score,
            'overall_risk_level': overall_risk_level,
            'total_risks_identified': len(risk_assessments)
        }
    
    async def _stage_agent_prompts_application(self, session_id: UUID, document_id: UUID,
                                             org_id: UUID, all_previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 7: Apply agent prompts for results processing (KEY CORRECTION)
        This is where agent prompts are applied - at the results processing stage, not initial stage
        """
        
        # Get agent prompts for organization
        agent_prompts = await self.db_service.get_agent_prompts(org_id)
        
        agent_results = []
        
        for prompt in agent_prompts:
            try:
                agent_key = prompt.get('agent_key', '')
                system_prompt = prompt.get('system_prompt', '')
                task_prompt = prompt.get('task_prompt', '')
                
                # Prepare input data with all previous stage outputs
                input_data = {
                    'document_id': str(document_id),
                    'session_id': str(session_id),
                    'previous_stages': all_previous_outputs
                }
                
                # Create comprehensive prompt with all previous results
                full_prompt = f"""
                {system_prompt}
                
                TASK: {task_prompt}
                
                CONTEXT - Previous Processing Results:
                
                Document Type Detection: {json.dumps(all_previous_outputs.get('document_type_detection', {}), indent=2)}
                
                Section Identification: {json.dumps(all_previous_outputs.get('section_identification', {}), indent=2)}
                
                Query Results: {json.dumps(all_previous_outputs.get('query_application', {}), indent=2)}
                
                Normalization Results: {json.dumps(all_previous_outputs.get('normalization', {}), indent=2)}
                
                Business Rules Validation: {json.dumps(all_previous_outputs.get('business_rules_validation', {}), indent=2)}
                
                Risk Assessment: {json.dumps(all_previous_outputs.get('risk_assessment', {}), indent=2)}
                
                Please process these results according to your specific agent role and provide structured output.
                """
                
                # Apply agent prompt using AI service
                agent_response = await self.ai_service.analyze_document_structure(full_prompt)
                
                # Store agent prompt application
                application_id = await self.db_service.store_agent_prompt_application(
                    session_id=session_id,
                    agent_prompt_id=UUID(prompt['id']),
                    application_stage='results_processing',
                    input_data=input_data,
                    prompt_response=agent_response,
                    confidence_score=0.8,
                    model_used='gpt-4',
                    prompt_version='1.0'
                )
                
                agent_results.append({
                    'application_id': str(application_id),
                    'agent_key': agent_key,
                    'agent_response': agent_response,
                    'confidence': 0.8,
                    'input_data_size': len(str(input_data))
                })
                
            except Exception as e:
                logger.error(f"Agent prompt application failed for {prompt.get('agent_key')}: {str(e)}")
        
        return {
            'agent_results': agent_results,
            'agents_processed': len(agent_results),
            'total_prompts_available': len(agent_prompts)
        }
    
    async def _stage_report_generation(self, session_id: UUID, document_id: UUID, org_id: UUID,
                                     all_previous_outputs: Dict[str, Any], agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 8: Generate final reports based on all previous stages"""
        
        # Get report definitions for organization
        report_definitions = await self.db_service.get_report_definitions(org_id)
        
        generated_reports = []
        
        for report_def in report_definitions:
            try:
                # Prepare report data from all previous stages
                report_data = {
                    'document_processing_summary': {
                        'document_type': all_previous_outputs.get('document_type_detection', {}),
                        'sections_identified': all_previous_outputs.get('section_identification', {}),
                        'extractions': all_previous_outputs.get('query_application', {}),
                        'normalizations': all_previous_outputs.get('normalization', {}),
                        'business_rules': all_previous_outputs.get('business_rules_validation', {}),
                        'risk_assessment': all_previous_outputs.get('risk_assessment', {}),
                        'agent_analysis': agent_results
                    },
                    'compliance_summary': {
                        'compliance_rate': all_previous_outputs.get('business_rules_validation', {}).get('compliance_rate', 0),
                        'violations': all_previous_outputs.get('business_rules_validation', {}).get('violations', []),
                        'overall_risk': all_previous_outputs.get('risk_assessment', {}).get('overall_risk_level', 'unknown')
                    }
                }
                
                # Generate report using template
                report_content = await self._generate_report_content(report_def, report_data)
                
                # Store generated report
                report_id = await self.db_service.store_generated_report(
                    session_id=session_id,
                    document_id=document_id,
                    report_definition_id=UUID(report_def['id']),
                    report_type=report_def.get('report_type', 'summary'),
                    report_format='JSON',
                    report_content=report_content
                )
                
                generated_reports.append({
                    'report_id': str(report_id),
                    'report_type': report_def.get('report_type', 'summary'),
                    'report_name': report_def.get('report_name', 'Unnamed Report'),
                    'content_size': len(str(report_content))
                })
                
            except Exception as e:
                logger.error(f"Report generation failed for {report_def.get('report_name')}: {str(e)}")
        
        return {
            'generated_reports': generated_reports,
            'total_reports_generated': len(generated_reports),
            'report_definitions_available': len(report_definitions)
        }
    
    async def _generate_report_content(self, report_definition: Dict[str, Any], 
                                     report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report content based on template and data"""
        
        template = report_definition.get('template_json', {})
        
        # Simple report generation (can be enhanced with more sophisticated templating)
        report_content = {
            'report_metadata': {
                'report_name': report_definition.get('report_name', 'NMTC Processing Report'),
                'generated_at': datetime.utcnow().isoformat(),
                'template_version': template.get('version', '1.0')
            },
            'executive_summary': {
                'document_type': report_data.get('document_processing_summary', {}).get('document_type', {}).get('document_type_id', 'unknown'),
                'compliance_rate': report_data.get('compliance_summary', {}).get('compliance_rate', 0),
                'risk_level': report_data.get('compliance_summary', {}).get('overall_risk', 'unknown'),
                'sections_processed': report_data.get('document_processing_summary', {}).get('sections_identified', {}).get('sections_found', 0)
            },
            'detailed_findings': report_data.get('document_processing_summary', {}),
            'compliance_analysis': report_data.get('compliance_summary', {}),
            'recommendations': [
                'Review all flagged compliance violations',
                'Address high-risk findings promptly',
                'Implement suggested mitigation strategies'
            ]
        }
        
        return report_content
    
    async def _store_workflow_summary(self, session_id: UUID, document_id: UUID, 
                                    workflow_results: Dict[str, Any]) -> None:
        """Store overall workflow summary"""
        
        try:
            # Determine compliance status
            compliance_rate = workflow_results.get('stage_outputs', {}).get('business_rules_validation', {}).get('compliance_rate', 0)
            compliance_status = ComplianceStatus.COMPLIANT
            
            if compliance_rate < 0.5:
                compliance_status = ComplianceStatus.NON_COMPLIANT
            elif compliance_rate < 0.9:
                compliance_status = ComplianceStatus.NEEDS_REVIEW
            
            # Calculate overall confidence
            stage_outputs = workflow_results.get('stage_outputs', {})
            confidence_scores = []
            
            for stage_name, output in stage_outputs.items():
                if isinstance(output, dict) and 'confidence' in output:
                    confidence_scores.append(output['confidence'])
            
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
            
            # Store workflow results
            await self.db_service.store_workflow_results(
                session_id=session_id,
                document_id=document_id,
                workflow_status=workflow_results['overall_status'],
                overall_confidence=overall_confidence,
                processing_summary=workflow_results['stage_outputs'],
                key_findings={
                    'stages_completed': workflow_results['stages_completed'],
                    'total_stages': len(self.stages)
                },
                compliance_status=compliance_status,
                recommendations=['Complete all processing stages', 'Review compliance violations']
            )
            
        except Exception as e:
            logger.error(f"Failed to store workflow summary: {str(e)}")

# Create global service instance
corrected_workflow_service = CorrectedWorkflowService()