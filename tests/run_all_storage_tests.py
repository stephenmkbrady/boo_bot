#!/usr/bin/env python3
"""
Comprehensive test runner for all storage tests
Integrates with pytest and provides clear reporting
"""

import subprocess
import sys
import os


def run_pytest_storage_tests():
    """Run storage tests using pytest"""
    print("🧪 RUNNING STORAGE TESTS WITH PYTEST")
    print("=" * 60)
    
    # Run different categories of tests
    test_commands = [
        # Unit tests (fast, no external dependencies)
        {
            "name": "Unit Tests",
            "cmd": [
                "python", "-m", "pytest", 
                "tests/test_storage_simple.py",
                "-m", "unit",
                "-v", "--tb=short"
            ],
            "description": "Core storage logic tests"
        },
        
        # Storage functionality tests
        {
            "name": "Storage Functionality Tests", 
            "cmd": [
                "python", "-m", "pytest",
                "tests/test_message_storage.py",
                "-m", "storage",
                "-v", "--tb=short"
            ],
            "description": "Message storage functionality tests"
        },
        
        # Integration tests (require boo_memories API)
        {
            "name": "Integration Tests",
            "cmd": [
                "python", "-m", "pytest",
                "tests/test_file_cycle_integration.py",
                "tests/test_automated_file_cycle.py",
                "-m", "integration", 
                "-v", "--tb=short"
            ],
            "description": "API integration and file cycle tests"
        }
    ]
    
    results = {}
    
    for test_group in test_commands:
        print(f"\n📋 Running {test_group['name']}...")
        print(f"   {test_group['description']}")
        
        try:
            result = subprocess.run(
                test_group["cmd"], 
                cwd="/app",
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"✅ {test_group['name']} PASSED")
                results[test_group['name']] = True
            else:
                print(f"❌ {test_group['name']} FAILED")
                print("Error output:")
                if result.stdout:
                    print(result.stdout[-1000:])  # Last 1000 chars
                if result.stderr:
                    print(result.stderr[-500:])   # Last 500 chars
                results[test_group['name']] = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_group['name']} TIMED OUT")
            results[test_group['name']] = False
        except Exception as e:
            print(f"❌ {test_group['name']} ERROR: {e}")
            results[test_group['name']] = False
    
    return results


def run_standalone_tests():
    """Run standalone test scripts"""
    print("\n🧪 RUNNING STANDALONE TESTS")
    print("=" * 60)
    
    standalone_tests = [
        {
            "name": "Real File Cycle Test",
            "script": "tests/test_automated_file_cycle.py",
            "description": "Test with actual test.jpg file"
        }
    ]
    
    results = {}
    
    for test in standalone_tests:
        print(f"\n📋 Running {test['name']}...")
        print(f"   {test['description']}")
        
        try:
            result = subprocess.run([
                "python", test["script"]
            ], cwd="/app", capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✅ {test['name']} PASSED")
                results[test['name']] = True
                # Show key success metrics
                if "SUCCESS: Perfect file integrity!" in result.stdout:
                    print("   🎯 File integrity verified")
                if "Cleanup complete" in result.stdout:
                    print("   🧹 Automatic cleanup successful")
            else:
                print(f"❌ {test['name']} FAILED")
                print("Output:")
                print(result.stdout[-800:] if result.stdout else "No output")
                if result.stderr:
                    print("Errors:")
                    print(result.stderr[-400:])
                results[test['name']] = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test['name']} TIMED OUT")
            results[test['name']] = False
        except Exception as e:
            print(f"❌ {test['name']} ERROR: {e}")
            results[test['name']] = False
    
    return results


def check_test_environment():
    """Check if test environment is properly set up"""
    print("🔍 CHECKING TEST ENVIRONMENT")
    print("=" * 40)
    
    checks = {
        "test.jpg exists": os.path.exists("/app/test_data/test.jpg"),
        "pytest available": True,
        "tests directory exists": os.path.exists("/app/tests"),
        "storage test files exist": all([
            os.path.exists("/app/tests/test_storage_simple.py"),
            os.path.exists("/app/tests/test_automated_file_cycle.py"),
            os.path.exists("/app/tests/test_file_cycle_integration.py")
        ])
    }
    
    # Check pytest
    try:
        result = subprocess.run(["python", "-m", "pytest", "--version"], 
                              capture_output=True, text=True, timeout=10)
        checks["pytest available"] = result.returncode == 0
    except:
        checks["pytest available"] = False
    
    # Check API availability
    try:
        import urllib.request
        import json
        
        api_key = "0DZ9a/sbgajCRmAMO+6SU2qCkw3QqTe5uJaPGa5YptA="
        req = urllib.request.Request("http://172.17.0.1:8000/health")
        req.add_header("Authorization", f"Bearer {api_key}")
        response = urllib.request.urlopen(req, timeout=5)
        health_data = json.loads(response.read().decode())
        checks["boo_memories API available"] = health_data.get("status") == "healthy"
    except:
        checks["boo_memories API available"] = False
    
    all_good = True
    for check_name, status in checks.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {check_name}")
        if not status:
            all_good = False
    
    if not all_good:
        print("\n⚠️ Some environment checks failed")
        if not checks["test.jpg exists"]:
            print("   📁 Make sure test.jpg is copied to /app/test_data/ in the container")
        if not checks["boo_memories API available"]:
            print("   🚀 Start boo_memories service: docker-compose --profile sqlite up -d")
    
    return all_good


def generate_test_report(pytest_results, standalone_results):
    """Generate comprehensive test report"""
    print("\n📊 COMPREHENSIVE TEST REPORT")
    print("=" * 60)
    
    all_results = {**pytest_results, **standalone_results}
    
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results.values() if result)
    
    print(f"📈 Summary: {passed_tests}/{total_tests} test groups passed")
    print("\n📋 Detailed Results:")
    
    for test_name, result in all_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:<35} {status}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Storage functionality is working perfectly")
        print("✅ Automated tests are ready for CI/CD")
        return True
    else:
        print(f"\n⚠️ {total_tests - passed_tests} test groups failed")
        print("🔧 Review failed tests and fix issues")
        return False


def main():
    """Main test runner"""
    print("🧪 BOO_BOT COMPREHENSIVE STORAGE TEST SUITE")
    print("=" * 60)
    print("Running all storage tests with pytest integration")
    
    # Check environment
    if not check_test_environment():
        print("\n❌ Environment checks failed - please fix issues before running tests")
        return False
    
    print("\n✅ Environment checks passed")
    
    # Run pytest tests
    pytest_results = run_pytest_storage_tests()
    
    # Run standalone tests
    standalone_results = run_standalone_tests()
    
    # Generate report
    success = generate_test_report(pytest_results, standalone_results)
    
    if success:
        print("\n🚀 All storage functionality verified!")
        print("💡 To run specific test categories:")
        print("   pytest tests/ -m unit          # Fast unit tests")
        print("   pytest tests/ -m storage       # Storage functionality")
        print("   pytest tests/ -m integration   # Integration tests")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)