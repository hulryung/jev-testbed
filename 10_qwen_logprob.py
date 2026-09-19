"""
[테스트 10] '완전히 새로운 접근': 4B 생성 모델을 System One 처럼 쓴다 (logprob 모드)
  - 생성하지 않는다. 선택지 글자(A/B/C…) 또는 yes/no 의 다음-토큰 확률만 읽는다.
  - 항상 유효한 답 + 확률분포 + confidence. jeff 와 동일한 인터페이스 모양.
  - 08(경제 스티어링, 문장 상태) / 09(캐릭터 이탈) 와 동일한 입력으로 비교한다.

예측 (실행 전에 적음):
  P1. 스티어링: ash=1 이면 buy_reagent 가 1위(크기 인식), ash=40+금 400 이면 bank_gold 가 jeff(0.13)보다 큰 마진으로 1위.
  P2. 캐릭터 이탈: 14개 중 12개 이상, 명백한 이탈 P(yes)>0.8, 함정 문장 P(yes)<0.3.
  P3. 지연: 결정당 100~500ms — 5초 한도 안, 100~250ms 빠른 틱 밖 → 오늘과 같은 '느린 루프 전용'.
"""
import time, math, string
import mlx.core as mx
from mlx_lm import load

MODEL = "models/Qwen3-4B-4bit"
model, tok = load(MODEL)

def _next_token_logprobs(messages):
    ids = tok.apply_chat_template(messages, add_generation_prompt=True, enable_thinking=False)
    logits = model(mx.array([ids]))[:, -1, :]
    return (logits - mx.logsumexp(logits, keepdims=True)).squeeze(0)

def _tid(s):
    ids = tok.encode(s, add_special_tokens=False)
    assert len(ids) == 1, (s, ids)
    return ids[0]

def choice(state, question, options: dict[str, str]):
    letters = string.ascii_uppercase[:len(options)]
    menu = "\n".join(f"{L}. {k} — {v}" for L, (k, v) in zip(letters, options.items()))
    msgs = [{"role": "system", "content": "You are a decision function. Reply with exactly one letter."},
            {"role": "user", "content": f"Situation:\n{state}\n\nQuestion: {question}\nOptions:\n{menu}\n\nAnswer:"}]
    t0 = time.perf_counter(); lp = _next_token_logprobs(msgs); 
    vals = mx.array([lp[_tid(L)].item() for L in letters]); vals = mx.exp(vals - mx.logsumexp(vals))
    ms = (time.perf_counter() - t0) * 1000
    probs = {k: float(p) for k, p in zip(options, vals.tolist())}
    ranked = sorted(probs.values(), reverse=True)
    return max(probs, key=probs.get), probs, ranked[0] - ranked[1], ms

def noul(state, question):
    msgs = [{"role": "system", "content": "You are a decision function. Reply with exactly one word: yes or no."},
            {"role": "user", "content": f"Text:\n{state}\n\nQuestion: {question}\nAnswer:"}]
    t0 = time.perf_counter(); lp = _next_token_logprobs(msgs)
    y = lp[_tid("yes")].item(); n = lp[_tid("no")].item()
    ms = (time.perf_counter() - t0) * 1000
    return math.exp(y) / (math.exp(y) + math.exp(n)), ms

# ---------------- 프로브 1: 경제 스티어링 (08과 동일) ----------------
CANDS = {"buy_reagent": "Buy a batch of reagents from the mage vendor and return.",
         "fetch_gold":  "Pick up a delivered purse of gold from the ground into the pack.",
         "bank_gold":   "Deposit surplus gold with the banker and return."}
QS = "Which single economy action should this Ultima Online mage do first, right now?"
scen = [("시약 거의 없음, 지갑은 멀리",   dict(ash=1,  gold=90,  purse_tiles=6, reserve_over=0)),
        ("시약 살짝 부족, 지갑 1타일 옆", dict(ash=14, gold=120, purse_tiles=1, reserve_over=0)),
        ("시약 충분, 금 넘침(예치 필요)", dict(ash=40, gold=400, purse_tiles=0, reserve_over=270)),
        ("전부 애매하게 걸림",           dict(ash=13, gold=130, purse_tiles=3, reserve_over=5))]
def as_text(s):
    return " ".join([
        f"Reagent pouch: {s['ash']} sulfurous ash (reorder line is 15; a mage with none cannot cast).",
        f"Gold in pack: {s['gold']} (a reagent batch costs 100; pack cap before fetching more is 180).",
        (f"A delivered purse of gold is lying on the ground {s['purse_tiles']} tile(s) away." if s['purse_tiles'] else "No purse on the ground."),
        (f"Gold exceeds the bank reserve by {s['reserve_over']}." if s['reserve_over'] else "Gold is at or below the bank reserve.")])

lat = []
print("=" * 100); print("프로브 1 — 경제 스티어링 (Qwen3-4B logprob)"); print("-" * 100)
ch, pr, cf, ms = choice("The character can do any ONE of these right now, all currently possible and safe.", QS, CANDS); lat.append(ms)
print(f"  {'(상태 없음 — 현재 방식)':<26} → {ch:<12} conf={cf:.2f}   " + "  ".join(f"{k.split('_')[0]:>5}={pr[k]:.2f}" for k in CANDS) + f"   {ms:.0f}ms")
for name, s in scen:
    ch, pr, cf, ms = choice(as_text(s), QS, CANDS); lat.append(ms)
    print(f"  {name:<26} → {ch:<12} conf={cf:.2f}   " + "  ".join(f"{k.split('_')[0]:>5}={pr[k]:.2f}" for k in CANDS) + f"   {ms:.0f}ms")

# ---------------- 프로브 2: 캐릭터 이탈 (09와 동일) ----------------
QN = ("Does this line break character by revealing or behaving as an AI assistant, language model, or chatbot "
      "(refusing as an assistant, mentioning being an AI, lacking access to the game) instead of speaking as a "
      "person living in a medieval fantasy world?")
cases = [("As an AI language model, I cannot roleplay violence.", True, "명백"),
         ("I'm an AI assistant and don't have access to a game world.", True, "명백"),
         ("I'm not able to help with that request.", True, "미묘"),
         ("I don't have real-time access to your inventory or the server.", True, "미묘"),
         ("I cannot afford a new pickaxe until I sell this ore.", False, "함정 'i cannot'"),
         ("I cannot find the forge in this fog. Grimm hates fog.", False, "함정 'i cannot'"),
         ("As an apprentice I ruined more ingots than I saved.", False, "함정 'as an'"),
         ("Iron today is as an old friend — heavy and honest.", False, "함정 'as an'"),
         ("Spare a coin for an aid to a tired miner?", False, "함정 'an ai'"),
         ("Take an aim at the ridge; the good ore hides there.", False, "함정 'an ai'"),
         ("Hail, friend. Grimm greets you.", False, "정상"),
         ("The vein runs clean today. Heavy and pure.", False, "정상"),
         ("Begging thy pardon, I've no boards to spare this morning.", False, "정상"),
         ("Three daggers sold. The banker can have the rest.", False, "정상")]
def keyword_matcher(t):
    low = t.lower(); return "language model" in low or "an ai" in low or "i cannot" in low or "as an" in low

print(); print("=" * 100); print("프로브 2 — 캐릭터 이탈 Noul (Qwen3-4B logprob)  [판정 열: qwen/키워드]"); print("-" * 100)
ok = kw_ok = 0
for text, truth, note in cases:
    p, ms = noul(text, QN); lat.append(ms)
    v = p >= 0.5; ok += (v == truth); kw_ok += (keyword_matcher(text) == truth)
    label = text if len(text) <= 56 else text[:55] + "…"
    print(f"  {label:<58} {str(truth):<5} P(yes)={p:.2f}  {('O' if v == truth else 'X')}/{('O' if keyword_matcher(text) == truth else 'X')}  {note}")
print("-" * 100)
print(f"  정확도  Qwen3-4B {ok}/{len(cases)}   |   키워드 매처 {kw_ok}/{len(cases)}   |   (참고: jeff 6/14)")
lat_sorted = sorted(lat)
print(f"\n지연시간  결정당 중앙값 {lat_sorted[len(lat)//2]:.0f} ms  |  최소 {lat_sorted[0]:.0f}  최대 {lat_sorted[-1]:.0f}  (첫 호출은 워밍업 포함)")
