"""
[테스트 1] Jev의 3가지 기본형(primitive)을 한 번의 호출로 확인

핵심: Jev는 '문장'을 만들지 않는다. state(평가 대상)를 주고
      questions(타입이 정해진 질문들)를 주면, 타입이 맞는 값 + 확률만 돌아온다.
"""
import _env  # noqa: F401  (.env 로더)
import json, time
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

# 평가 대상 = state. 문자열도 되고 dict/list 같은 구조체도 된다.
ticket = "3일째 Stripe 계정 연동이 계속 실패합니다. 매출이 계속 빠지고 있어요. 빨리 좀 봐주세요."

client = TypeSafeClient()

t0 = time.perf_counter()
res = client.system_one(
    state=ticket,
    questions={
        # (1) Choice = 내가 정한 보기 중 하나 고르기 -> 라우팅/분류용
        "department": Choice(
            instructions="이 문의를 어느 팀이 처리해야 하는가",
            criteria={
                "billing":   "결제, 정산, 환불 관련",
                "technical": "버그, 장애, 연동 문제",
                "sales":     "가격, 업그레이드, 신규 계정",
            },
        ),
        # (2) Score = 내가 정의한 등급 위의 연속값 -> 심각도/품질 점수용
        "frustration": Score(
            instructions="고객이 얼마나 화가 나 있는가",
            criteria=[
                "차분함, 사실만 전달",           # 0
                "불만스럽지만 예의는 지킴",        # 1
                "매우 화남, 강한 표현 사용",       # 2
            ],
        ),
        # (3) Noul = 예/아니오의 '확률' -> 게이트/플래그용
        "is_urgent": Noul(
            instructions="이 메시지는 긴급하거나 시간에 민감한가",
            criteria={"true": "명시적으로 시간 압박이 있음", "false": "긴급함이 드러나지 않음"},
        ),
    },
)
elapsed = (time.perf_counter() - t0) * 1000

a = res.answers
print("=" * 62)
print("입력(state):", ticket)
print("=" * 62)
print(f"[Choice] department  = {a['department'].choice}   (confidence {a['department'].confidence:.3f})")
for opt, p in sorted(a["department"].probabilities.items(), key=lambda kv: -kv[1]):
    print(f"           {opt:<10} {p:6.1%} {'█' * int(p * 30)}")
print(f"[Score ] frustration = {a['frustration'].score:.3f} / 2.0   (confidence {a['frustration'].confidence:.3f})")
print(f"           범례: {a['frustration'].legend}")
print(f"[Noul  ] is_urgent   = {a['is_urgent'].noul:.3f}  (1에 가까울수록 '예')")
print("-" * 62)
print(f"지연시간 {elapsed:.0f} ms | 입력 토큰 {res.usage.input_tokens} | 모델 {res.model}")
print(f"비용: ${res.usage.input_tokens / 1_000_000 * 0.042:.8f}  (100만 토큰당 $0.042)")
print()
print(">>> 서버가 돌려준 원본 JSON <<<")
print(json.dumps(res.model_dump(), indent=2, ensure_ascii=False))
