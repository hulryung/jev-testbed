"""
[테스트 2] confidence(확신도)로 '자동처리 vs 사람에게 넘김'을 코드로 가르기

핵심: Jev는 답만 주는 게 아니라 '얼마나 확신하는지'를 같이 준다.
      그래서 애매한 건(=confidence 낮음) 자동으로 사람에게 넘길 수 있다.
      LLM은 애매해도 자신있게 한 문장을 뱉는다. 이게 결정적 차이다.
"""
import _env  # noqa: F401  (.env 로더)
from typesafe_sdk import Choice, TypeSafeClient

THRESHOLD = 0.70  # 이 값 미만이면 사람이 본다

tickets = [
    "카드 결제가 두 번 청구됐어요. 환불해주세요.",                    # 명백히 billing
    "API가 500 에러를 계속 뱉습니다. 로그 첨부합니다.",                # 명백히 technical
    "요금제 올리면 지금 쓰는 웹훅 연동도 같이 늘어나나요?",             # 애매함: sales? technical?
    "안녕하세요",                                                    # 정보 없음
]

client = TypeSafeClient()
q = {
    "department": Choice(
        instructions="Which team should handle this?",
        criteria={
            "billing":   "payments, invoicing, refunds",
            "technical": "bugs, outages, integrations",
            "sales":     "pricing, upgrades, new accounts",
        },
    )
}

print(f"{'문의':<42} {'판단':<10} {'확신도':>7}  처리")
print("-" * 80)
auto = escalated = 0
for t in tickets:
    ans = client.system_one(state=t, questions=q).answers["department"]
    if ans.confidence >= THRESHOLD:
        action, auto = "자동 라우팅", auto + 1
    else:
        action, escalated = "사람이 확인 ←", escalated + 1
    label = t if len(t) <= 40 else t[:39] + "…"
    print(f"{label:<42} {ans.choice:<10} {ans.confidence:>6.1%}  {action}")

print("-" * 80)
print(f"자동 처리 {auto}건 / 사람 확인 {escalated}건  (임계값 {THRESHOLD:.0%})")
print("→ 임계값을 올리면 정확도가 오르고 자동화율이 떨어진다. 이 조절이 핵심.")
