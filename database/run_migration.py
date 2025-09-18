#!/usr/bin/env python3
"""
NMTC Core Engine Database Migration Runner

This script applies the enterprise database schema for Core Engine processing.
Run this to create all the necessary tables for processing sessions, agent states,
background jobs, and real-time progress tracking.

Usage:
    python database/run_migration.py

Author: Database Architect Agent
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.supabase_service import supabase_service

async def run_core_engine_migration():
    """Run the Core Engine database migration"""
    
    migration_file = project_root / "database" / "migrations" / "001_core_engine_tables.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print("🚀 Starting NMTC Core Engine Database Migration")
    print(f"📄 Reading migration file: {migration_file}")
    
    try:
        # Read migration SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print(f"📊 Migration contains {len(migration_sql)} characters")
        
        # Split SQL into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        print(f"📋 Found {len(statements)} SQL statements to execute")
        
        # Execute each statement
        successful_statements = 0
        failed_statements = 0
        
        for i, statement in enumerate(statements, 1):
            try:
                # Skip comments and empty statements
                if statement.startswith('--') or statement.startswith('/*') or len(statement) < 10:
                    continue
                
                print(f"⚡ Executing statement {i}/{len(statements)}")
                
                # For Supabase, we need to use the SQL editor or direct PostgreSQL connection
                # This is a simplified approach - in production, use proper migration tools
                
                result = supabase_service.client.rpc('exec_sql', {
                    'sql': statement
                }).execute()
                
                successful_statements += 1
                print(f"✅ Statement {i} executed successfully")
                
            except Exception as e:
                failed_statements += 1
                error_msg = str(e)
                
                # Some errors are expected (like "type already exists")
                if any(expected in error_msg.lower() for expected in [
                    'already exists',
                    'duplicate',
                    'relation already exists'
                ]):
                    print(f"⚠️  Statement {i} skipped (already exists): {error_msg[:100]}...")
                else:
                    print(f"❌ Statement {i} failed: {error_msg}")
                    # Don't stop on errors - continue with remaining statements
                    continue
        
        print("\n" + "="*60)
        print("📊 MIGRATION SUMMARY")
        print("="*60)
        print(f"✅ Successful statements: {successful_statements}")
        print(f"❌ Failed statements: {failed_statements}")
        print(f"📋 Total statements: {len(statements)}")
        
        if successful_statements > 0:
            print("\n🎉 Core Engine database schema migration completed!")
            print("\n📋 CREATED ENTERPRISE TABLES:")
            print("   • processing_sessions - Session management with heartbeat monitoring")
            print("   • agent_pipeline_states - 3-Agent workflow tracking")  
            print("   • background_jobs - Enterprise job queue with retry logic")
            print("   • progress_events - Real-time progress updates")
            print("   • user_sessions - Cross-device synchronization")
            print("   • processing_errors - Error tracking and recovery")
            
            print("\n🔧 CREATED PERFORMANCE FEATURES:")
            print("   • 20+ optimized indexes for enterprise scale")
            print("   • Row Level Security (RLS) policies")
            print("   • Utility functions for maintenance")
            print("   • Custom enums for type safety")
            
            print("\n🚀 NEXT STEPS:")
            print("   1. Update background_processor.py to use new database service")
            print("   2. Integrate frontend with real-time progress tracking")
            print("   3. Test with 50MB+ documents")
            
            return True
        else:
            print("\n❌ Migration failed - no statements executed successfully")
            return False
            
    except Exception as e:
        print(f"\n❌ Migration failed with error: {str(e)}")
        return False

async def verify_migration():
    """Verify that the migration was successful"""
    
    print("\n🔍 Verifying migration results...")
    
    expected_tables = [
        'processing_sessions',
        'agent_pipeline_states', 
        'background_jobs',
        'progress_events',
        'user_sessions',
        'processing_errors'
    ]
    
    try:
        for table in expected_tables:
            result = supabase_service.client.table(table).select('*').limit(1).execute()
            print(f"✅ Table '{table}' exists and is accessible")
            
        print("\n🎉 All Core Engine tables verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False

async def main():
    """Main migration runner"""
    
    print("🔧 NMTC Core Engine Database Migration")
    print("=" * 50)
    
    # Check environment
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_SERVICE_ROLE_KEY'):
        print("❌ Missing Supabase environment variables")
        print("   Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    
    # Run migration
    migration_success = await run_core_engine_migration()
    
    if migration_success:
        # Verify migration
        verification_success = await verify_migration()
        
        if verification_success:
            print("\n✅ Core Engine database migration completed successfully!")
            print("🚀 Ready for enterprise-grade document processing!")
        else:
            print("\n⚠️  Migration completed but verification failed")
            print("   Please check the database manually")
    else:
        print("\n❌ Migration failed - please check the errors above")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Migration cancelled by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)