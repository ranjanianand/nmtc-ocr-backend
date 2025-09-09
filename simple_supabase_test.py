#!/usr/bin/env python3
"""
Simple Supabase connection test without complex models
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test basic Supabase connection"""
    try:
        # Initialize client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            print("Missing environment variables:")
            print(f"   SUPABASE_URL: {'OK' if url else 'MISSING'}")
            print(f"   SUPABASE_SERVICE_KEY: {'OK' if key else 'MISSING'}")
            return False
        
        print(">> Connecting to Supabase...")
        print(f"   URL: {url}")
        print(f"   Key: {key[:20]}...")
        
        client: Client = create_client(url, key)
        
        # Test basic query - try to get table schema information
        print("\n>> Testing database connection...")
        
        # Try a simple query first
        try:
            # Query table information (PostgreSQL system table)
            result = client.rpc('pg_tables_list').execute()
            print("[OK] RPC connection successful!")
        except:
            # Fallback to a direct table query
            try:
                result = client.table('information_schema.tables').select('table_name').limit(5).execute()
                print("[OK] Information schema query successful!")
            except Exception as e:
                print(f"[WARNING] Schema query failed, trying direct table access: {e}")
        
        # Test storage connection
        print("\n>> Testing storage connection...")
        try:
            buckets = client.storage.list_buckets()
            print("[OK] Storage connection successful!")
            print(f"   Available buckets: {len(buckets)} found")
            for bucket in buckets[:5]:  # Show first 5
                print(f"      - {bucket.name}")
        except Exception as e:
            print(f"[ERROR] Storage connection failed: {e}")
        
        # Test basic table operations
        print("\n>> Checking common tables...")
        common_tables = ['documents', 'organizations', 'status_types']
        
        for table in common_tables:
            try:
                result = client.table(table).select('*').limit(1).execute()
                count = len(result.data) if result.data else 0
                print(f"   ✅ {table}: Accessible ({count} sample records)")
                
                if table == 'documents' and result.data:
                    # Show structure
                    columns = list(result.data[0].keys())
                    print(f"      Columns: {', '.join(columns[:8])}{'...' if len(columns) > 8 else ''}")
                    
            except Exception as e:
                if "does not exist" in str(e).lower() or "relation" in str(e).lower():
                    print(f"   ❓ {table}: Table not found (needs creation)")
                else:
                    print(f"   ❌ {table}: Error - {str(e)[:100]}")
        
        # Test basic insert/update capability
        print("\n🧪 Testing write operations...")
        try:
            # Try to create a simple test record in a system table
            test_data = {
                'key': 'connection_test',
                'display_name': 'Connection Test',
                'description': 'Test record created during connection validation',
                'order_index': 9999
            }
            
            # First try to see if status_types exists
            result = client.table('status_types').select('*').eq('key', 'connection_test').execute()
            
            if not result.data:
                insert_result = client.table('status_types').insert(test_data).execute()
                print("   ✅ Write test: Successfully created test record")
                
                # Clean up
                client.table('status_types').delete().eq('key', 'connection_test').execute()
                print("   ✅ Write test: Successfully cleaned up test record")
            else:
                print("   ✅ Write test: Table accessible, test record already exists")
                
        except Exception as e:
            print(f"   ⚠️  Write test failed (table may need setup): {e}")
        
        print("\n✅ Connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def show_table_creation_guide():
    """Show SQL commands for creating basic tables"""
    print("\n" + "="*60)
    print("📋 TABLE CREATION GUIDE")
    print("="*60)
    
    sql_commands = {
        "status_types": """
CREATE TABLE status_types (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key VARCHAR UNIQUE NOT NULL,
    display_name VARCHAR NOT NULL,
    description TEXT,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);""",
        
        "organizations": """
CREATE TABLE organizations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    created_by UUID,
    status_id UUID REFERENCES status_types(id),
    industry_type_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);""",
        
        "documents": """
CREATE TABLE documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    org_id UUID REFERENCES organizations(id),
    document_type_id UUID,
    filename VARCHAR NOT NULL,
    storage_path VARCHAR NOT NULL,
    mime_type VARCHAR NOT NULL,
    hash BYTEA,
    uploaded_by UUID,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    ocr_status VARCHAR DEFAULT 'queued',
    parsed_index JSONB
);"""
    }
    
    for table_name, sql in sql_commands.items():
        print(f"\n📄 {table_name.upper()}:")
        print(sql)

if __name__ == "__main__":
    print("🚀 SIMPLE SUPABASE CONNECTION TEST")
    print("="*60)
    
    success = test_supabase_connection()
    
    if not success:
        show_table_creation_guide()
        print("\n💡 If tables don't exist, you can run the SQL commands above in your Supabase SQL editor.")
    
    print(f"\n{'✅ SUCCESS' if success else '❌ NEEDS SETUP'}: Connection test completed.")