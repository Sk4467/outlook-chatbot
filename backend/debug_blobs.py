#!/usr/bin/env python3
"""
Debug utility to test blob URL accessibility and performance
"""
import sys
import time
import httpx
from rag.vector_store import ATTACHMENTS_TABULAR_IDX

def test_blob_urls():
    """Test all blob URLs in the tabular index for accessibility"""
    print("🔍 Testing blob URL accessibility...")
    
    # Get all documents from tabular index
    try:
        result = ATTACHMENTS_TABULAR_IDX.get(limit=100)
        metadatas = result.get("metadatas", [])
        
        if not metadatas:
            print("❌ No tabular attachments found in index")
            return
        
        print(f"Found {len(metadatas)} tabular index entries")
        
        # Test each unique blob URI
        tested_uris = set()
        
        for i, meta in enumerate(metadatas):
            blob_uri = meta.get("blob_uri")
            filename = meta.get("filename", "unknown")
            
            if not blob_uri or blob_uri in tested_uris:
                continue
                
            tested_uris.add(blob_uri)
            
            print(f"\n📋 Testing {i+1}: {filename}")
            print(f"🔗 URI: {blob_uri[:100]}{'...' if len(blob_uri) > 100 else ''}")
            
            # Test HEAD request first (faster)
            try:
                start_time = time.time()
                timeout = httpx.Timeout(5.0, connect=2.0, read=5.0)
                
                with httpx.Client(timeout=timeout) as client:
                    response = client.head(blob_uri)
                    head_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        content_length = response.headers.get("content-length", "unknown")
                        print(f"✅ HEAD request OK ({head_time:.2f}s) - Size: {content_length} bytes")
                        
                        # Test actual download for small files
                        if content_length != "unknown" and int(content_length) < 1024 * 1024:  # < 1MB
                            start_time = time.time()
                            download_response = client.get(blob_uri)
                            download_time = time.time() - start_time
                            
                            if download_response.status_code == 200:
                                actual_size = len(download_response.content)
                                print(f"✅ Download OK ({download_time:.2f}s) - Actual size: {actual_size} bytes")
                            else:
                                print(f"❌ Download failed: HTTP {download_response.status_code}")
                        else:
                            print(f"⚠️  File too large for test download: {content_length} bytes")
                    else:
                        print(f"❌ HEAD request failed: HTTP {response.status_code}")
                        
            except httpx.ReadTimeout:
                print(f"⏰ Timeout - URL is slow or unresponsive")
            except httpx.ConnectTimeout:
                print(f"⏰ Connection timeout - Cannot reach server")
            except httpx.RequestError as e:
                print(f"❌ Network error: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                
        print(f"\n📊 Tested {len(tested_uris)} unique blob URLs")
        
    except Exception as e:
        print(f"❌ Failed to access tabular index: {e}")

def test_vector_store():
    """Test vector store accessibility"""
    print("\n🗄️  Testing vector store...")
    
    try:
        # Test each collection
        collections = [
            ("MAIL_BODIES", "rag.vector_store.MAIL_BODIES"),
            ("ATTACHMENTS_SEMANTIC", "rag.vector_store.ATTACHMENTS_SEMANTIC"), 
            ("ATTACHMENTS_TABULAR_IDX", "rag.vector_store.ATTACHMENTS_TABULAR_IDX")
        ]
        
        for name, collection_path in collections:
            try:
                module_path, collection_name = collection_path.rsplit(".", 1)
                module = __import__(module_path, fromlist=[collection_name])
                collection = getattr(module, collection_name)
                
                result = collection.get(limit=1)
                count = len(result.get("ids", []))
                print(f"✅ {name}: accessible ({count} items)")
                
            except Exception as e:
                print(f"❌ {name}: failed - {e}")
                
    except Exception as e:
        print(f"❌ Vector store test failed: {e}")

def check_configuration():
    """Check system configuration"""
    print("\n⚙️  Checking configuration...")
    
    try:
        from config_loader import load_config_to_env
        import os
        
        load_config_to_env()
        
        # Check API keys
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            print(f"✅ Google API key: {google_key[:10]}...")
        else:
            print("❌ Google API key not found")
            
        # Check other config
        print("✅ Configuration loaded successfully")
        
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")

if __name__ == "__main__":
    print("🔧 RAG System Debug Utility")
    print("=" * 50)
    
    check_configuration()
    test_vector_store()
    test_blob_urls()
    
    print("\n🎯 Debug Summary:")
    print("- Check the blob URL test results above")
    print("- Timeouts indicate slow/unreachable blob storage")
    print("- Large files may need streaming or chunked downloads")
    print("- Network errors suggest connectivity issues")
