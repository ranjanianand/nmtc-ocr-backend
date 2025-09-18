"""
Auto Migration Service - Automatically create missing tables
This service can automatically run migrations using direct PostgreSQL connection
"""

import os
import asyncio
import logging
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class AutoMigrationService:
    """
    Service to automatically run database migrations
    Supports multiple connection methods for maximum compatibility
    """
    
    def __init__(self):
        self.migration_dir = "database/migrations"
        self.connection_string = None
    
    async def setup_direct_connection(self) -> bool:
        """
        Setup direct PostgreSQL connection for DDL operations
        Returns True if connection is available
        """
        try:
            # Method 1: Try psycopg2 with connection string
            if await self._try_psycopg2():
                return True
            
            # Method 2: Try environment variables
            if await self._try_env_connection():
                return True
            
            # Method 3: Create SQL files for manual execution
            await self._create_migration_scripts()
            return False
            
        except Exception as e:
            logger.error(f"Failed to setup database connection: {e}")
            return False
    
    async def _try_psycopg2(self) -> bool:
        """Try to connect using psycopg2"""
        try:
            import psycopg2
            
            # Try to construct connection string from Supabase URL
            supabase_url = settings.SUPABASE_URL
            if not supabase_url:
                return False
            
            # Extract project reference from Supabase URL
            # Format: https://[project-ref].supabase.co
            project_ref = supabase_url.split('//')[1].split('.')[0]
            
            # Check if DATABASE_URL is set in environment
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                logger.info("DATABASE_URL not set. To enable auto-migrations:")
                logger.info("Set DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
                return False
            
            # Test connection
            conn = psycopg2.connect(db_url)
            conn.close()
            
            self.connection_string = db_url
            logger.info("Direct PostgreSQL connection available - auto-migrations enabled!")
            return True
            
        except ImportError:
            logger.info("psycopg2 not installed. Install with: pip install psycopg2-binary")
            return False
        except Exception as e:
            logger.info(f"Direct connection not available: {e}")
            return False
    
    async def _try_env_connection(self) -> bool:
        """Try to connect using environment variables"""
        try:
            required_vars = ['SUPABASE_DB_HOST', 'SUPABASE_DB_PASSWORD', 'SUPABASE_DB_USER']
            if not all(os.getenv(var) for var in required_vars):
                return False
            
            import psycopg2
            
            conn_string = (
                f"host={os.getenv('SUPABASE_DB_HOST')} "
                f"port={os.getenv('SUPABASE_DB_PORT', '5432')} "
                f"dbname={os.getenv('SUPABASE_DB_NAME', 'postgres')} "
                f"user={os.getenv('SUPABASE_DB_USER')} "
                f"password={os.getenv('SUPABASE_DB_PASSWORD')}"
            )
            
            conn = psycopg2.connect(conn_string)
            conn.close()
            
            self.connection_string = conn_string
            return True
            
        except Exception as e:
            logger.info(f"Environment connection failed: {e}")
            return False
    
    async def run_migration(self, migration_file: str) -> bool:
        """
        Run a single migration file
        Returns True if successful
        """
        try:
            if not self.connection_string:
                logger.error("No direct database connection available")
                return False
            
            migration_path = os.path.join(self.migration_dir, migration_file)
            if not os.path.exists(migration_path):
                logger.error(f"Migration file not found: {migration_path}")
                return False
            
            # Read migration SQL
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            logger.info(f"Running migration: {migration_file}")
            
            # Execute migration
            import psycopg2
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            try:
                cursor.execute(migration_sql)
                conn.commit()
                logger.info(f"Migration {migration_file} completed successfully")
                return True
                
            except psycopg2.Error as e:
                conn.rollback()
                logger.error(f"Migration {migration_file} failed: {e}")
                return False
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            logger.error(f"Failed to run migration {migration_file}: {e}")
            return False
    
    async def run_all_pending_migrations(self) -> Dict[str, Any]:
        """
        Run all pending migrations automatically
        Returns status of all migrations
        """
        results = {
            'connection_available': False,
            'migrations_run': [],
            'migrations_failed': [],
            'status': 'failed'
        }
        
        # Check if direct connection is available
        if not await self.setup_direct_connection():
            results['status'] = 'manual_required'
            results['message'] = 'Direct database connection not available. Manual migration required.'
            return results
        
        results['connection_available'] = True
        
        # List of migrations to run in order
        migrations = [
            '002_agent_output_tables_clean.sql',
            '003_workflow_enhancement_tables.sql'
        ]
        
        # Run each migration
        for migration in migrations:
            if await self.run_migration(migration):
                results['migrations_run'].append(migration)
            else:
                results['migrations_failed'].append(migration)
        
        if len(results['migrations_failed']) == 0:
            results['status'] = 'success'
        elif len(results['migrations_run']) > 0:
            results['status'] = 'partial'
        else:
            results['status'] = 'failed'
        
        return results
    
    async def _create_migration_scripts(self) -> None:
        """Create standalone migration scripts for manual execution"""
        try:
            script_content = '''#!/bin/bash
# Automatic Migration Script for NMTC Workflow Enhancement
# Run this script to execute all pending migrations

echo "NMTC Database Migration Script"
echo "=============================="

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql is not installed"
    echo "Install PostgreSQL client tools to use this script"
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set"
    echo "Set it to your Supabase connection string:"
    echo "export DATABASE_URL='postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres'"
    exit 1
fi

echo "Running migrations..."

# Run migration 002
echo "Running 002_agent_output_tables_clean.sql..."
psql "$DATABASE_URL" -f database/migrations/002_agent_output_tables_clean.sql
if [ $? -eq 0 ]; then
    echo "✓ Migration 002 completed"
else
    echo "✗ Migration 002 failed"
    exit 1
fi

# Run migration 003
echo "Running 003_workflow_enhancement_tables.sql..."
psql "$DATABASE_URL" -f database/migrations/003_workflow_enhancement_tables.sql
if [ $? -eq 0 ]; then
    echo "✓ Migration 003 completed"
else
    echo "✗ Migration 003 failed"
    exit 1
fi

echo "All migrations completed successfully!"
echo "Test with: python simple_table_test.py"
'''
            
            with open('run_migrations.sh', 'w') as f:
                f.write(script_content)
            
            # Make executable on Unix systems
            try:
                os.chmod('run_migrations.sh', 0o755)
            except:
                pass
            
            logger.info("Created run_migrations.sh script for manual execution")
            
        except Exception as e:
            logger.error(f"Failed to create migration scripts: {e}")

# Global instance
auto_migration_service = AutoMigrationService()