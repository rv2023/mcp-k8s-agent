import subprocess
import json
import time

def send_message(proc, message):
    payload = json.dumps(message)
    framed = f"Content-Length: {len(payload)}\r\n\r\n{payload}"
    proc.stdin.write(framed)
    proc.stdin.flush()

p = subprocess.Popen(
    ["python", "server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

time.sleep(0.5)

# Send tools/list request
send_message(
    p,
    {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }
)

# --- Read headers ---
content_length = None

while True:
    line = p.stdout.readline()
    if not line:
        raise RuntimeError("Server closed connection")
    line = line.strip()
    if line == "":
        break
    if line.lower().startswith("content-length"):
        content_length = int(line.split(":")[1].strip())

if content_length is None:
    raise RuntimeError("No Content-Length header received")

# --- Read body ---
body = p.stdout.read(content_length)

print("RESPONSE JSON:")
print(body)
