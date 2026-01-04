import json
import subprocess
import time


def _initialize(proc):
    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "clientCapabilities": {},
                "clientInfo": {
                    "name": "phase2-smoke-test",
                    "version": "0.1",
                },
            },
        },
    )
    _recv(proc)

    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {},
        },
    )


def _send(proc, msg):
    payload = json.dumps(msg).encode("utf-8")
    framed = (
        b"Content-Length: "
        + str(len(payload)).encode("ascii")
        + b"\r\n\r\n"
        + payload
    )
    proc.stdin.write(framed)
    proc.stdin.flush()


def _recv(proc):
    content_length = None

    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("Server closed connection")

        line = line.strip()
        if line == b"":
            break

        if line.lower().startswith(b"content-length"):
            content_length = int(line.split(b":")[1].strip())

    if content_length is None:
        raise RuntimeError("No Content-Length header received")

    body = proc.stdout.read(content_length)
    return json.loads(body.decode("utf-8"))


def main():
    p = subprocess.Popen(
        ["python", "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(0.5)

    _initialize(p)

    # 1) Ensure delete tool is present
    _send(p, {"jsonrpc": "2.0", "method": "tools/list", "id": 1})
    tools = _recv(p)
    tool_names = [t["name"] for t in tools["result"]["tools"]]
    assert "k8s_delete" in tool_names, f"k8s_delete not found, tools={tool_names}"

    # 2) Delete without approval must fail (gate)
    _send(
        p,
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 2,
            "params": {
                "name": "k8s_delete",
                "arguments": {
                    "namespace": "default",
                    "group": "",
                    "version": "v1",
                    "plural": "pods",
                    "name": "does-not-matter",
                    "approved": False,
                },
            },
        },
    )
    resp = _recv(p)
    text = resp["result"]["content"][0]["text"]
    assert "approved=true" in text or "blocked" in text.lower(), text

    print("Phase 2 smoke test passed ✅")
    p.terminate()


if __name__ == "__main__":
    main()
