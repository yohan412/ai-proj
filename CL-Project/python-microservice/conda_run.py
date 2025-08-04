import subprocess, json, os, base64
from typing import List

def _try_parse_b64_json(lines: List[str]) -> dict:
    """
    뒤에서부터 탐색하며 base64‑JSON 파싱이 성공하는 첫 줄을 반환.
    실패하면 {} 리턴
    """
    for ln in reversed(lines):
        ln = ln.strip()
        if not ln:
            continue

        # base64 → bytes → UTF‑8 → JSON
        try:
            raw = base64.b64decode(ln, validate=True)
            return json.loads(raw.decode("utf-8"))
        except Exception:   # binascii.Error | UnicodeDecodeError | JSONDecodeError
            continue

    # 전혀 찾지 못한 경우
    print("[WARN] base64‑JSON 파싱 실패: 후보 없음", file=sys.stderr, flush=True)
    return {}

def run_in_conda(env_name: str, module_name: str, *args):
    cmd = ["conda", "run", "-n", env_name, "python", "-u", "-m",
           module_name, *args]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"        # 한글 깨짐 방지

    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        # shell=True,
        text=True,               # ← str 로 읽음
        encoding="utf-8",
        bufsize=1,
        env=env
    ) as proc:
        lines = []               # ★ 문자열 리스트
        last_line = ""

        for line in proc.stdout:
            print(line, end="")          # 실시간 echo
            lines.append(line)
            last_line = line.rstrip("\n")

        if proc.wait() != 0:
            raise subprocess.CalledProcessError(
                proc.returncode, cmd, output="".join(lines))
        
        return _try_parse_b64_json(lines)
        
