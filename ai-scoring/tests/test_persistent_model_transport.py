import sys

import pytest

from app.services.media_evidence.persistent_model_transport import (
    JsonLineModelTransport,
)


def _worker_script(tmp_path, body):
    script = tmp_path / "worker.py"
    script.write_text(body, encoding="utf-8")
    return script


def test_reuses_one_process_and_correlates_json_responses(tmp_path):
    script = _worker_script(
        tmp_path,
        """import json, os, sys
for line in sys.stdin:
    request=json.loads(line)
    print(json.dumps({'requestId':request['requestId'],'ok':True,'result':{'pid':os.getpid(),'value':request['payload']['value']}}), flush=True)
""",
    )
    transport = JsonLineModelTransport([sys.executable, str(script)])
    try:
        first = transport.request({"value": 1}, timeout_seconds=1)
        second = transport.request({"value": 2}, timeout_seconds=1)
        assert first["pid"] == second["pid"]
        assert [first["value"], second["value"]] == [1, 2]
    finally:
        transport.close()


def test_timeout_terminates_unresponsive_process(tmp_path):
    script = _worker_script(
        tmp_path,
        """import sys, time
for line in sys.stdin:
    time.sleep(2)
""",
    )
    transport = JsonLineModelTransport([sys.executable, str(script)])
    with pytest.raises(TimeoutError, match="persistent_worker_timeout"):
        transport.request({"value": 1}, timeout_seconds=0.02)
    assert transport.is_running is False


def test_mismatched_response_id_is_treated_as_broken_protocol(tmp_path):
    script = _worker_script(
        tmp_path,
        """import json, sys
for line in sys.stdin:
    print(json.dumps({'requestId':'wrong','ok':True,'result':{}}), flush=True)
""",
    )
    transport = JsonLineModelTransport([sys.executable, str(script)])
    try:
        with pytest.raises(BrokenPipeError, match="persistent_worker_request_mismatch"):
            transport.request({}, timeout_seconds=1)
    finally:
        transport.close()
