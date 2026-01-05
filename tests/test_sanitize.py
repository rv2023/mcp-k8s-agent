import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sanitize import sanitize_output


def test_redacts_simple_token():
    raw = "TOKEN=abc123"
    out = sanitize_output(tool_name="k8s_pod_logs", raw=raw)

    assert "abc123" not in out
    assert "[REDACTED: token]" in out


def test_redacts_jwt():
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def"
    out = sanitize_output(tool_name="k8s_pod_logs", raw=raw)

    assert "eyJhbGci" not in out
    assert "REDACTED" in out


def test_high_entropy_redaction():
    raw = "SOMETHING=QWxhZGRpbjpvcGVuIHNlc2FtZQ==" * 3
    out = sanitize_output(tool_name="k8s_get", raw=raw)

    assert "QWxhZGRpb" not in out
    assert "high-entropy" in out.lower()


def test_truncation():
    raw = "\n".join([f"line {i}" for i in range(1000)])
    out = sanitize_output(tool_name="k8s_pod_logs", raw=raw)

    assert "Output truncated" in out
    assert out.count("\n") < 600


def test_deterministic_output():
    raw = "password=foo token=bar"
    out1 = sanitize_output(tool_name="k8s_list_events", raw=raw)
    out2 = sanitize_output(tool_name="k8s_list_events", raw=raw)

    assert out1 == out2

print("✅ sanitize tests passed")
