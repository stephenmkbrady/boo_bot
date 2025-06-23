"""
Test crypto dependencies that matrix-nio needs
Run this in your container to diagnose the issue
"""

import sys
import subprocess

def test_system_libs():
    """Test if required system libraries are available"""
    print("🔍 Testing system libraries...")
    
    # Test libolm
    try:
        result = subprocess.run(['pkg-config', '--exists', 'olm'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = subprocess.run(['pkg-config', '--modversion', 'olm'], 
                                   capture_output=True, text=True)
            print(f"✅ libolm found: {version.stdout.strip()}")
        else:
            print("❌ libolm NOT found via pkg-config")
    except FileNotFoundError:
        print("❌ pkg-config not available")
    
    # Test direct library access
    try:
        import ctypes
        lib = ctypes.CDLL("libolm.so.3")
        print("✅ libolm.so.3 can be loaded directly")
    except OSError as e:
        print(f"❌ Cannot load libolm.so.3: {e}")
        try:
            lib = ctypes.CDLL("libolm.so.2")
            print("⚠️ Only libolm.so.2 available (too old for modern matrix-nio)")
        except OSError:
            print("❌ No libolm library found")

def test_python_crypto():
    """Test Python crypto dependencies"""
    print("\n🐍 Testing Python crypto libraries...")
    
    # Test olm import
    try:
        import olm
        print(f"✅ python-olm imported successfully: {olm.__version__}")
    except ImportError as e:
        print(f"❌ python-olm import failed: {e}")
    
    # Test cryptography
    try:
        import cryptography
        print(f"✅ cryptography imported: {cryptography.__version__}")
    except ImportError as e:
        print(f"❌ cryptography import failed: {e}")

def test_matrix_nio_crypto():
    """Test matrix-nio crypto functionality"""
    print("\n🔐 Testing matrix-nio crypto...")
    
    try:
        from nio.crypto import Olm
        print("✅ matrix-nio crypto import successful")
        
        # Try to create an Olm account (basic crypto test)
        try:
            from nio.crypto.olm_machine import OlmMachine
            print("✅ OlmMachine can be imported")
        except Exception as e:
            print(f"❌ OlmMachine creation failed: {e}")
            
    except ImportError as e:
        print(f"❌ matrix-nio crypto import failed: {e}")

def test_matrix_nio_basic():
    """Test basic matrix-nio functionality"""
    print("\n📡 Testing basic matrix-nio...")
    
    try:
        from nio import AsyncClient
        print("✅ AsyncClient import successful")
        
        # Try to create a client
        client = AsyncClient("https://matrix.org", "@test:matrix.org")
        print("✅ AsyncClient creation successful")
        
        print(f"   Client configured for: {client.homeserver}")
        print(f"   User: {client.user_id}")
        print(f"   Encryption enabled: {client.olm is not None}")
        
    except ImportError as e:
        print(f"❌ AsyncClient import failed: {e}")
    except Exception as e:
        print(f"❌ AsyncClient creation failed: {e}")

def main():
    print("🔬 Matrix Crypto Dependency Test")
    print("=" * 50)
    
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    test_system_libs()
    test_python_crypto()
    test_matrix_nio_crypto()
    test_matrix_nio_basic()
    
    print("\n" + "=" * 50)
    print("💡 ANALYSIS:")
    print("If libolm is missing or too old, that's likely your sync issue.")
    print("Modern matrix-nio needs libolm 3.x for encryption to work properly.")
    print("Even if you disable encryption, some sync functionality may fail.")

if __name__ == "__main__":
    main()