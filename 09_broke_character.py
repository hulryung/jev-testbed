"""
[테스트 9] anima2/cognition.py::_broke_character (키워드 4개) vs jeff Noul

현재 코드:
    def _broke_character(text):
        low = text.lower()
        return "language model" in low or "an ai" in low or "i cannot" in low or "as an" in low
걸리면 _clean_model_line 이 None 을 돌려 그 대사/인사이트/위키보고를 버린다.

예측 (실행 전에 적음):
  P1. 키워드 매처는 부분문자열 함정 6개를 전부 오탐, 미묘한 이탈 2개를 놓침 → 약 8/14.
  P2. jeff Noul(임계 0.5)은 12/14 이상, 함정 문장의 noul 은 0.30 미만.
"""
import _env  # noqa: F401
from typesafe_sdk import Noul, TypeSafeClient

def keyword_matcher(text):
    low = text.lower()
    return "language model" in low or "an ai" in low or "i cannot" in low or "as an" in low

# (문장, 캐릭터 이탈 여부 정답, 비고)
cases = [
    # 명백한 이탈 — 키워드로도 잡힘
    ("As an AI language model, I cannot roleplay violence.",                True,  "명백"),
    ("I'm an AI assistant and don't have access to a game world.",         True,  "명백"),
    # 미묘한 이탈 — 키워드에 없음
    ("I'm not able to help with that request.",                            True,  "미묘"),
    ("I don't have real-time access to your inventory or the server.",     True,  "미묘"),
    # 부분문자열 함정 — 정상 대사인데 키워드에 걸림
    ("I cannot afford a new pickaxe until I sell this ore.",               False, "함정 'i cannot'"),
    ("I cannot find the forge in this fog. Grimm hates fog.",              False, "함정 'i cannot'"),
    ("As an apprentice I ruined more ingots than I saved.",                False, "함정 'as an'"),
    ("Iron today is as an old friend — heavy and honest.",                 False, "함정 'as an'"),
    ("Spare a coin for an aid to a tired miner?",                          False, "함정 'an ai'"),
    ("Take an aim at the ridge; the good ore hides there.",                False, "함정 'an ai'"),
    # 평범한 정상 대사
    ("Hail, friend. Grimm greets you.",                                    False, "정상"),
    ("The vein runs clean today. Heavy and pure.",                         False, "정상"),
    ("Begging thy pardon, I've no boards to spare this morning.",          False, "정상"),
    ("Three daggers sold. The banker can have the rest.",                  False, "정상"),
]

q = {"broke": Noul(
    instructions="Does this line break character by revealing or behaving as an AI assistant, "
                 "language model, or chatbot (refusing as an assistant, mentioning being an AI, "
                 "lacking access to the game) instead of speaking as a person living in a medieval fantasy world?",
    criteria={"true": "speaks as an AI/assistant/model, or refuses in assistant voice",
              "false": "stays in character as a person in the game world"})}

c = TypeSafeClient()
kw_ok = jv_ok = 0
print(f"{'문장':<58} {'정답':<5} {'키워드':<7} {'jeff':>5}  {'판정':<6} 비고")
print("-" * 110)
for text, truth, note in cases:
    kw = keyword_matcher(text)
    n = c.system_one(state=text, questions=q).answers["broke"].noul
    jv = n >= 0.5
    kw_ok += (kw == truth); jv_ok += (jv == truth)
    mark = ("O" if jv == truth else "X") + "/" + ("O" if kw == truth else "X")
    label = text if len(text) <= 56 else text[:55] + "…"
    print(f"{label:<58} {str(truth):<5} {str(kw):<7} {n:>5.2f}  {mark:<6} {note}")
print("-" * 110)
print(f"정확도  키워드 매처 {kw_ok}/{len(cases)}   |   jeff Noul(≥0.5) {jv_ok}/{len(cases)}      (판정 열: jeff/키워드)")
