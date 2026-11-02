"""Windows process tree ownership; imported only on Windows."""

import msvcrt
import os
import subprocess

import pywintypes
import win32api
import win32con
import win32event
import win32job
import win32process

from installation import external_environment, external_runtime


def _api(function, *args):
    try:
        return function(*args)
    except pywintypes.error as error:
        raise OSError(str(error)) from error


class WindowsProcess:
    def __init__(self, command, cwd, log):
        self.job = None
        self.handle = None
        self.returncode = None
        thread = None
        handles = []
        try:
            # pywin32 requires a string; an empty name creates an unnamed job.
            self.job = win32job.CreateJobObject(None, "")
            info = win32job.QueryInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation)
            info["BasicLimitInformation"]["LimitFlags"] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation, info)
            current = win32api.GetCurrentProcess()
            with open(os.devnull, "rb") as devnull:
                for file in (devnull, log):
                    handles.append(win32api.DuplicateHandle(
                        current, msvcrt.get_osfhandle(file.fileno()), current,
                        0, True, win32con.DUPLICATE_SAME_ACCESS))
                startup = win32process.STARTUPINFO()
                startup.dwFlags |= win32con.STARTF_USESTDHANDLES
                startup.hStdInput = handles[0]
                startup.hStdOutput = handles[1]
                startup.hStdError = handles[1]
                with external_runtime():
                    self.handle, thread, self.pid, _ = win32process.CreateProcess(
                        command[0], subprocess.list2cmdline(command), None, None, True,
                        win32process.CREATE_SUSPENDED | win32process.CREATE_NO_WINDOW,
                        external_environment(), str(cwd), startup)
                # Assign before resuming: even immediate children belong to our job.
                win32job.AssignProcessToJobObject(self.job, self.handle)
                win32process.ResumeThread(thread)
        except (OSError, pywintypes.error) as error:
            if self.handle is not None:
                win32api.TerminateProcess(self.handle, 1)
            self.close()
            raise OSError(f"Could not start a managed Windows process: {error}") from error
        finally:
            if thread is not None:
                thread.Close()
            for handle in handles:
                handle.Close()

    def poll(self):
        if self.returncode is None and self.handle is not None:
            if _api(win32event.WaitForSingleObject, self.handle, 0) == win32event.WAIT_OBJECT_0:
                self.returncode = _api(win32process.GetExitCodeProcess, self.handle)
        return self.returncode

    def kill(self):
        if self.job is not None:
            _api(win32job.TerminateJobObject, self.job, 1)

    def wait(self):
        if self.handle is not None:
            _api(win32event.WaitForSingleObject, self.handle, win32event.INFINITE)
        return self.poll()

    def close(self):
        if self.job is not None:
            _api(self.job.Close)
            self.job = None
        if self.handle is not None:
            self.wait()
            _api(self.handle.Close)
            self.handle = None
