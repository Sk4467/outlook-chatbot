#!/usr/bin/env python3
"""
Quick test to check if blob downloads are working
"""
import httpx
import time

def test_download(url: str):
    """Test a specific download URL"""
    print(f"Testing: {url}")
    
    try:
        timeout = httpx.Timeout(30.0, connect=10.0, read=30.0)
        start_time = time.time()
        
        with httpx.Client(timeout=timeout) as client:
            print("Starting download...")
            response = client.get(url)
            download_time = time.time() - start_time
            
            print(f"Status: {response.status_code}")
            print(f"Time: {download_time:.2f}s")
            print(f"Size: {len(response.content)} bytes")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✅ Download successful")
                return True
            else:
                print(f"❌ HTTP error: {response.status_code}")
                return False
                
    except httpx.ReadTimeout:
        print("❌ Read timeout")
        return False
    except httpx.ConnectTimeout:
        print("❌ Connection timeout")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Test with the specific URL that's failing
    test_url = "http://localhost:8000/gmail/message/515/attachments/0/download?user=2"
    
    print("🔍 Testing blob download functionality")
    print("=" * 50)
    
    success = test_download(test_url)
    
    if success:
        print("\n✅ Downloads are working - issue might be elsewhere")
    else:
        print("\n❌ Download issue confirmed - check server or network")
        print("\nSuggestions:")
        print("1. Check if backend server is running on port 8000")
        print("2. Verify the attachment exists for message 515")
        print("3. Check if user 2 has valid credentials")
        print("4. Try downloading through browser first")
