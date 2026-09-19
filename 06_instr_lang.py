"""
[테스트 6] 가설 검증: state는 한국어여도 되지만, instructions/criteria는 영어여야 하는가?
같은 state(한국어)에 대해 질문문만 KO/EN으로 바꿔 2x2로 비교한다.
"""
import _env  # noqa: F401
from typesafe_sdk import Choice, Noul, TypeSafeClient

state_ko = "3일째 Stripe 계정 연동이 계속 실패합니다. 매출이 계속 빠지고 있어요. 빨리 좀 봐주세요."
state_en = "Stripe integration has been failing for 3 days. I'm losing sales. Please help ASAP."

q_ko = {
    "urgent": Noul(instructions="이 메시지는 긴급하거나 시간에 민감한가"),
    "dept": Choice(instructions="이 문의를 어느 팀이 처리해야 하는가",
                   criteria={"billing": "결제, 정산, 환불 관련",
                             "technical": "버그, 장애, 연동 문제",
                             "sales": "가격, 업그레이드, 신규 계정"}),
}
q_en = {
    "urgent": Noul(instructions="Is this message urgent or time-sensitive?"),
    "dept": Choice(instructions="Which team should handle this?",
                   criteria={"billing": "payments, invoicing, refunds",
                             "technical": "bugs, outages, integrations",
                             "sales": "pricing, upgrades, new accounts"}),
}

client = TypeSafeClient()
print(f"{'state':<6} {'질문문':<8} {'urgent':>8}  {'dept':<10} {'conf':>7}")
print("-" * 48)
for sname, state in (("KO", state_ko), ("EN", state_en)):
    for qname, q in (("KO", q_ko), ("EN", q_en)):
        a = client.system_one(state=state, questions=q).answers
        print(f"{sname:<6} {qname:<8} {a['urgent'].noul:>8.3f}  "
              f"{a['dept'].choice:<10} {a['dept'].confidence:>6.1%}")
print("-" * 48)
print("기대: urgent는 1에 가까워야 정답, dept는 technical(또는 billing)")
