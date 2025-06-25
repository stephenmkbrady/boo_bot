#!/usr/bin/env python3
"""
Test runner for bot storage functionality tests
This script can be run in CI/CD or manually for comprehensive testing
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path


def check_environment():
    """Check if the testing environment is properly set up"""
    print("🔍 Checking test environment...")
    
    issues = []
    
    # Check if we're in the right directory
    if not os.path.exists('/app/boo_bot.py'):
        issues.append("Not running in bot container (missing /app/boo_bot.py)")
    
    # Check if required modules are available
    try:
        import pytest
        print("✅ pytest available")
    except ImportError:
        issues.append("pytest not installed")
    
    try:
        import nio
        print("✅ matrix-nio available")
    except ImportError:
        issues.append("matrix-nio not installed")
    
    # Check if test files exist
    test_files = [
        '/app/tests/test_message_storage.py',
        '/app/tests/test_file_cycle_integration.py'
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"✅ {os.path.basename(test_file)} found")
        else:
            issues.append(f"Test file missing: {test_file}")
    
    return issues


def check_services():
    """Check if required services are running"""
    print("\n🔍 Checking required services...")
    
    services = {
        'boo_memories': 'http://localhost:8000/health',
    }
    
    api_key = "0DZ9a/sbgajCRmAMO+6SU2qCkw3QqTe5uJaPGa5YptA="
    service_status = {}
    
    for service_name, health_url in services.items():
        try:
            result = subprocess.run([
                'curl', '-s', '-f', '--max-time', '5',
                '-H', f'Authorization: Bearer {api_key}',
                health_url
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {service_name} is running")
                service_status[service_name] = True
            else:
                print(f"❌ {service_name} not responding")
                service_status[service_name] = False
        except Exception as e:
            print(f"❌ {service_name} check failed: {e}")
            service_status[service_name] = False
    
    return service_status


def run_unit_tests():
    """Run unit tests for message storage"""
    print("\n🧪 Running unit tests...")
    
    cmd = [
        'python', '-m', 'pytest',
        '/app/tests/test_message_storage.py',
        '-v', '--tb=short', '--no-header'
    ]
    
    try:
        result = subprocess.run(cmd, cwd='/app', capture_output=True, text=True)
        
        print("📋 Unit test output:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        if result.returncode == 0:
            print("✅ Unit tests PASSED")
            return True
        else:
            print("❌ Unit tests FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error running unit tests: {e}")
        return False


def run_integration_tests(service_status):
    """Run integration tests if services are available"""
    print("\n🧪 Running integration tests...")
    
    if not service_status.get('boo_memories', False):
        print("⚠️ Skipping integration tests - boo_memories service not available")
        return True  # Don't fail CI/CD for missing services
    
    cmd = [
        'python', '-m', 'pytest',
        '/app/tests/test_file_cycle_integration.py',
        '-v', '--tb=short', '--no-header'
    ]
    
    try:
        result = subprocess.run(cmd, cwd='/app', capture_output=True, text=True)
        
        print("📋 Integration test output:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        if result.returncode == 0:
            print("✅ Integration tests PASSED")
            return True
        else:
            print("❌ Integration tests FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        return False


def run_file_cycle_test():
    """Run the standalone file cycle test"""
    print("\n🧪 Running standalone file cycle test...")
    
    try:
        result = subprocess.run([
            'python', '/app/tests/test_file_cycle_integration.py'
        ], cwd='/app', capture_output=True, text=True)
        
        print("📋 File cycle test output:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        if result.returncode == 0:
            print("✅ File cycle test PASSED")
            return True
        else:
            print("❌ File cycle test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error running file cycle test: {e}")
        return False


def generate_test_report(results):
    """Generate a test report"""
    print("\n📊 TEST REPORT")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
    
    print(f"\n📈 Summary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️ Some tests failed")
        return False


def main():
    """Main test runner"""
    print("🧪 BOO_BOT STORAGE TESTS")
    print("=" * 50)
    print("Comprehensive testing for message and media storage functionality")
    
    # Check environment
    env_issues = check_environment()
    if env_issues:
        print("\n❌ Environment issues:")
        for issue in env_issues:
            print(f"   • {issue}")
        print("\nPlease fix these issues before running tests")
        return False
    
    print("✅ Environment check passed")
    
    # Check services
    service_status = check_services()
    
    # Run tests
    results = {}
    
    # Unit tests (always run)
    results['Unit Tests'] = run_unit_tests()
    
    # Integration tests (conditional)
    if service_status.get('boo_memories', False):
        results['Integration Tests'] = run_integration_tests(service_status)
        results['File Cycle Test'] = run_file_cycle_test()
    else:
        print("\n⚠️ Skipping integration tests - services not available")
        print("   To run full tests, ensure boo_memories service is running:")
        print("   docker-compose --profile sqlite up -d")
    
    # Generate report
    success = generate_test_report(results)
    
    if success:
        print("\n🚀 Storage functionality is working correctly!")
    else:
        print("\n🔧 Some storage functionality needs attention")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)