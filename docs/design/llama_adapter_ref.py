import subprocess
import textwrap

LLAMA_BIN = "/home/hkirk/packy2/runtime/llama.cpp/build/bin/llama-cli"
MODEL_PATH = "/home/hkirk/packy2/runtime/llama.cpp/models/tinyllama-1.1b-chat-v1.0.Q4_0.gguf"

def call_llama(prompt: str, max_tokens: int = 256) -> str:
    """
    Call llama.cpp via llama-cli and return generated text.
    """
    cmd = [
        LLAMA_BIN,
        "-m", MODEL_PATH,
        "-p", prompt,
        "--n-predict", str(max_tokens),
        "--no-warmup"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return f"[LLAMA ERROR]\n{result.stderr}"

    return _extract_response(result.stdout)


def _extract_response(output: str) -> str:
    """
    Extract assistant response from llama-cli output.
    """
    marker = "<|assistant|>"
    if marker in output:
        return output.split(marker, 1)[-1].strip()
    return output.strip()
