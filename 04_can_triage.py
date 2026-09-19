"""
[테스트 4] 실제 업무에 붙이면? — BMS/CAN 이벤트 분류 (state를 '구조체'로 주는 예)

핵심 2가지:
  1) state는 문자열뿐 아니라 dict/list(=장비 상태 스냅샷)도 된다.
  2) 질문 여러 개를 한 번에 던지면 한 번의 호출로 모두 답이 온다.
     -> 규칙(if문)으로 짜기엔 애매하고, LLM 쓰기엔 느리고 비싼 자리에 들어간다.
"""
import _env  # noqa: F401  (.env 로더)
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

# 배터리팩에서 올라온 이벤트 스냅샷 3건
events = [
    {
        "설명": "주행 중 셀 전압 편차 급증",
        "state": {
            "timestamp": "2026-09-19T14:22:03Z",
            "pack_voltage_V": 398.2,
            "cell_voltage_min_V": 3.02, "cell_voltage_max_V": 4.11,
            "cell_delta_mV": 1090,
            "pack_current_A": -180.5,
            "temp_max_C": 47.8, "temp_min_C": 31.2,
            "soc_percent": 41,
            "active_dtc": ["P0AFA", "P0A80"],
            "can_bus_load_percent": 62,
            "recent_frames": [
                "0x18F 8 02 1A 3F 00 00 00 00 11",
                "0x1A0 8 FF FF 0C 05 00 00 00 00",
            ],
        },
    },
    {
        "설명": "주차 중 정상 유휴 상태",
        "state": {
            "timestamp": "2026-09-19T03:10:55Z",
            "pack_voltage_V": 402.0,
            "cell_voltage_min_V": 3.71, "cell_voltage_max_V": 3.74,
            "cell_delta_mV": 30,
            "pack_current_A": -0.3,
            "temp_max_C": 24.1, "temp_min_C": 23.5,
            "soc_percent": 78,
            "active_dtc": [],
            "can_bus_load_percent": 12,
            "recent_frames": ["0x18F 8 00 00 00 00 00 00 00 00"],
        },
    },
    {
        "설명": "CAN 통신 자체가 불안정",
        "state": {
            "timestamp": "2026-09-19T09:41:12Z",
            "pack_voltage_V": 399.8,
            "cell_voltage_min_V": 3.68, "cell_voltage_max_V": 3.75,
            "cell_delta_mV": 70,
            "pack_current_A": -12.0,
            "temp_max_C": 29.0, "temp_min_C": 27.4,
            "soc_percent": 65,
            "active_dtc": ["U0111"],
            "can_bus_load_percent": 94,
            "bus_error_counters": {"tx_err": 128, "rx_err": 96, "bus_off_events": 2},
            "recent_frames": ["0x1A0 8 FF FF FF FF FF FF FF FF"],
        },
    },
]

questions = {
    "fault_domain": Choice(
        instructions="What is the primary fault domain in this battery pack snapshot?",
        criteria={
            "cell_imbalance": "cell voltage spread, balancing failure",
            "thermal":        "overheating, cooling failure, temperature anomaly",
            "communication":  "CAN bus errors, bus-off, lost communication",
            "normal":         "no fault, within normal operating range",
        },
    ),
    "severity": Score(
        instructions="Severity from a field-service perspective",
        criteria=[
            "normal, no action needed",
            "monitor, check at next service",
            "inspect before next drive",
            "stop immediately, safety risk",
        ],
    ),
    "needs_immediate_stop": Noul(
        instructions="Must the vehicle be taken out of service immediately?",
        criteria={"true": "imminent safety risk", "false": "safe to keep operating"},
    ),
    "is_sensor_glitch": Noul(
        instructions="Could this be a false reading caused by a sensor or communication fault rather than a real failure?",
    ),
}

client = TypeSafeClient()
for ev in events:
    r = client.system_one(state=ev["state"], questions=questions)
    a = r.answers
    print("=" * 66)
    print(f"■ {ev['설명']}")
    print(f"  DTC={ev['state']['active_dtc'] or '없음'}  "
          f"셀편차={ev['state']['cell_delta_mV']}mV  "
          f"버스부하={ev['state']['can_bus_load_percent']}%")
    print("-" * 66)
    print(f"  문제 영역   : {a['fault_domain'].choice}  (확신도 {a['fault_domain'].confidence:.1%})")
    for opt, p in sorted(a["fault_domain"].probabilities.items(), key=lambda kv: -kv[1]):
        print(f"                {opt:<16} {p:6.1%} {'█' * int(p * 24)}")
    print(f"  심각도      : {a['severity'].score:.2f} / 3.00  (확신도 {a['severity'].confidence:.1%})")
    print(f"  즉시 정지?  : {a['needs_immediate_stop'].noul:.3f}")
    print(f"  센서 오류?  : {a['is_sensor_glitch'].noul:.3f}")
    print(f"  [토큰 {r.usage.input_tokens} / ${r.usage.input_tokens/1_000_000*0.042:.8f}]")
print("=" * 66)
print("질문 4개를 호출 1번으로 처리했다. 이게 Jev의 사용 패턴이다.")
