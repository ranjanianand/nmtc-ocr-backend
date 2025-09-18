#!/usr/bin/env python3
"""Debug script to check document processing status and detection results"""

import asyncio
import json
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.supabase_service import SupabaseService

async def main():
    document_id = "9e7cd7af-834b-4bc7-94c9-6e97833d166e"
    
    try:
        supabase_service = SupabaseService()
        document = await supabase_service.get_document(document_id)
        
        if not document:
            print(f"Document {document_id} not found")
            return
            
        print(f"Document found: {document['filename']}")
        print(f"Status: {document.get('ocr_status')}")
        print(f"Storage path: {document.get('storage_path')}")
        print(f"Uploaded: {document.get('uploaded_at')}")
        
        # Check parsed_index for detection results
        parsed_index = document.get('parsed_index', {})
        print(f"\nParsed Index Structure:")
        print(json.dumps(parsed_index, indent=2, default=str))
        
        # Check specifically for detection results
        if 'detection_results' in parsed_index:
            detection_results = parsed_index['detection_results']
            print(f"\nDetection Results Found:")
            print(f"   Document Type: {detection_results.get('document_type_detected')}")
            print(f"   Confidence: {detection_results.get('confidence')}")
            print(f"   Reasoning: {detection_results.get('reasoning', 'Not provided')}")
            print(f"   Primary Indicators: {len(detection_results.get('primary_indicators', []))}")
            print(f"   Secondary Indicators: {len(detection_results.get('secondary_indicators', []))}")
        else:
            print(f"\nNo detection results found in parsed_index")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())