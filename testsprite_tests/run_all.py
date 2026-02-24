#!/usr/bin/env python3
import os
import sys
import subprocess
import glob

def run_tests():
    # Get the directory where this script is located
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find all test files starting with TC
    test_files = sorted(glob.glob(os.path.join(test_dir, "TC*.py")))
    
    if not test_files:
        print("No test files found in", test_dir)
        return

    print(f"Found {len(test_files)} tests to run in {test_dir}\n")
    
    passed = 0
    failed = 0
    results = []

    for test_file in test_files:
        test_name = os.path.basename(test_file)
        print(f"Running {test_name}...")
        
        try:
            # Run the test file as a subprocess
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=60 # 1 minute timeout per test
            )
            
            if result.returncode == 0:
                print(f"✅ PASSED: {test_name}")
                passed += 1
                results.append((test_name, "PASSED"))
            else:
                print(f"❌ FAILED: {test_name}")
                print(f"   Error Output:\n{result.stderr}")
                print(f"   Standard Output:\n{result.stdout}")
                failed += 1
                results.append((test_name, "FAILED"))
                
        except subprocess.TimeoutExpired:
            print(f"⚠️ TIMEOUT: {test_name}")
            failed += 1
            results.append((test_name, "TIMEOUT"))
        except Exception as e:
            print(f"❌ ERROR: {test_name} - {str(e)}")
            failed += 1
            results.append((test_name, "ERROR"))
            
        print("-" * 40)

    print("\n" + "=" * 40)
    print(f"Test Summary")
    print("=" * 40)
    print(f"Total Tests: {len(test_files)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed Tests:")
        for name, status in results:
            if status != "PASSED":
                print(f"- {name} ({status})")
        sys.exit(1)
    else:
        print("\nAll tests passed! 🚀")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
