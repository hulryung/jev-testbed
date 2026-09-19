"""같은 폴더의 .env 파일에서 TYPESAFE_API_KEY를 읽어 환경변수로 넣어준다."""
import os, pathlib, sys

_p = pathlib.Path(__file__).with_name(".env")
if _p.exists():
    for _line in _p.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))

if not os.environ.get("TYPESAFE_API_KEY"):
    sys.exit(
        "TYPESAFE_API_KEY 가 없습니다.\n"
        "  https://console.typesafe.ai/keys 에서 키를 발급받아\n"
        "  이 폴더의 .env 파일에 다음과 같이 저장하세요:\n"
        "      TYPESAFE_API_KEY=sk-..."
    )
