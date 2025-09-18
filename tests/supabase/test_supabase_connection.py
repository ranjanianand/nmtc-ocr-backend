#!/usr/bin/env python3
"""
Test Supabase connection and explore database schema
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
from services.database_service import database_service
from services.supabase_service import supabase_service

# Load environment variables
load_dotenv()

async def test_connection():
    """Test Supabase connection and basic operations"""
    try:
        print("🔌 Testing Supabase Connection...")
        print(f"   URL: {os.getenv('SUPABASE_URL')}")
        print(f"   Service Key: {os.getenv('SUPABASE_SERVICE_KEY')[:20]}...")
        
        # Test basic connection by trying to query a system table
        print("\n📊 Testing database connection...")
        result = database_service.client.table('information_schema.tables').select('table_name').limit(5).execute()
        
        if hasattr(result, 'data') and result.data:
            print("✅ Connection successful!")
            print(f"   Found {len(result.data)} tables in schema")
        else:
            print("⚠️  Connection established but no tables found")
        
        # Test storage connection
        print("\n💾 Testing storage connection...")
        try:
            buckets = database_service.client.storage.list_buckets()
            print("✅ Storage connection successful!")
            print(f"   Available buckets: {[b.name for b in buckets] if buckets else 'None'}")
        except Exception as e:
            print(f"❌ Storage connection failed: {e}")
        
        # Try to get existing tables
        print("\n📋 Checking for existing tables...")
        tables_to_check = [
            'documents', 'organizations', 'document_types', 
            'status_types', 'user_roles', 'org_members'
        ]
        
        for table_name in tables_to_check:
            try:
                result = database_service.client.table(table_name).select('*').limit(1).execute()
                if hasattr(result, 'data'):
                    print(f"   ✅ {table_name}: Found (sample records: {len(result.data)})")
                    
                    # Show column structure for documents table
                    if table_name == 'documents' and result.data:
                        print(f"      Columns: {list(result.data[0].keys())}")
                else:
                    print(f"   ❓ {table_name}: No data or structure issue")
            except Exception as e:
                print(f"   ❌ {table_name}: {str(e)}")
        
        # Test creating a simple record (if possible)
        print("\n🧪 Testing record creation...")
        try:
            # Try to get or create a basic status type
            result = database_service.client.table('status_types').select('*').eq('key', 'test').limit(1).execute()
            
            if not result.data:
                print("   Creating test status type...")
                test_status = {
                    'key': 'test',
                    'display_name': 'Test Status',
                    'description': 'Test record for connection validation',
                    'order_index': 999
                }
                result = database_service.client.table('status_types').insert(test_status).execute()
                print("   ✅ Test record created successfully")
            else:
                print("   ✅ Test record already exists")
        except Exception as e:
            print(f"   ⚠️  Record creation test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

async def show_table_info():
    """Show detailed table information"""
    print("\n" + "="*60)
    print("📊 DATABASE SCHEMA ANALYSIS")
    print("="*60)
    
    # Show document table structure in detail
    try:
        print("\n📄 DOCUMENTS TABLE:")
        result = database_service.client.table('documents').select('*').limit(1).execute()
        if result.data:
            doc = result.data[0]
            print("   Columns:")
            for key, value in doc.items():
                print(f"      {key}: {type(value).__name__} = {str(value)[:50]}")
        else:
            print("   No sample data available")
            
        # Get total count
        count_result = database_service.client.table('documents').select('id', count='exact').execute()
        print(f"   Total records: {count_result.count if hasattr(count_result, 'count') else 'Unknown'}")
        
    except Exception as e:
        print(f"   Error accessing documents table: {e}")

async def main():
    """Main test function"""
    print("🚀 SUPABASE CONNECTION TEST")
    print("="*60)
    
    success = await test_connection()
    
    if success:
        await show_table_info()
        print("\n✅ All tests completed successfully!")
    else:
        print("\n❌ Connection tests failed. Please check your configuration.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())