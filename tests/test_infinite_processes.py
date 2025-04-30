#!/usr/bin/env python3
import pytest
import subprocess
import time
from pathlib import Path
import sys
import os


@pytest.fixture
def infinite_script(tmp_path):
    """Fixture that creates the test script"""
    script = tmp_path / "infinite_loop.sh"
    script.write_text(
        """#!/bin/bash
while true; do
    echo "$(date) - Process $1 running...";
    sleep 1;
done
"""
    )
    script.chmod(0o755)
    return script


def run_parallel_process_test(script_path, run_time=4):
    """Core test logic that can be called from pytest or main"""
    process_ids = [f"run-{i}" for i in range(1, 4)]
    processes = []

    def run_rnce(*args, stdout_only=False):
        """Helper to run python -m runce with stderr capture"""
        result = subprocess.run(
            ["python", "-m", "runce", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # print("args", args)
        if stdout_only:
            return result.stdout
        # Combine stdout and stderr for verification
        return result.stdout + result.stderr

    try:
        run_rnce("clean")
        # Launch 3 processes
        # print("process_ids", process_ids)
        for pid in process_ids:
            proc = subprocess.Popen(
                [
                    "python",
                    "-m",
                    "runce",
                    "run",
                    "--id",
                    pid,
                    "--",
                    str(script_path),
                    pid[-1],
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # print("proc", proc.pid, proc)
            processes.append(proc)
            time.sleep(0.3)  # Stagger startup

        # print(run_rnce("list"))
        # Verify they're running
        for pid in process_ids:
            output = run_rnce("status", pid)
            # print("output", output, pid)
            assert pid in output
            assert "Running" in output

        # Test singleton behavior
        for pid in process_ids:
            output = run_rnce("run", "--id", pid, str(script_path), "dupe")
            assert "found" in output.lower()

        # Let them run for specified time
        print(f"\n⏳ Running processes for {run_time} seconds...")
        time.sleep(run_time)

        # Verify output
        for pid in process_ids:
            output = run_rnce("tail", pid, "-n", "2")
            assert "running" in output.lower()
        run_rnce("kill", "run-2")
        if 1:
            for x in run_rnce("status").strip().splitlines():
                if "Running" in x:
                    assert "run-1" in x or "run-3" in x
                elif "Absent" in x:
                    assert "run-2" in x
                print(x)
        run_rnce("restart", "run-2")
        if 1:
            ids = list(process_ids)
            for x in run_rnce("list").strip().splitlines():
                if "Running" in x:
                    for id in ids:
                        if id in x:
                            ids.remove(id)
                            break
                print(x)
            assert len(ids) == 0
        assert (
            "Process 1 running"
            in run_rnce("tail", "un-1", "-n", "3", stdout_only=True).strip()
        )
        for x in run_rnce(
            "tail", "run-3", "--tab", "-n", "4", "--header", "no"
        ).splitlines():
            assert "Process 3 running" in x and x.startswith("\t")
        run_rnce("kill", "run-1")
        for x in run_rnce("clean").strip().splitlines():
            assert "Cleaning" in x and "1" in x

        return True

    finally:
        # Cleanup
        for pid in process_ids:
            run_rnce("kill", pid)
        for proc in processes:
            proc.terminate()


# Pytest entry point
def test_parallel_processes(infinite_script):
    """Pytest test function"""
    assert run_parallel_process_test(infinite_script, run_time=2)  # Shorter for pytest


# Standalone script entry point
if __name__ == "__main__":
    # Create temp script in current directory
    script_path = Path("/tmp/temp_infinite_loop.sh")
    try:
        script_path.write_text(
            """#!/bin/bash
while true; do
    echo "$(date) - Process $1 running...";
    sleep 1;
done
"""
        )
        script_path.chmod(0o755)

        print("🚀 Starting infinite process test (standalone mode)")
        success = run_parallel_process_test(script_path, run_time=2)
        print("✅ Test passed" if success else "❌ Test failed")
        sys.exit(0 if success else 1)

    finally:
        if script_path.exists():
            script_path.unlink()
            pass
