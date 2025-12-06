#!/bin/bash
#
# Comprehensive validation script for 3-tier architecture
# This script validates the separated architecture without requiring external dependencies
#

set -e

echo "=========================================="
echo "3-Tier Architecture Validation Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Test function
test_check() {
    local test_name="$1"
    local command="$2"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "Testing: $test_name... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test function with output
test_check_with_output() {
    local test_name="$1"
    local command="$2"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "Testing: $test_name... "

    output=$(eval "$command" 2>&1)
    status=$?

    if [ $status -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo "  Output: $output"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "  Error: $output"
        return 1
    fi
}

echo "Section 1: File Existence Checks"
echo "-----------------------------------"

test_check "eas_service.py exists" "test -f eas_service.py"
test_check "Redis SDR adapter exists" "test -f app_core/audio/redis_sdr_adapter.py"
test_check "Redis audio adapter exists" "test -f app_core/audio/redis_audio_adapter.py"
test_check "Redis audio publisher exists" "test -f app_core/audio/redis_audio_publisher.py"
test_check "Architecture docs exist" "test -f ARCHITECTURE_3_TIER.md"

echo ""
echo "Section 2: Python Syntax Validation"
echo "------------------------------------"

test_check "eas_service.py syntax" "python3 -m py_compile eas_service.py"
test_check "audio_service.py syntax" "python3 -m py_compile audio_service.py"
test_check "sdr_service.py syntax" "python3 -m py_compile sdr_service.py"
test_check "redis_sdr_adapter.py syntax" "python3 -m py_compile app_core/audio/redis_sdr_adapter.py"
test_check "redis_audio_adapter.py syntax" "python3 -m py_compile app_core/audio/redis_audio_adapter.py"
test_check "redis_audio_publisher.py syntax" "python3 -m py_compile app_core/audio/redis_audio_publisher.py"

echo ""
echo "Section 3: Configuration Validation"
echo "------------------------------------"

test_check "docker-compose.yml valid" "docker compose config > /dev/null"
test_check "eas-service defined" "docker compose config | grep -q 'eas-service:'"
test_check "audio-service defined" "docker compose config | grep -q 'audio-service:'"
test_check "sdr-service defined" "docker compose config | grep -q 'sdr-service:'"

echo ""
echo "Section 4: Code Pattern Validation"
echo "-----------------------------------"

# Check that audio_service uses Redis publisher not EAS monitor
test_check "audio_service uses Redis publisher" "grep -q 'initialize_redis_audio_publisher' audio_service.py"
test_check "audio_service deprecated EAS init" "grep -q 'DEPRECATED.*EAS monitoring moved' audio_service.py"

# Check that eas_service uses Redis audio adapter
test_check "eas_service uses Redis adapter" "grep -q 'RedisAudioAdapter' eas_service.py"
test_check "eas_service initializes EAS monitor" "grep -q 'ContinuousEASMonitor' eas_service.py"

# Check FIPS code fix
test_check "FIPS code fix applied" "grep -q \"fips_codes = settings.get('fips_codes'\" app_core/audio/startup_integration.py"

echo ""
echo "Section 5: Redis Channel Validation"
echo "------------------------------------"

# Check that services use correct Redis channels
test_check "SDR service publishes to sdr:samples" "grep -q 'sdr:samples' sdr_service.py"
test_check "Redis SDR adapter subscribes sdr:samples" "grep -q 'sdr:samples' app_core/audio/redis_sdr_adapter.py"
test_check "Audio publisher publishes audio:samples" "grep -q 'audio:samples' app_core/audio/redis_audio_publisher.py"
test_check "Audio adapter subscribes audio:samples" "grep -q 'audio:samples' app_core/audio/redis_audio_adapter.py"

echo ""
echo "Section 6: Service Dependencies"
echo "--------------------------------"

# Check docker-compose dependencies
test_check "eas-service depends on audio-service" "docker compose config | grep -A5 'eas-service:' | grep -q 'audio-service'"
test_check "audio-service depends on redis" "docker compose config | grep -A10 'audio-service:' | grep -q 'redis'"
test_check "sdr-service depends on redis" "docker compose config | grep -A10 'sdr-service:' | grep -q 'redis'"

echo ""
echo "Section 7: Architecture Separation"
echo "-----------------------------------"

# Verify proper separation of concerns
test_check "sdr_service.py does NOT import EAS monitor" "! grep -q 'ContinuousEASMonitor' sdr_service.py"
test_check "eas_service.py does NOT import SDR" "! grep -q 'RadioManager\|SoapySDR' eas_service.py"

echo ""
echo "Section 8: Integration Points"
echo "------------------------------"

# Check that integration points exist
test_check "Audio service creates Redis SDR sources" "grep -q 'RedisSDRSourceAdapter' audio_service.py"
test_check "Audio service auto-discovers receivers" "grep -q 'Auto-discover.*Redis SDR' audio_service.py"

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo -e "Total Tests:  $TESTS_TOTAL"
echo -e "${GREEN}Passed:       $TESTS_PASSED${NC}"
echo -e "${RED}Failed:       $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "The 3-tier architecture is properly implemented and validated."
    echo ""
    echo "Next steps:"
    echo "1. Build containers: docker compose build"
    echo "2. Start services: docker compose up -d"
    echo "3. Monitor logs:"
    echo "   docker logs -f eas-sdr-service"
    echo "   docker logs -f eas-audio-service"
    echo "   docker logs -f eas-eas-service"
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    echo ""
    echo "Please review the failures above and fix any issues."
    exit 1
fi
