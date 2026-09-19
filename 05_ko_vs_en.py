"""
[테스트 5] 로컬 모델(GLiFormer/jeff)의 한국어 성능 검증
같은 뜻의 문장을 한국어/영어로 각각 넣어 결과를 비교한다.
"""
import _env  # noqa: F401
from typesafe_sdk import Choice, Noul, TypeSafeClient

pairs = [
    ("3일째 Stripe 연동이 실패합니다. 매출이 빠지고 있어요. 빨리 봐주세요.",
     "Stripe integration has been failing for 3 days. I'm losing sales. Please help ASAP."),
    ("카드가 두 번 청구됐습니다. 환불해주세요.",
     "My card was charged twice. Please refund me."),
    ("서버가 500 에러를 계속 뱉습니다.",
     "The server keeps returning 500 errors."),
    ("안녕하세요, 잘 지내시죠?",
     "Hello, how are you?"),
]

q = {
    "urgent": Noul(instructions="Is this message urgent or time-sensitive?"),
    "dept": Choice(
        instructions="Which team should handle this?",
        criteria={"billing": "payments, refunds, invoices",
                  "technical": "bugs, outages, integrations",
                  "other": "anything else"},
    ),
}
client = TypeSafeClient()

print(f"{'언어':<4} {'문장':<48} {'urgent':>7} {'dept':<10} {'conf':>6}")
print("-" * 82)
for ko, en in pairs:
    for lang, text in (("KO", ko), ("EN", en)):
        a = client.system_one(state=text, questions=q).answers
        label = text if len(text) <= 46 else text[:45] + "…"
        print(f"{lang:<4} {label:<48} {a['urgent'].noul:>7.3f} "
              f"{a['dept'].choice:<10} {a['dept'].confidence:>6.1%}")
    print("-" * 82)
