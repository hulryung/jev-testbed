"""
[테스트 7] 로컬 모델의 한계선 찾기: 숫자(JSON) vs 문장(자연어)
같은 3개 상황을 (A) 숫자 스냅샷 (B) 서술 문장 으로 각각 넣어 판별력을 비교한다.
"""
import _env  # noqa: F401
from typesafe_sdk import Choice, TypeSafeClient

numeric = [
    {"cell_delta_mV": 1090, "temp_max_C": 47.8, "can_bus_load_percent": 62,
     "bus_off_events": 0, "active_dtc": ["P0AFA"]},
    {"cell_delta_mV": 30, "temp_max_C": 24.1, "can_bus_load_percent": 12,
     "bus_off_events": 0, "active_dtc": []},
    {"cell_delta_mV": 70, "temp_max_C": 29.0, "can_bus_load_percent": 94,
     "bus_off_events": 2, "active_dtc": ["U0111"]},
]
verbal = [
    "Cell voltage spread is very large at over 1000 mV. Temperatures are elevated. The CAN bus is healthy.",
    "All cells are tightly balanced, temperatures are cool, the bus is quiet, and there are no fault codes.",
    "The CAN bus is saturated and has gone bus-off twice with a lost-communication fault code. Cells are balanced and cool.",
]
expected = ["cell_imbalance", "normal", "communication"]

q = {"fault": Choice(
    instructions="What is the primary fault domain in this battery pack snapshot?",
    criteria={"cell_imbalance": "cell voltage spread, balancing failure",
              "thermal": "overheating, cooling failure",
              "communication": "CAN bus errors, bus-off, lost communication",
              "normal": "no fault, within normal operating range"})}

client = TypeSafeClient()
print(f"{'입력형태':<10} {'정답':<15} {'모델 답':<15} {'conf':>6}  판정")
print("-" * 62)
hits = {"숫자(JSON)": 0, "문장(자연어)": 0}
for kind, data in (("숫자(JSON)", numeric), ("문장(자연어)", verbal)):
    for st, exp in zip(data, expected):
        a = client.system_one(state=st, questions=q).answers["fault"]
        ok = a.choice == exp
        hits[kind] += ok
        print(f"{kind:<10} {exp:<15} {a.choice:<15} {a.confidence:>5.1%}  {'O' if ok else 'X'}")
    print("-" * 62)
for k, v in hits.items():
    print(f"{k:<12} 정답 {v}/3")
