"""Correlated JSON-lines transport for reusable isolated model processes."""

from __future__ import annotations

import json
import select
import subprocess
import threading
from uuid import uuid4


class JsonLineModelTransport:
    def __init__(self, command: list[str], *, process_factory=subprocess.Popen) -> None:
        if not command or any(not str(item) for item in command):
            raise ValueError("persistent_worker_command_invalid")
        self._command = [str(item) for item in command]
        self._process_factory = process_factory
        self._process = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _start(self) -> None:
        if self.is_running:
            return
        self.close()
        self._process = self._process_factory(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            shell=False,
        )
        if self._process.stdin is None or self._process.stdout is None:
            self.close()
            raise BrokenPipeError("persistent_worker_pipe_unavailable")

    def request(self, payload: dict, *, timeout_seconds: float) -> dict:
        request_id = uuid4().hex
        with self._lock:
            self._start()
            process = self._process
            try:
                process.stdin.write(
                    json.dumps(
                        {"requestId": request_id, "payload": payload},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                process.stdin.flush()
            except (BrokenPipeError, OSError) as error:
                self.close()
                raise BrokenPipeError("persistent_worker_write_failed") from error

            readable, _, _ = select.select(
                [process.stdout], [], [], max(0.0, float(timeout_seconds))
            )
            if not readable:
                self.close()
                raise TimeoutError("persistent_worker_timeout")
            line = process.stdout.readline()
            if not line:
                self.close()
                raise BrokenPipeError("persistent_worker_closed")
            try:
                response = json.loads(line)
            except json.JSONDecodeError as error:
                self.close()
                raise BrokenPipeError("persistent_worker_invalid_json") from error
            if response.get("requestId") != request_id:
                self.close()
                raise BrokenPipeError("persistent_worker_request_mismatch")
            if response.get("ok") is not True:
                code = str(response.get("error") or "persistent_worker_failed")
                raise RuntimeError(code)
            result = response.get("result")
            if not isinstance(result, dict):
                raise BrokenPipeError("persistent_worker_result_invalid")
            return result

    def close(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        for stream in (process.stdin, process.stdout):
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
