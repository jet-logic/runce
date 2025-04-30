#!/usr/bin/env python3
import os
import time
import subprocess
from pathlib import Path


def run_test_process():
    """Test launching and managing a long-running process with RunCE"""
    print("🚀 Starting RunCE singleton process test...")

    # 1. Create a test script that runs indefinitely
    test_script = Path("infinite_runner.py")
    test_script.write_text(
        """#!/usr/bin/env python3
import time, os
print("🔄 Test process started (PID: {})".format(os.getpid()))
while True:
    print("⏳ Still running...")
    time.sleep(5)
"""
    )
    test_script.chmod(0o755)

    process_id = "test-process-" + str(int(time.time()))

    # 2. Launch the process using RunCE
    print(f"\n✅ Launching process with ID: {process_id}")
    subprocess.run(
        [
            "python",
            "-m",
            "runce",
            "run",
            "--id",
            process_id,
            "python3",
            str(test_script),
        ]
    )

    # 3. Verify it's running
    time.sleep(2)
    print("\n🔍 Checking process status:")
    subprocess.run(["python", "-m", "runce", "status", process_id])

    # 4. Attempt to launch duplicate (should fail)
    print("\n🚫 Attempting to launch duplicate:")
    subprocess.run(
        ["python", "-m", "runce", "run", "--id", process_id, str(test_script)]
    )

    # 5. Show logs
    print("\n📜 Tailing process output:")
    subprocess.run(["python", "-m", "runce", "tail", process_id, "-n", "5"])

    # 6. Let it run for a while
    print("\n⏳ Letting process run for 2 seconds...")
    print("   (Try running 'runce status' in another terminal)")
    time.sleep(2)

    # 7. Clean up
    print("\n🧹 Cleaning up:")
    subprocess.run(["python", "-m", "runce", "kill", process_id])
    subprocess.run(["python", "-m", "runce", "clean"])
    test_script.unlink()

    print("\n🎉 Test completed successfully!")


if __name__ == "__main__":
    try:
        run_test_process()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
