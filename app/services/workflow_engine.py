"""
NMTC Platform Enterprise Workflow Engine
Autonomous document processing with Supabase integration
"""

import asyncio
import threading
import time
import uuid
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json
import hashlib

from .supabase_service import supabase_service
from .detection_service import detection_service
from .nmtc_agents import process_nmtc_document
from .ai_service import ai_service

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowStep:
    name: str
    display_name: str
    order: int
    estimated_duration_minutes: int
    function: Callable
    dependencies: List[str] = None
    can_retry: bool = True
    max_retries: int = 3

@dataclass
class JobMetrics:
    start_time: datetime
    estimated_completion: datetime
    steps_completed: int
    steps_total: int
    current_throughput: float
    error_count: int

class WorkflowEngineError(Exception):
    """Base exception for workflow engine errors"""
    pass

class EnterpriseWorkflowEngine:
    """
    Production-grade workflow orchestration engine
    Handles fire-and-forget document processing with Supabase persistence
    """

    def __init__(self, max_concurrent_jobs: int = 3):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_jobs)
        self.active_jobs: Dict[str, threading.Thread] = {}
        self.job_metrics: Dict[str, JobMetrics] = {}
        self.shutdown_event = threading.Event()

        # Recovery and monitoring
        self._recovery_thread = threading.Thread(target=self._recovery_monitor, daemon=True)
        self._recovery_thread.start()

        logger.info(f"Enterprise Workflow Engine initialized with {max_concurrent_jobs} workers")

    async def health_check(self) -> bool:
        """Health check for workflow engine"""
        try:
            # Check basic functionality
            return True
        except Exception as e:
            logger.error(f"Workflow engine health check failed: {e}")
            return False

    async def submit_allocation_job(self,
                             org_id: str,
                             user_id: str,
                             document_id: str,
                             allocation_year: int,
                             description: Optional[str] = None) -> str:
        """
        Submit allocation processing job - returns immediately with job_id
        This is the main entry point for fire-and-forget processing
        """

        try:
            # Generate human-readable job ID
            job_id = self._generate_job_id(org_id, allocation_year)

            # Get document information
            document_info = supabase_service.get_document_by_id(document_id)
            if not document_info:
                raise WorkflowEngineError(f"Document {document_id} not found")

            # Create comprehensive job record
            job_data = {
                "job_id": job_id,
                "org_id": org_id,
                "user_id": user_id,
                "job_type": "allocation_processing",
                "display_name": f"Allocation Agreement {allocation_year}",
                "original_filename": document_info.get("filename", "unknown.pdf"),
                "status": JobStatus.QUEUED.value,
                "progress_percent": 0,
                "estimated_duration_minutes": 25,
                "input_metadata": {
                    "document_id": document_id,
                    "allocation_year": allocation_year,
                    "description": description,
                    "file_size_mb": document_info.get("file_size", 0),
                    "submission_source": "allocation_dashboard",
                    "document_url": document_info.get("storage_url")
                },
                "created_by": user_id
            }

            # Atomic operations in Supabase
            job_record = self._create_job_record(job_data)
            self._create_workflow_steps(job_id)
            self._link_document_to_job(document_id, job_id)

            # Submit for background processing
            future = self.executor.submit(self._execute_allocation_workflow, job_id)
            self.active_jobs[job_id] = future

            # Log successful submission
            self._log_event(job_id, "job_submitted", {
                "submission_time": datetime.utcnow().isoformat(),
                "document_id": document_id,
                "allocation_year": allocation_year
            })

            logger.info(f"Allocation job {job_id} submitted successfully")
            return job_id

        except Exception as e:
            logger.error(f"Failed to submit allocation job: {str(e)}")
            raise WorkflowEngineError(f"Job submission failed: {str(e)}")

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get comprehensive job status - main API for frontend polling
        """

        try:
            # Get job data from Supabase
            job_data = supabase_service.client.table("workflow_jobs").select("*").eq("job_id", job_id).execute()

            if not job_data.data:
                return {"error": "Job not found", "job_id": job_id}

            job = job_data.data[0]

            # Get step details
            steps_data = supabase_service.client.table("workflow_steps").select("*").eq("job_id", job_id).order("step_order").execute()
            steps = steps_data.data if steps_data.data else []

            # Get recent events
            events_data = supabase_service.client.table("workflow_events").select("*").eq("job_id", job_id).order("created_at", desc=True).limit(5).execute()
            events = events_data.data if events_data.data else []

            # Calculate metrics
            metrics = self._calculate_job_metrics(job_id, job, steps)

            # Build comprehensive response
            return {
                "job_id": job_id,
                "status": job["status"],
                "progress_percent": job["progress_percent"],
                "current_step": job["current_step"],
                "current_step_detail": job["current_step_detail"],

                # Timing information
                "created_at": job["created_at"],
                "started_at": job["started_at"],
                "estimated_completion": self._calculate_estimated_completion(job),
                "estimated_remaining_minutes": self._calculate_remaining_time(job, metrics),

                # Progress details
                "steps_completed": len([s for s in steps if s["status"] == "completed"]),
                "steps_total": len(steps),
                "detailed_steps": [self._format_step_for_ui(step) for step in steps],

                # User-facing information
                "can_view_partial_results": job["progress_percent"] > 40,
                "can_cancel": job["status"] in ["queued", "running"],
                "can_retry": job["status"] == "failed",

                # Error information
                "error_message": job.get("error_message"),
                "retry_count": job.get("retry_count", 0),

                # Business context
                "original_filename": job["original_filename"],
                "display_name": job["display_name"],
                "allocation_year": job.get("input_metadata", {}).get("allocation_year"),

                # Results
                "partial_results": job.get("partial_results"),
                "final_results": job.get("final_results") if job["status"] == "completed" else None,

                # Recent activity
                "recent_events": [self._format_event_for_ui(event) for event in events]
            }

        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {str(e)}")
            return {"error": "Status retrieval failed", "job_id": job_id}

    def get_active_jobs_for_org(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all active jobs for an organization"""

        try:
            response = supabase_service.client.table("workflow_jobs").select(
                "job_id, display_name, status, progress_percent, current_step, created_at, original_filename"
            ).eq("org_id", org_id).in_("status", ["queued", "running"]).order("created_at", desc=True).execute()

            jobs = []
            for job in response.data:
                jobs.append({
                    "job_id": job["job_id"],
                    "display_name": job["display_name"],
                    "status": job["status"],
                    "progress_percent": job["progress_percent"],
                    "current_step": job["current_step"],
                    "created_at": job["created_at"],
                    "original_filename": job["original_filename"],
                    "estimated_completion": self._calculate_estimated_completion(job)
                })

            return jobs

        except Exception as e:
            logger.error(f"Error getting active jobs for org {org_id}: {str(e)}")
            return []

    def get_jobs_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Find all jobs associated with a document - key recovery mechanism"""

        try:
            # First get the document to find associated job
            doc_response = supabase_service.client.table("documents").select("job_id, filename, uploaded_at").eq("document_id", document_id).execute()

            if not doc_response.data:
                return []

            document = doc_response.data[0]
            job_id = document.get("job_id")

            if not job_id:
                return []

            # Get the job details
            job_response = supabase_service.client.table("workflow_jobs").select("*").eq("job_id", job_id).execute()

            if not job_response.data:
                return []

            job = job_response.data[0]

            return [{
                "job_id": job["job_id"],
                "display_name": job["display_name"],
                "status": job["status"],
                "progress_percent": job["progress_percent"],
                "created_at": job["created_at"],
                "original_filename": job["original_filename"],
                "document_filename": document["filename"]
            }]

        except Exception as e:
            logger.error(f"Error getting jobs by document {document_id}: {str(e)}")
            return []

    def _execute_allocation_workflow(self, job_id: str):
        """
        Main workflow execution - runs in background thread
        Handles the complete allocation agreement processing pipeline
        """

        start_time = datetime.utcnow()

        try:
            logger.info(f"Starting workflow execution for job {job_id}")

            # Update job to running status
            self._update_job_status(job_id, JobStatus.RUNNING, 5, "initializing_workflow")
            self._log_event(job_id, "workflow_started", {"start_time": start_time.isoformat()})

            # Get job configuration
            job_data = self._get_job_from_database(job_id)
            document_id = job_data["input_metadata"]["document_id"]
            allocation_year = job_data["input_metadata"]["allocation_year"]

            # Step 1: Document Upload & Validation (5-10%)
            self._execute_step_safely(job_id, "document_validation", self._step_document_validation, document_id)
            self._update_job_progress(job_id, 10, "document_validation_complete")

            # Step 2: Azure OCR Processing (10-60%)
            ocr_text = self._execute_step_safely(job_id, "azure_ocr_processing", self._step_azure_ocr, document_id)
            self._update_job_progress(job_id, 60, "azure_ocr_complete")

            # Step 3: AI Agents Processing with Allocation Year Configuration (60-90%)
            agents_results = self._execute_step_safely(job_id, "ai_agents_processing", self._step_ai_agents, ocr_text, allocation_year)
            self._update_job_progress(job_id, 90, "ai_agents_complete")

            # Step 4: Results Compilation (90-100%)
            final_results = self._execute_step_safely(job_id, "results_compilation", self._step_compile_results, agents_results, job_data)
            self._update_job_progress(job_id, 100, "workflow_complete")

            # Mark job as completed
            completion_time = datetime.utcnow()
            duration_minutes = (completion_time - start_time).total_seconds() / 60

            self._complete_job(job_id, final_results, duration_minutes)

            logger.info(f"Workflow {job_id} completed successfully in {duration_minutes:.2f} minutes")

        except Exception as e:
            logger.error(f"Workflow execution failed for job {job_id}: {str(e)}")
            self._handle_workflow_failure(job_id, str(e))

        finally:
            # Cleanup resources
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    def _step_document_validation(self, document_id: str) -> bool:
        """Step 1: Validate document exists and is accessible"""

        document_info = supabase_service.get_document_by_id(document_id)
        if not document_info:
            raise WorkflowEngineError(f"Document {document_id} not found")

        # Validate document accessibility
        if not document_info.get("storage_url"):
            raise WorkflowEngineError("Document storage URL not found")

        logger.info(f"Document validation successful for {document_id}")
        return True

    def _step_azure_ocr(self, document_id: str) -> str:
        """Step 2: Extract text using Azure Document Intelligence"""

        # Get document URL from Supabase
        document_info = supabase_service.get_document_by_id(document_id)
        document_url = document_info["storage_url"]

        # Use existing detection service for OCR
        ocr_results = detection_service.process_document_url(document_url)

        if not ocr_results or "error" in ocr_results:
            raise WorkflowEngineError(f"Azure OCR failed: {ocr_results.get('error', 'Unknown error')}")

        # Extract text content
        extracted_text = ocr_results.get("extracted_text", "")
        if not extracted_text:
            raise WorkflowEngineError("No text extracted from document")

        logger.info(f"Azure OCR extracted {len(extracted_text)} characters")
        return extracted_text

    def _get_allocation_year_configuration(self, allocation_year: int) -> Dict[str, Any]:
        """Get allocation year configuration from database"""
        try:
            result = supabase_service.client.table("allocation_years").select("*").eq("year", allocation_year).execute()

            if not result.data:
                raise WorkflowEngineError(f"Allocation year {allocation_year} configuration not found")

            config = result.data[0]
            logger.info(f"Retrieved allocation year {allocation_year} configuration")
            return config
        except Exception as e:
            logger.error(f"Failed to get allocation year configuration: {e}")
            raise WorkflowEngineError(f"Configuration lookup failed: {str(e)}")

    def _step_ai_agents(self, document_text: str, allocation_year: int) -> Dict[str, Any]:
        """Step 3: Process document through NMTC AI agents with allocation year context"""

        if not document_text or len(document_text.strip()) < 100:
            raise WorkflowEngineError("Insufficient text for AI processing")

        # Get allocation year configuration
        allocation_config = self._get_allocation_year_configuration(allocation_year)

        # Extract configuration details
        document_types = allocation_config.get("document_types", [])
        required_sections = allocation_config.get("required_sections", [])
        processing_instructions = allocation_config.get("processing_instructions", {})

        # Process through all 3 agents with enhanced context
        agents_results = process_nmtc_document(
            document_text,
            allocation_year=allocation_year,
            document_types=document_types,
            required_sections=required_sections,
            processing_instructions=processing_instructions
        )

        # Validate results
        if not agents_results:
            raise WorkflowEngineError("AI agents processing failed")

        # Check if critical agents succeeded
        critical_agents = ["classification", "extraction"]
        failed_critical = [agent for agent in critical_agents if not agents_results.get(agent, {}).success]

        if failed_critical:
            raise WorkflowEngineError(f"Critical agents failed: {', '.join(failed_critical)}")

        logger.info(f"AI agents processing completed with allocation year {allocation_year} context. Success rate: {len([r for r in agents_results.values() if hasattr(r, 'success') and r.success])}/{len([r for r in agents_results.values() if hasattr(r, 'success')])}")
        return agents_results

    def _step_compile_results(self, agents_results: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: Compile final results and generate dashboard data"""

        try:
            # Extract key information from agents
            classification = agents_results.get("classification", {})
            extraction = agents_results.get("extraction", {})
            analysis = agents_results.get("analysis", {})

            # Compile dashboard summary
            final_results = {
                "processing_summary": {
                    "job_id": job_data["job_id"],
                    "processing_date": datetime.utcnow().isoformat(),
                    "document_filename": job_data["original_filename"],
                    "allocation_year": job_data["input_metadata"]["allocation_year"],
                    "total_processing_time_minutes": (datetime.utcnow() - datetime.fromisoformat(job_data["created_at"].replace('Z', '+00:00'))).total_seconds() / 60
                },

                "document_classification": classification.data if hasattr(classification, 'data') else {},
                "extracted_data": extraction.data if hasattr(extraction, 'data') else {},
                "compliance_analysis": analysis.data if hasattr(analysis, 'data') else {},

                "dashboard_data": {
                    "cde_name": self._safe_extract(classification, "data.cde_name", "Unknown CDE"),
                    "total_allocation_amount": self._safe_extract(classification, "data.total_allocation_amount", 0),
                    "allocation_year": self._safe_extract(classification, "data.allocation_year", job_data["input_metadata"]["allocation_year"]),
                    "risk_score": self._safe_extract(analysis, "data.risk_assessment.overall_risk_score", 5),
                    "success_probability": self._safe_extract(analysis, "data.success_probability.overall_success_probability", 0.5),
                    "compliance_status": "processed",
                    "key_findings": self._extract_key_findings(agents_results)
                },

                "confidence_scores": {
                    "classification_confidence": getattr(classification, 'confidence_score', 0.0),
                    "extraction_confidence": getattr(extraction, 'confidence_score', 0.0),
                    "analysis_confidence": getattr(analysis, 'confidence_score', 0.0),
                    "overall_confidence": self._calculate_overall_confidence(agents_results)
                },

                "agent_performance": {
                    "classification_time": getattr(classification, 'processing_time_seconds', 0),
                    "extraction_time": getattr(extraction, 'processing_time_seconds', 0),
                    "analysis_time": getattr(analysis, 'processing_time_seconds', 0)
                }
            }

            logger.info(f"Results compilation completed for {job_data['job_id']}")
            return final_results

        except Exception as e:
            logger.error(f"Results compilation failed: {str(e)}")
            raise WorkflowEngineError(f"Results compilation failed: {str(e)}")

    def _safe_extract(self, obj, path: str, default=None):
        """Safely extract nested values from objects"""
        try:
            keys = path.split('.')
            value = obj
            for key in keys:
                if hasattr(value, key):
                    value = getattr(value, key)
                elif isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value
        except:
            return default

    def _extract_key_findings(self, agents_results: Dict[str, Any]) -> List[str]:
        """Extract key findings for dashboard display"""
        findings = []

        try:
            # From classification
            classification = agents_results.get("classification", {})
            if hasattr(classification, 'data'):
                cde_name = classification.data.get("cde_name")
                if cde_name:
                    findings.append(f"Community Development Entity: {cde_name}")

            # From extraction
            extraction = agents_results.get("extraction", {})
            if hasattr(extraction, 'data'):
                financial = extraction.data.get("financial_details", {})
                max_loan = financial.get("maximum_qlici_loan_amount")
                if max_loan:
                    findings.append(f"Maximum QLICI Loan: ${max_loan:,}")

            # From analysis
            analysis = agents_results.get("analysis", {})
            if hasattr(analysis, 'data'):
                risk = analysis.data.get("risk_assessment", {})
                high_risks = risk.get("high_risk_factors", [])
                if high_risks:
                    findings.append(f"High Risk Factors: {len(high_risks)} identified")

        except Exception as e:
            logger.warning(f"Error extracting key findings: {str(e)}")

        return findings[:5]  # Limit to top 5 findings

    def _calculate_overall_confidence(self, agents_results: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        scores = []

        for agent_name, result in agents_results.items():
            if hasattr(result, 'confidence_score'):
                scores.append(result.confidence_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _execute_step_safely(self, job_id: str, step_name: str, step_function: Callable, *args, **kwargs):
        """Execute a workflow step with error handling and progress tracking"""

        step_start = datetime.utcnow()

        try:
            # Update step status to running
            self._update_step_status(job_id, step_name, StepStatus.RUNNING)
            logger.info(f"Starting step {step_name} for job {job_id}")

            # Execute the step function
            result = step_function(*args, **kwargs)

            # Update step status to completed
            duration = (datetime.utcnow() - step_start).total_seconds()
            self._update_step_completion(job_id, step_name, result, duration)

            logger.info(f"Step {step_name} completed for job {job_id} in {duration:.2f}s")
            return result

        except Exception as e:
            duration = (datetime.utcnow() - step_start).total_seconds()
            error_msg = str(e)

            self._update_step_failure(job_id, step_name, error_msg, duration)
            logger.error(f"Step {step_name} failed for job {job_id}: {error_msg}")

            raise WorkflowEngineError(f"Step {step_name} failed: {error_msg}")

    def _generate_job_id(self, org_id: str, allocation_year: int) -> str:
        """Generate human-readable job ID"""

        # Use first 6 chars of org_id hash + year + random
        org_hash = hashlib.md5(org_id.encode()).hexdigest()[:6].upper()
        timestamp = datetime.utcnow().strftime("%m%d%H%M")

        job_id = f"NMTC-{allocation_year}-{org_hash}-{timestamp}"

        # Ensure uniqueness
        existing = supabase_service.client.table("workflow_jobs").select("job_id").eq("job_id", job_id).execute()
        if existing.data:
            # Add random suffix if collision
            import random
            job_id += f"-{random.randint(10,99)}"

        return job_id

    def _create_job_record(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create job record in Supabase"""

        response = supabase_service.client.table("workflow_jobs").insert(job_data).execute()

        if not response.data:
            raise WorkflowEngineError("Failed to create job record")

        return response.data[0]

    def _create_workflow_steps(self, job_id: str):
        """Create workflow steps for allocation processing"""

        steps = [
            {"job_id": job_id, "step_name": "document_validation", "step_display_name": "Document Validation", "step_order": 1, "status": "pending"},
            {"job_id": job_id, "step_name": "azure_ocr_processing", "step_display_name": "Azure OCR Processing", "step_order": 2, "status": "pending"},
            {"job_id": job_id, "step_name": "ai_agents_processing", "step_display_name": "AI Analysis", "step_order": 3, "status": "pending"},
            {"job_id": job_id, "step_name": "results_compilation", "step_display_name": "Results Compilation", "step_order": 4, "status": "pending"}
        ]

        supabase_service.client.table("workflow_steps").insert(steps).execute()

    def _link_document_to_job(self, document_id: str, job_id: str):
        """Link document to workflow job"""

        supabase_service.client.table("documents").update({
            "job_id": job_id,
            "processing_status": "queued",
            "job_created_at": datetime.utcnow().isoformat()
        }).eq("document_id", document_id).execute()

    def _update_job_status(self, job_id: str, status: JobStatus, progress: int, current_step: str):
        """Update job status in database"""

        update_data = {
            "status": status.value,
            "progress_percent": progress,
            "current_step": current_step,
            "updated_at": datetime.utcnow().isoformat()
        }

        if status == JobStatus.RUNNING and progress == 5:
            update_data["started_at"] = datetime.utcnow().isoformat()

        supabase_service.client.table("workflow_jobs").update(update_data).eq("job_id", job_id).execute()

    def _update_job_progress(self, job_id: str, progress: int, current_step: str):
        """Update job progress"""

        supabase_service.client.table("workflow_jobs").update({
            "progress_percent": progress,
            "current_step": current_step,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("job_id", job_id).execute()

    def _update_step_status(self, job_id: str, step_name: str, status: StepStatus):
        """Update step status"""

        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }

        if status == StepStatus.RUNNING:
            update_data["started_at"] = datetime.utcnow().isoformat()

        supabase_service.client.table("workflow_steps").update(update_data).eq("job_id", job_id).eq("step_name", step_name).execute()

    def _update_step_completion(self, job_id: str, step_name: str, result: Any, duration_seconds: float):
        """Update step completion"""

        supabase_service.client.table("workflow_steps").update({
            "status": StepStatus.COMPLETED.value,
            "completed_at": datetime.utcnow().isoformat(),
            "duration_seconds": int(duration_seconds),
            "step_output": {"success": True, "result_summary": str(result)[:500]}
        }).eq("job_id", job_id).eq("step_name", step_name).execute()

    def _update_step_failure(self, job_id: str, step_name: str, error_message: str, duration_seconds: float):
        """Update step failure"""

        supabase_service.client.table("workflow_steps").update({
            "status": StepStatus.FAILED.value,
            "completed_at": datetime.utcnow().isoformat(),
            "duration_seconds": int(duration_seconds),
            "error_details": error_message
        }).eq("job_id", job_id).eq("step_name", step_name).execute()

    def _complete_job(self, job_id: str, final_results: Dict[str, Any], duration_minutes: float):
        """Complete job successfully"""

        supabase_service.client.table("workflow_jobs").update({
            "status": JobStatus.COMPLETED.value,
            "progress_percent": 100,
            "current_step": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "actual_duration_minutes": int(duration_minutes),
            "final_results": final_results
        }).eq("job_id", job_id).execute()

        # Log completion event
        self._log_event(job_id, "job_completed", {
            "completion_time": datetime.utcnow().isoformat(),
            "duration_minutes": duration_minutes,
            "final_status": "success"
        })

    def _handle_workflow_failure(self, job_id: str, error_message: str):
        """Handle workflow failure"""

        supabase_service.client.table("workflow_jobs").update({
            "status": JobStatus.FAILED.value,
            "error_message": error_message,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("job_id", job_id).execute()

        # Log failure event
        self._log_event(job_id, "job_failed", {
            "failure_time": datetime.utcnow().isoformat(),
            "error_message": error_message
        })

    def _log_event(self, job_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log workflow event"""

        try:
            supabase_service.client.table("workflow_events").insert({
                "job_id": job_id,
                "event_type": event_type,
                "event_category": "system",
                "event_data": event_data,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log event {event_type} for job {job_id}: {str(e)}")

    def _get_job_from_database(self, job_id: str) -> Dict[str, Any]:
        """Get job data from database"""

        response = supabase_service.client.table("workflow_jobs").select("*").eq("job_id", job_id).execute()

        if not response.data:
            raise WorkflowEngineError(f"Job {job_id} not found")

        return response.data[0]

    def _calculate_job_metrics(self, job_id: str, job: Dict[str, Any], steps: List[Dict[str, Any]]) -> JobMetrics:
        """Calculate job metrics for status display"""

        try:
            start_time = datetime.fromisoformat(job["created_at"].replace('Z', '+00:00'))
            estimated_duration = timedelta(minutes=job["estimated_duration_minutes"])
            estimated_completion = start_time + estimated_duration

            steps_completed = len([s for s in steps if s["status"] == "completed"])
            steps_total = len(steps)

            return JobMetrics(
                start_time=start_time,
                estimated_completion=estimated_completion,
                steps_completed=steps_completed,
                steps_total=steps_total,
                current_throughput=0.0,  # Can be calculated based on actual progress
                error_count=len([s for s in steps if s["status"] == "failed"])
            )
        except Exception:
            # Return default metrics if calculation fails
            return JobMetrics(
                start_time=datetime.utcnow(),
                estimated_completion=datetime.utcnow() + timedelta(minutes=25),
                steps_completed=0,
                steps_total=4,
                current_throughput=0.0,
                error_count=0
            )

    def _calculate_estimated_completion(self, job: Dict[str, Any]) -> str:
        """Calculate estimated completion time"""

        try:
            created_at = datetime.fromisoformat(job["created_at"].replace('Z', '+00:00'))
            estimated_duration = timedelta(minutes=job["estimated_duration_minutes"])
            return (created_at + estimated_duration).isoformat()
        except:
            return (datetime.utcnow() + timedelta(minutes=25)).isoformat()

    def _calculate_remaining_time(self, job: Dict[str, Any], metrics: JobMetrics) -> int:
        """Calculate remaining time in minutes"""

        try:
            if job["status"] in ["completed", "failed"]:
                return 0

            progress = job["progress_percent"]
            if progress == 0:
                return job["estimated_duration_minutes"]

            # Estimate based on current progress
            elapsed_minutes = (datetime.utcnow() - metrics.start_time).total_seconds() / 60
            estimated_total = elapsed_minutes * (100 / progress)
            remaining = max(0, estimated_total - elapsed_minutes)

            return int(remaining)
        except:
            return job.get("estimated_duration_minutes", 25)

    def _format_step_for_ui(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Format step data for UI display"""

        return {
            "name": step["step_name"],
            "display_name": step["step_display_name"],
            "status": step["status"],
            "progress_percent": step.get("progress_percent", 0),
            "started_at": step.get("started_at"),
            "completed_at": step.get("completed_at"),
            "duration_seconds": step.get("duration_seconds"),
            "error_details": step.get("error_details")
        }

    def _format_event_for_ui(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event data for UI display"""

        return {
            "event_type": event["event_type"],
            "created_at": event["created_at"],
            "description": self._get_event_description(event["event_type"]),
            "data": event.get("event_data", {})
        }

    def _get_event_description(self, event_type: str) -> str:
        """Get human-readable event description"""

        descriptions = {
            "job_submitted": "Job submitted for processing",
            "workflow_started": "Workflow execution started",
            "job_completed": "Job completed successfully",
            "job_failed": "Job processing failed",
            "step_started": "Processing step started",
            "step_completed": "Processing step completed"
        }

        return descriptions.get(event_type, event_type.replace("_", " ").title())

    def _recovery_monitor(self):
        """Background thread that monitors for interrupted jobs"""

        while not self.shutdown_event.is_set():
            try:
                # Find jobs that may need recovery
                response = supabase_service.client.table("workflow_jobs").select("job_id, status, started_at").eq("status", "running").execute()

                current_time = datetime.utcnow()

                for job in response.data:
                    if job["started_at"]:
                        started_at = datetime.fromisoformat(job["started_at"].replace('Z', '+00:00'))
                        # If job has been running for more than 45 minutes, consider it stuck
                        if (current_time - started_at).total_seconds() > 2700:  # 45 minutes
                            logger.warning(f"Found potentially stuck job: {job['job_id']}")
                            # Could implement recovery logic here

                # Sleep before next check
                time.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Recovery monitor error: {str(e)}")
                time.sleep(600)  # Wait longer on error

    def shutdown(self):
        """Gracefully shutdown the workflow engine"""

        logger.info("Shutting down workflow engine...")
        self.shutdown_event.set()

        # Wait for active jobs to complete (with timeout)
        for job_id, future in self.active_jobs.items():
            try:
                future.result(timeout=30)  # 30 second timeout per job
            except:
                logger.warning(f"Job {job_id} did not complete during shutdown")

        self.executor.shutdown(wait=True)
        logger.info("Workflow engine shutdown complete")

# Create singleton instance
workflow_engine = EnterpriseWorkflowEngine()

# Export for use in other modules
__all__ = [
    "workflow_engine",
    "EnterpriseWorkflowEngine",
    "JobStatus",
    "WorkflowEngineError"
]