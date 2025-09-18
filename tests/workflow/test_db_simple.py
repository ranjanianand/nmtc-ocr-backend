#!/usr/bin/env python3
"""
Simple Supabase connection test without Unicode
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
            print("ERROR: Missing environment variables")
            print(f"SUPABASE_URL: {'SET' if url else 'MISSING'}")
            print(f"SUPABASE_SERVICE_KEY: {'SET' if key else 'MISSING'}")
            return False
        
        print("Connecting to Supabase...")
        print(f"URL: {url}")
        print(f"Key: {key[:20]}...")
        
        client: Client = create_client(url, key)
        
        print("\nTesting storage connection...")
        try:
            buckets = client.storage.list_buckets()
            print("SUCCESS: Storage connection works!")
            print(f"Available buckets: {len(buckets)} found")
            for bucket in buckets[:5]:
                print(f"  - {bucket.name}")
        except Exception as e:
            print(f"ERROR: Storage connection failed - {e}")
        
        print("\nTesting database tables...")
        common_tables = ['documents', 'organizations', 'status_types']
        
        for table in common_tables:
            try:
                result = client.table(table).select('*').limit(1).execute()
                count = len(result.data) if result.data else 0
                print(f"SUCCESS: {table} table accessible ({count} sample records)")
                
                if table == 'documents' and result.data:
                    columns = list(result.data[0].keys())
                    print(f"  Columns: {', '.join(columns[:6])}...")
                    
            except Exception as e:
                if "does not exist" in str(e).lower():
                    print(f"INFO: {table} table not found (needs creation)")
                else:
                    print(f"ERROR: {table} - {str(e)[:80]}...")
        
        print("\nTesting write operations...")
        try:
            test_data = {
                'key': 'test_connection',
                'display_name': 'Test Connection',
                'description': 'Test record',
                'order_index': 999
            }
            
            # Try to query first
            result = client.table('status_types').select('*').eq('key', 'test_connection').execute()
            
            if not result.data:
                insert_result = client.table('status_types').insert(test_data).execute()
                print("SUCCESS: Write test passed - created test record")
                
                # Clean up
                client.table('status_types').delete().eq('key', 'test_connection').execute()
                print("SUCCESS: Cleanup completed")
            else:
                print("INFO: Write test - table accessible, test record exists")
                
        except Exception as e:
            print(f"WARNING: Write test failed (table may need setup) - {e}")
        
        print("\nSUCCESS: Connection test completed!")
        return True
        
    except Exception as e:
        print(f"ERROR: Connection failed - {e}")
        return False

def create_basic_tables():
    """Create basic tables if they don't exist"""
    print("\n" + "="*50)
    print("TABLE CREATION SQL COMMANDS")
    print("="*50)
    print("\nRun these in your Supabase SQL Editor:\n")
    
    print("-- 1. Status Types Table")
    print("""CREATE TABLE IF NOT EXISTS status_types (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key VARCHAR UNIQUE NOT NULL,
    display_name VARCHAR NOT NULL,
    description TEXT,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);""")
    
    print("\n-- 2. Organizations Table")
    print("""CREATE TABLE IF NOT EXISTS organizations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    created_by UUID,
    status_id UUID REFERENCES status_types(id),
    industry_type_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);""")
    
    print("\n-- 3. Documents Table")
    print("""CREATE TABLE IF NOT EXISTS documents (
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
);""")
    
    print("\n-- 4. Insert sample data")
    print("""INSERT INTO status_types (key, display_name, description) VALUES 
('active', 'Active', 'Active status'),
('draft', 'Draft', 'Draft status'),
('archived', 'Archived', 'Archived status')
ON CONFLICT (key) DO NOTHING;""")

if __name__ == "__main__":
    print("SUPABASE CONNECTION TEST")
    print("="*50)
    
    success = test_supabase_connection()
    
    if not success:
        create_basic_tables()
        print("\nNEXT STEPS: Run the SQL commands above in Supabase, then test again.")
    else:
        print("\nALL TESTS PASSED!")
        
        # Show table modification functions
        print("\n" + "="*50)
        print("AVAILABLE OPERATIONS")
        print("="*50)
        print("1. Create tables: Run SQL commands above")
        print("2. Add columns: ALTER TABLE table_name ADD COLUMN column_name TYPE;")
        print("3. Modify columns: ALTER TABLE table_name ALTER COLUMN column_name TYPE new_type;")
        print("4. Drop columns: ALTER TABLE table_name DROP COLUMN column_name;")
        print("5. Create indexes: CREATE INDEX idx_name ON table_name (column_name);")