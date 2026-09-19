"""
[테스트 3] 속도와 비용을 실제로 재본다 (순차 vs 병렬)

핵심: Jev의 존재 이유는 '싸고 빠른 결정'이다.
      숫자로 직접 확인한다.
"""
import _env  # noqa: F401  (.env 로더)
import time, statistics
from concurrent.futures import ThreadPoolExecutor
from typesafe_sdk import Noul, TypeSafeClient

msgs = [
    "환불 요청합니다", "서버가 죽었어요 지금 당장", "가격표 좀 보내주세요",
    "로그인이 안 됩니다", "계약서 검토 부탁드립니다", "청구서가 이상합니다",
    "API 키를 재발급하고 싶습니다", "그냥 인사드립니다",
    "결제가 3번 중복됐습니다 급합니다", "문서 링크가 깨져 있어요",
]
q = {"is_urgent": Noul(instructions="Is this message urgent or time-sensitive?")}
client = TypeSafeClient()

def ask(m):
    t0 = time.perf_counter()
    r = client.system_one(state=m, questions=q)
    return (time.perf_counter() - t0) * 1000, r

# --- 순차 ---
t0 = time.perf_counter()
seq = [ask(m) for m in msgs]
seq_total = time.perf_counter() - t0
lat = [x[0] for x in seq]

# --- 병렬 (10개 동시) ---
t0 = time.perf_counter()
with ThreadPoolExecutor(max_workers=10) as ex:
    par = list(ex.map(ask, msgs))
par_total = time.perf_counter() - t0

tokens = sum(r.usage.input_tokens for _, r in seq)
cost = tokens / 1_000_000 * 0.042

print(f"{'메시지':<34} {'긴급도':>7} {'ms':>7}")
print("-" * 52)
for m, (ms, r) in zip(msgs, seq):
    label = m if len(m) <= 32 else m[:31] + "…"
    print(f"{label:<34} {r.answers['is_urgent'].noul:>7.3f} {ms:>7.0f}")

print("-" * 52)
print(f"건당 지연시간   중앙값 {statistics.median(lat):.0f} ms  |  최소 {min(lat):.0f}  최대 {max(lat):.0f}")
print(f"순차 {len(msgs)}건 총 {seq_total:.2f} s   →   병렬 {len(msgs)}건 총 {par_total:.2f} s  ({seq_total/par_total:.1f}배 빠름)")
print(f"총 입력 토큰 {tokens} → 비용 ${cost:.8f}")
print(f"환산: 100만 건 처리 시 약 ${cost / len(msgs) * 1_000_000:.2f}")
