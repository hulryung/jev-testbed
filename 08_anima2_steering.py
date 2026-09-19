"""
[테스트 8] anima2의 실제 스티어링 결정을 jeff에 던져본다.

anima2/mage_life.py::decide_candidates 는 매지가 지금 할 수 있는 경제 행동을
우선순위 순으로 돌려준다: buy_reagent > fetch_gold > bank_gold.
현재 _LifeClient._work 는 후보 '이름만' Haiku에 보내 한 단어를 고르게 한다 (상태 없음).

예측 (실행 전에 적음):
  P1. 이름만 주면(현재 방식) 세 후보 확률이 거의 균등, confidence < 0.30  → 정보가 없다.
  P2. 상태를 '문장'으로 주면 명백한 상황에서 confidence 가 오르고 선택이 상황을 따른다.
  P3. 같은 상태를 '숫자 JSON'으로 주면 P2보다 평탄해진다 (BMS 테스트에서 본 한계).
"""
import _env  # noqa: F401
from typesafe_sdk import Choice, TypeSafeClient

# anima2/skills 의 description 문구를 그대로 가져온 후보 사전
CANDS = {
    "buy_reagent": "Buy a batch of reagents from the mage vendor and return.",
    "fetch_gold":  "Pick up a delivered purse of gold from the ground into the pack.",
    "bank_gold":   "Deposit surplus gold with the banker and return.",
}
Q = lambda: {"pick": Choice(
    instructions="Which single economy action should this Ultima Online mage do first, right now?",
    criteria=CANDS)}

# 상수는 mage_life.py 의 이름을 따름 (LOW_REAGENTS, REAGENT_BATCH_COST, FETCH_GOLD_PACK_CAP, BANK_RESERVE)
scenarios = [
    ("시약 거의 없음, 지갑은 멀리",   dict(ash=1,  gold=90,  purse_tiles=6, reserve_over=0)),
    ("시약 살짝 부족, 지갑 1타일 옆", dict(ash=14, gold=120, purse_tiles=1, reserve_over=0)),
    ("시약 충분, 금 넘침(예치 필요)", dict(ash=40, gold=400, purse_tiles=0, reserve_over=270)),
    ("전부 애매하게 걸림",           dict(ash=13, gold=130, purse_tiles=3, reserve_over=5)),
]
def as_text(s):
    parts = [f"Reagent pouch: {s['ash']} sulfurous ash (reorder line is 15; a mage with none cannot cast).",
             f"Gold in pack: {s['gold']} (a reagent batch costs 100; pack cap before fetching more is 180).",
             (f"A delivered purse of gold is lying on the ground {s['purse_tiles']} tile(s) away."
              if s['purse_tiles'] else "No purse on the ground."),
             (f"Gold exceeds the bank reserve by {s['reserve_over']}." if s['reserve_over']
              else "Gold is at or below the bank reserve.")]
    return " ".join(parts)
def as_json(s):
    return {"sulfurous_ash": s["ash"], "low_reagents": 15, "gold": s["gold"], "reagent_batch_cost": 100,
            "fetch_gold_pack_cap": 180, "purse_on_ground_tiles": s["purse_tiles"],
            "gold_over_bank_reserve": s["reserve_over"]}

c = TypeSafeClient()
def show(label, state):
    a = c.system_one(state=state, questions=Q()).answers["pick"]
    p = a.probabilities
    bar = "  ".join(f"{k.split('_')[0]:>5}={p[k]:.2f}" for k in CANDS)
    print(f"  {label:<26} → {a.choice:<12} conf={a.confidence:.2f}   {bar}")

print("=" * 96)
print("A. 현재 방식 재현 — 후보 이름만, 상태 없음 (_LifeClient._work 와 동일한 정보량)")
print("-" * 96)
show("(상태 없음)", "The character can do any ONE of these right now, all currently possible and safe.")
print()
print("B. 상태를 문장으로 렌더링해서 함께 제공")
print("-" * 96)
for name, s in scenarios: show(name, as_text(s))
print()
print("C. 같은 상태를 숫자 JSON 으로 제공")
print("-" * 96)
for name, s in scenarios: show(name, as_json(s))
print("=" * 96)
print("규칙(decide_candidates)의 답은 항상 우선순위 1순위 = 후보가 있으면 buy_reagent.")
