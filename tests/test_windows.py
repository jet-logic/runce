import sys
import unittest
import os
import signal
import time
import ctypes
from typing import Optional
from subprocess import Popen, run


# Functions to test (copied from your code)
# def check_pid(pid: int) -> bool:
#     kernel32 = ctypes.windll.kernel32
#     PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
#     process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
#     if process:
#         kernel32.G
#         kernel32.CloseHandle(process)
#         return True
#     return False


def check_pid(pid: int) -> bool:
    """Properly checks if a process is running by verifying exit code."""
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    STILL_ACTIVE = 0x103  # (259)

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False

    try:
        exit_code = ctypes.c_ulong()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return exit_code.value == STILL_ACTIVE
        return False
    finally:
        kernel32.CloseHandle(handle)


# def kill_pid(
#     pid: int, sig: Optional[int] = signal.SIGTERM, process_group: Optional[bool] = None
# ) -> bool:
#     PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
#     PROCESS_TERMINATE = 0x0001
#     STILL_ACTIVE = 0x103
#     handle = ctypes.windll.kernel32.OpenProcess(
#         PROCESS_TERMINATE + PROCESS_QUERY_LIMITED_INFORMATION, False, pid
#     )
#     if handle:
#         exit_code = ctypes.c_ulong()
#         exit_code.value = 9999
#         if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
#             if exit_code.value != STILL_ACTIVE:
#                 return False
#         print(f"kill_pid {pid}", "A", exit_code.value)
#     else:
#         err = ctypes.get_last_error()
#         print(f"kill_pid {pid}", "B", err)
#         if err == 87:  # ERROR_INVALID_PARAMETER (no such process)
#             return False
#         elif err == 0:
#             return False
#         else:
#             raise ctypes.WinError(err)
#     result = ctypes.windll.kernel32.TerminateProcess(handle, -1)
#     print(f"kill_pid {pid}", "result", result)
#     error = 0 if result else ctypes.get_last_error()
#     print(f"kill_pid {pid}", "get_last_error", error)
#     ctypes.windll.kernel32.CloseHandle(handle)
#     if error:
#         if check_pid(pid):
#             raise ctypes.WinError(error)
#     return True


def kill_pid(
    pid: int, sig: Optional[int] = None, process_group: Optional[bool] = None
) -> bool:
    """
    Kills a Windows process with precise return behavior:
    - True:  Successfully terminated the process
    - False: Process was already dead or doesn't exist
    - Raises OSError: If termination fails due to permissions/other errors
    """
    PROCESS_TERMINATE = 0x0001
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 0x103
    kernel32 = ctypes.windll.kernel32

    # Phase 1: Check process existence and state
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        err = ctypes.get_last_error()
        if err == 87:  # ERROR_INVALID_PARAMETER (no such process)
            return False
        if err == 0:
            return False
        raise ctypes.WinError(err)  # Permission error or other issues

    try:
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise ctypes.WinError(ctypes.get_last_error())

        if exit_code.value != STILL_ACTIVE:
            return False  # Already dead
    finally:
        kernel32.CloseHandle(handle)

    # Phase 2: Attempt termination
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        err = ctypes.get_last_error()
        if err in (87, 5):  # ERROR_INVALID_PARAMETER or ERROR_ACCESS_DENIED
            return False  # Process died or we lost permissions
        raise ctypes.WinError(err)

    try:
        if not kernel32.TerminateProcess(handle, -1):
            err = ctypes.get_last_error()
            if err == 5:  # ERROR_ACCESS_DENIED
                raise ctypes.WinError(err)  # We have handle but can't terminate
            return False  # Process likely died
        return True  # Successfully terminated
    finally:
        kernel32.CloseHandle(handle)


def task_kill(pid):
    cp = run(["taskkill", "/PID", str(pid), "/F"])
    if cp.returncode == 128:
        return False
    assert cp.returncode == 0


class TestPidUtilsWindows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not sys.platform.startswith("win"):
            raise unittest.SkipTest("Test only runs on Windows")
        """Start a dummy process to test against"""
        cls.dummy_proc = Popen(
            ["cmd.exe", "/c", "timeout 60"]
        )  # Will run for 60 seconds

    @classmethod
    def tearDownClass(cls):
        """Clean up dummy process if still running"""
        if cls.dummy_proc.poll() is None:
            cls.dummy_proc.kill()

    def test_check_pid(self):
        """Test check_pid with existing and non-existing PIDs"""
        # Test with real PID
        self.assertTrue(check_pid(self.dummy_proc.pid))

        # Test with invalid PID
        self.assertFalse(check_pid(999999))  # Unlikely to exist

    def test_kill_pid(self):
        """Test kill_pid functionality"""
        # Create new process to kill
        victim_proc = Popen(["cmd.exe", "/c", "timeout 60"])

        # Verify it's running
        self.assertTrue(check_pid(victim_proc.pid), f"check_pid {victim_proc.pid}")

        # Kill it
        self.assertTrue(kill_pid(victim_proc.pid), f"kill_pid {victim_proc.pid}")

        # Give it a moment to die
        time.sleep(0.1)

        # Verify it's gone
        self.assertFalse(check_pid(victim_proc.pid), f"check_pid {victim_proc.pid}")

        # Test killing non-existent process
        self.assertFalse(kill_pid(999999), f"kill_pid {victim_proc.pid}")

    def test_kill_already_dead(self):
        """Test killing a process that just exited"""
        temp_proc = Popen(["cmd.exe", "/c", "exit 0"])
        temp_pid = temp_proc.pid
        temp_proc.terminate()
        temp_proc.wait()  # Wait for natural exit
        # self.assertFalse(check_pid(temp_pid), f"check_pid {temp_pid}")
        # Should return False (process already dead)
        self.assertFalse(kill_pid(temp_pid), f"kill_pid {temp_pid}")

    def test_tail_n(self):
        proc = run(
            ["tail", "-n", "10", "README.md"],
            capture_output=True,
            text=True,
        )
        self.assertRegex(proc.stdout, r"(?xi) \W+ flake8 \W+ runce \W+", proc.stdout)

    def test_tail_powershell(self):
        proc = run(
            ["powershell", "-c", "Get-Content -Tail 10 README.md"],
            capture_output=True,
            text=True,
        )
        self.assertRegex(proc.stdout, r"(?xi) \W+ flake8 \W+ runce \W+")

    def test_tail_pwsh(self):
        proc = run(
            ["pwsh", "-c", 'Write-Host -NoNewline "123"; Write-Error -NoNewline "456"'],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.stdout, r"123")
        self.assertEqual(proc.stderr, r"456")

    def test_tail_pwsh(self):
        proc = run(
            ["pwsh", "-c", "$input | Write-Output"],
            capture_output=True,
            text=True,
            input="QWERTY",
        )
        self.assertEqual(proc.stdout, "QWERTY\n")
        self.assertEqual(proc.stderr, r"")

    def test_emoji(self):
        try:
            # Try printing a test emoji
            print("print emoji: 😊")
        except UnicodeEncodeError:
            print("No emoji :-(")
            self.assertTrue(1)
        else:
            print("Has emoji :-)")
            self.assertTrue(1)

    def test_emoji_2(self):
        sys.stdout.buffer.write("Write emoji: 😊\n".encode())


if __name__ == "__main__":
    unittest.main()
