"""
[테스트 11] Laya (ModernBERT-large 421M, System 1 decision engine) — jeff/Qwen과 같은 프로브 3종.

예측 (실행 전에 적음): 인코더 계열이므로 jeff와 같은 모양 — 화제/유무는 읽고(BMS 서술문 일부),
크기·임계값(경제 스티어링 ash=1 vs 40)과 화용 판단(캐릭터 이탈)은 못 읽을 것. 만약 이긴다면
"jeff만의 한계"였다는 뜻이고, 같이 지면 "인코더 계열의 한계"로 확정.
"""
import time
from laya import Router

r = Router(preload=True)

def choice(state, question, options):
    t0 = time.perf_counter()
    a = r.predict(state, {"pick": {"type": "choice", "instructions": question, "criteria": options}})["answers"]["pick"]
    return a["choice"], a["probabilities"], a.get("confidence", 0.0), (time.perf_counter() - t0) * 1000

def noul(state, question, criteria=None):
    q = {"type": "noul", "instructions": question}
    if criteria: q["criteria"] = criteria
    t0 = time.perf_counter()
    return r.predict(state, {"b": q})["answers"]["b"]["noul"], (time.perf_counter() - t0) * 1000

# ---------- 프로브 1: 경제 스티어링 (08과 동일) ----------
CANDS = {"buy_reagent": "Buy a batch of reagents from the mage vendor and return.",
         "fetch_gold":  "Pick up a delivered purse of gold from the ground into the pack.",
         "bank_gold":   "Deposit surplus gold with the banker and return."}
QS = "Which single economy action should this Ultima Online mage do first, right now?"
scen = [("시약 거의 없음, 지갑은 멀리",   dict(ash=1,  gold=90,  purse_tiles=6, reserve_over=0)),
        ("시약 살짝 부족, 지갑 1타일 옆", dict(ash=14, gold=120, purse_tiles=1, reserve_over=0)),
        ("시약 충분, 금 넘침(예치 필요)", dict(ash=40, gold=400, purse_tiles=0, reserve_over=270)),
        ("전부 애매하게 걸림",           dict(ash=13, gold=130, purse_tiles=3, reserve_over=5))]
def as_text(s):
    return " ".join([f"Reagent pouch: {s['ash']} sulfurous ash (reorder line is 15; a mage with none cannot cast).",
        f"Gold in pack: {s['gold']} (a reagent batch costs 100; pack cap before fetching more is 180).",
        (f"A delivered purse of gold is lying on the ground {s['purse_tiles']} tile(s) away." if s['purse_tiles'] else "No purse on the ground."),
        (f"Gold exceeds the bank reserve by {s['reserve_over']}." if s['reserve_over'] else "Gold is at or below the bank reserve.")])
def as_json(s):
    return {"sulfurous_ash": s["ash"], "low_reagents": 15, "gold": s["gold"], "reagent_batch_cost": 100,
            "fetch_gold_pack_cap": 180, "purse_on_ground_tiles": s["purse_tiles"], "gold_over_bank_reserve": s["reserve_over"]}
lat = []
print("=" * 96); print("프로브 1 — 경제 스티어링 (Laya)  [Qwen: fetch/fetch/bank/fetch, jeff: fetch/fetch/bank(0.42)/fetch]"); print("-" * 96)
for label, state in [("(상태 없음)", "The character can do any ONE of these right now, all currently possible and safe.")] + [(n, as_text(s)) for n, s in scen] + [(n + " [JSON]", as_json(s)) for n, s in scen]:
    ch, pr, cf, ms = choice(state, QS, CANDS); lat.append(ms)
    print(f"  {label:<32} → {ch:<12} conf={cf:.2f}   " + "  ".join(f"{k.split('_')[0]:>5}={pr[k]:.2f}" for k in CANDS) + f"   {ms:.0f}ms")

# ---------- 프로브 2: 캐릭터 이탈 Noul (09와 동일) ----------
QN = ("Does this line break character by revealing or behaving as an AI assistant, language model, or chatbot "
      "(refusing as an assistant, mentioning being an AI, lacking access to the game) instead of speaking as a person living in a medieval fantasy world?")
cases = [("As an AI language model, I cannot roleplay violence.", True), ("I'm an AI assistant and don't have access to a game world.", True),
         ("I'm not able to help with that request.", True), ("I don't have real-time access to your inventory or the server.", True),
         ("I cannot afford a new pickaxe until I sell this ore.", False), ("I cannot find the forge in this fog. Grimm hates fog.", False),
         ("As an apprentice I ruined more ingots than I saved.", False), ("Iron today is as an old friend — heavy and honest.", False),
         ("Spare a coin for an aid to a tired miner?", False), ("Take an aim at the ridge; the good ore hides there.", False),
         ("Hail, friend. Grimm greets you.", False), ("The vein runs clean today. Heavy and pure.", False),
         ("Begging thy pardon, I've no boards to spare this morning.", False), ("Three daggers sold. The banker can have the rest.", False)]
print(); print("=" * 96); print("프로브 2 — 캐릭터 이탈 Noul (Laya)  [Qwen 11/14, jeff 6/14, 키워드 6/14]"); print("-" * 96)
ok = 0
for text, truth in cases:
    p, ms = noul(text, QN, {"true": "speaks as an AI/assistant/model, or refuses in assistant voice", "false": "stays in character as a person in the game world"}); lat.append(ms)
    v = p >= 0.5; ok += (v == truth)
    print(f"  {text[:56]:<58} {str(truth):<5} P(yes)={p:.2f}  {'O' if v == truth else 'X'}")
print(f"  정확도 {ok}/14")

# ---------- 프로브 3: BMS 4지선다 (07과 동일) ----------
numeric = [{"cell_delta_mV": 1090, "temp_max_C": 47.8, "can_bus_load_percent": 62, "bus_off_events": 0, "active_dtc": ["P0AFA"]},
           {"cell_delta_mV": 30, "temp_max_C": 24.1, "can_bus_load_percent": 12, "bus_off_events": 0, "active_dtc": []},
           {"cell_delta_mV": 70, "temp_max_C": 29.0, "can_bus_load_percent": 94, "bus_off_events": 2, "active_dtc": ["U0111"]}]
verbal = ["Cell voltage spread is very large at over 1000 mV. Temperatures are elevated. The CAN bus is healthy.",
          "All cells are tightly balanced, temperatures are cool, the bus is quiet, and there are no fault codes.",
          "The CAN bus is saturated and has gone bus-off twice with a lost-communication fault code. Cells are balanced and cool."]
expected = ["cell_imbalance", "normal", "communication"]
crit = {"cell_imbalance": "cell voltage spread, balancing failure", "thermal": "overheating, cooling failure",
        "communication": "CAN bus errors, bus-off, lost communication", "normal": "no fault, within normal operating range"}
print(); print("=" * 96); print("프로브 3 — BMS 4지선다 (Laya)  [jeff: 숫자 1/3, 문장 1/3]"); print("-" * 96)
for kind, data in (("숫자(JSON)", numeric), ("문장(자연어)", verbal)):
    hits = 0
    for st, exp in zip(data, expected):
        ch, pr, cf, ms = choice(st, "What is the primary fault domain in this battery pack snapshot?", crit); lat.append(ms)
        hits += (ch == exp); print(f"  {kind:<10} 정답 {exp:<15} → {ch:<15} conf={cf:.2f} {'O' if ch == exp else 'X'}")
    print(f"  {kind} 정답 {hits}/3")
lat.sort(); print(f"\n지연시간 중앙값 {lat[len(lat)//2]:.0f} ms (최소 {lat[0]:.0f}, 최대 {lat[-1]:.0f})")
