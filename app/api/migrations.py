"""
Database Migration API Endpoints
Allows automatic execution of database migrations
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.services.auto_migration_service import auto_migration_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/migrations", tags=["migrations"])

@router.post("/run-auto")
async def run_auto_migrations():
    """
    Automatically run all pending database migrations
    This endpoint attempts to run migrations automatically if direct DB connection is available
    """
    try:
        logger.info("Starting automatic migration process...")
        
        results = await auto_migration_service.run_all_pending_migrations()
        
        if results['status'] == 'success':
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "All migrations completed successfully!",
                    "migrations_run": results['migrations_run'],
                    "connection_method": "direct_postgresql",
                    "next_steps": [
                        "Run: python simple_table_test.py",
                        "Test the corrected workflow system",
                        "All API endpoints should now work"
                    ]
                }
            )
        
        elif results['status'] == 'partial':
            return JSONResponse(
                status_code=207,  # Multi-status
                content={
                    "success": False,
                    "message": "Some migrations failed",
                    "migrations_run": results['migrations_run'],
                    "migrations_failed": results['migrations_failed'],
                    "next_steps": [
                        "Check logs for error details",
                        "Run failed migrations manually in Supabase Dashboard"
                    ]
                }
            )
        
        elif results['status'] == 'manual_required':
            return JSONResponse(
                status_code=202,  # Accepted but manual action needed
                content={
                    "success": False,
                    "message": "Direct database connection not available - manual migration required",
                    "connection_available": False,
                    "manual_steps": [
                        "Go to Supabase Dashboard > SQL Editor",
                        "Run: database/migrations/002_agent_output_tables_clean.sql",
                        "Run: database/migrations/003_workflow_enhancement_tables.sql",
                        "Test with: python simple_table_test.py"
                    ],
                    "alternative": "Set DATABASE_URL environment variable to enable auto-migrations"
                }
            )
        
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "All migrations failed",
                    "migrations_failed": results['migrations_failed'],
                    "connection_available": results['connection_available']
                }
            )
            
    except Exception as e:
        logger.error(f"Migration API error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Migration failed: {str(e)}"
        )

@router.get("/status")
async def get_migration_status():
    """
    Check the current migration status and what tables exist
    """
    try:
        from app.services.supabase_service import supabase_service
        
        # Check what tables exist
        required_tables = [
            'agent_extraction_results', 'risk_assessment_results', 
            'generated_reports', 'agent_workflow_results',
            'document_section_instances', 'query_execution_results',
            'normalization_applications', 'business_rule_evaluations',
            'agent_prompt_applications', 'workflow_stage_completions'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in required_tables:
            try:
                result = supabase_service.client.table(table).select('*').limit(0).execute()
                existing_tables.append(table)
            except:
                missing_tables.append(table)
        
        # Check if auto-migration is possible
        connection_available = await auto_migration_service.setup_direct_connection()
        
        status = "complete" if len(missing_tables) == 0 else "pending"
        
        return {
            "status": status,
            "total_tables_required": len(required_tables),
            "existing_tables": len(existing_tables),
            "missing_tables": len(missing_tables),
            "missing_table_names": missing_tables,
            "auto_migration_available": connection_available,
            "migration_methods": {
                "automatic": connection_available,
                "manual_supabase": True,
                "script_execution": True
            },
            "next_actions": {
                "if_auto_available": "POST /api/migrations/run-auto",
                "if_manual_required": [
                    "Supabase Dashboard > SQL Editor",
                    "Run migration files manually"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Migration status error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check migration status: {str(e)}"
        )

@router.get("/setup-instructions")
async def get_setup_instructions():
    """
    Get detailed instructions for setting up auto-migrations
    """
    return {
        "title": "Enable Automatic Database Migrations",
        "methods": [
            {
                "method": "Environment Variable",
                "description": "Set DATABASE_URL to enable direct PostgreSQL access",
                "steps": [
                    "Go to Supabase Dashboard > Settings > Database",
                    "Copy the Connection string (URI format)",
                    "Set environment variable: DATABASE_URL='postgresql://...'",
                    "Restart your application",
                    "Call POST /api/migrations/run-auto"
                ],
                "example": "DATABASE_URL='postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres'"
            },
            {
                "method": "Install psycopg2",
                "description": "Install PostgreSQL adapter for Python",
                "steps": [
                    "pip install psycopg2-binary",
                    "Set DATABASE_URL as above",
                    "Auto-migrations will be enabled"
                ]
            },
            {
                "method": "Manual Migration (Current)",
                "description": "Run migrations manually in Supabase Dashboard",
                "steps": [
                    "Supabase Dashboard > SQL Editor",
                    "Copy content from database/migrations/002_agent_output_tables_clean.sql",
                    "Paste and run",
                    "Copy content from database/migrations/003_workflow_enhancement_tables.sql", 
                    "Paste and run",
                    "Test with: python simple_table_test.py"
                ]
            }
        ],
        "future_benefits": [
            "Automatic table creation in development",
            "Seamless migration deployment",
            "No manual SQL execution needed",
            "Version-controlled database changes",
            "Rollback capabilities"
        ]
    }

@router.post("/create-script")
async def create_migration_script():
    """
    Create a shell script for running migrations via command line
    """
    try:
        await auto_migration_service._create_migration_scripts()
        
        return {
            "success": True,
            "message": "Migration script created successfully",
            "file_created": "run_migrations.sh",
            "usage": [
                "Set DATABASE_URL environment variable",
                "Make script executable: chmod +x run_migrations.sh",
                "Run script: ./run_migrations.sh"
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create migration script: {str(e)}"
        )