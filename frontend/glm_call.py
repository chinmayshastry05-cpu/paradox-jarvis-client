"""Call GLM 5.3 via the NVIDIA NIM connector (surrogate credential), STREAMING.

Usage:
  python3 glm_call.py <prompt-file> <output-file> [--max-tokens N] [--temperature T]

Reads the prompt from <prompt-file>, calls
POST https://integrate.api.nvidia.com/v1/chat/completions with model
"z-ai/glm-5.3" and stream=true, and writes the model's code output to
<output-file>.

Streaming is required: GLM 5.3 is a reasoning model and long
non-streaming generations get their connection closed before the
response completes. Deltas arrive incrementally, keeping the
connection alive.

GLM 5.3 is a reasoning model: the final answer is in `content` deltas;
when only `reasoning_content` deltas arrive, those are used as a
fallback (the model only emitted reasoning). The credential is
injected by authd via the surrogate; it never appears in this file,
in arguments, or in logs.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# The directory containing dynamic_credentials.py is configured via
# CONNECTOR_BIN_DIR (no hardcoded absolute paths).
_connector_bin = os.environ.get("CONNECTOR_BIN_DIR")
if not _connector_bin:
    raise SystemExit(
        "CONNECTOR_BIN_DIR is not set: point it at the directory "
        "containing dynamic_credentials.py"
    )
sys.path.insert(0, _connector_bin)
from dynamic_credentials import add_surrogate_to_request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt_file")
    ap.add_argument("output_file")
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--reasoning-effort", default="low",
                    help="GLM reasoning budget: low keeps the model from spending "
                         "the whole token budget on reasoning and never emitting content.")
    args = ap.parse_args()

    with open(args.prompt_file) as f:
        prompt = f.read()

    payload = {
        "model": "z-ai/glm-5.3",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "stream": True,
    }
    request = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    add_surrogate_to_request(
        request, "custom.nvidia-nim", allowed_hosts=["integrate.api.nvidia.com"]
    )
    content_parts = []
    reasoning_parts = []
    finish = ""
    try:
        with urllib.request.build_opener(NoRedirect()).open(
            request, timeout=900
        ) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                if delta.get("content"):
                    content_parts.append(delta["content"])
                if delta.get("reasoning_content"):
                    reasoning_parts.append(delta["reasoning_content"])
                if choices[0].get("finish_reason"):
                    finish = choices[0]["finish_reason"]
    except urllib.error.HTTPError as e:
        print("HTTP ERROR", e.code, e.read().decode()[:2000], file=sys.stderr)
        raise SystemExit(1)

    text = "".join(content_parts) if content_parts else "".join(reasoning_parts)
    print(
        f"finish_reason={finish} content_chars={sum(len(p) for p in content_parts)} "
        f"reasoning_chars={sum(len(p) for p in reasoning_parts)}",
        file=sys.stderr,
    )
    with open(args.output_file, "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
