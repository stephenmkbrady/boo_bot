# BOO_BOT Storage Testing Suite

Comprehensive automated tests for message and media storage functionality.

## Test Files Overview

### Core Tests
- **`test_automated_file_cycle.py`** - Real file testing with actual test.jpg
- **`test_storage_simple.py`** - Core storage functionality tests
- **`test_file_cycle_integration.py`** - API integration tests
- **`test_message_storage.py`** - Comprehensive storage logic tests

### Test Runner
- **`run_storage_tests.py`** - CI/CD test runner (in parent directory)

## Running Tests

### Quick Test (Real File)
```bash
# Test with actual test.jpg file - includes automatic cleanup
python tests/test_automated_file_cycle.py
```

### Full Test Suite
```bash
# From bot container
python run_storage_tests.py

# Or with pytest
python -m pytest tests/test_storage_simple.py -v
python -m pytest tests/test_file_cycle_integration.py -v
```

### CI/CD Integration
```bash
# In your CI pipeline
docker exec boo_bot python /app/run_storage_tests.py
```

## What Gets Tested

### ✅ Core Functionality
- [x] File integrity (hash verification)
- [x] MIME type detection (PNG, JPEG, text files)
- [x] Complete upload/download cycles
- [x] Database integration
- [x] Error handling
- [x] Service health checking

### ✅ File Formats Supported
- [x] JPEG files (including EXIF data preservation)
- [x] PNG files
- [x] Text files with Unicode
- [x] Binary files

### ✅ Real Data Testing
- [x] Uses actual test.jpg file (1.4MB)
- [x] Verifies perfect file integrity
- [x] Tests complete storage workflow
- [x] Automatic cleanup after testing

### ✅ CI/CD Ready
- [x] Clear pass/fail results
- [x] Detailed error reporting
- [x] Service dependency checking
- [x] Automatic file cleanup
- [x] No manual intervention required

## Test Results Summary

The automated test suite verifies that:
1. **Bot stores ALL incoming messages** (text + media) ✅
2. **Files maintain perfect integrity** during storage/retrieval ✅
3. **Multiple file formats supported** without corruption ✅
4. **Database integration works correctly** ✅
5. **Error handling is robust** ✅
6. **API authentication works properly** ✅

## Cleanup Policy

All tests automatically clean up:
- Temporary files created during testing
- Downloaded test files (test_received.*)
- Partial files from failed tests
- Database test entries (optional)

## Integration Notes

These tests complement the existing test suite and can be run:
- **Standalone** - Individual test files
- **As part of pytest suite** - Full integration
- **In CI/CD pipelines** - Automated validation
- **Manual validation** - Developer testing

The storage functionality is now fully tested and ready for production use.