# Jev 테스트베드

**Jev** = TypeSafe AI의 *System One* 모델. 텍스트를 생성하지 않고
**타입이 정해진 결정값 + 확률**만 돌려준다.

| | 일반 LLM (System Two) | Jev (System One) |
|---|---|---|
| 출력 | 자유 문장 | `choice` / `score` / `noul` 값 |
| 확신도 | 없음 (파싱해야 함) | `confidence` 로 항상 같이 옴 |
| 지연 | 초 단위 | 수백 ms |
| 가격 | 입력 $ 수/1M | **입력 $0.042/1M, 출력 무료** |
| 쓰는 자리 | 작성, 추론, 대화 | 라우팅, 분류, 게이트, 필터 |

## 3가지 질문 형태

- **Noul** — 예/아니오의 *확률* (0.0 ~ 1.0)
- **Choice** — 내가 정의한 보기 중 하나 + 전체 확률분포
- **Score** — 내가 정의한 등급 위의 연속값 (예: 0~2 사이 1.035)

## 준비

```bash
export TYPESAFE_API_KEY=...        # https://console.typesafe.ai/keys 에서 발급
```

## 실행

```bash
.venv/bin/python 01_basics.py      # 3가지 기본형 한 번에 + 원본 JSON
.venv/bin/python 02_confidence.py  # 확신도로 자동처리/사람확인 가르기
.venv/bin/python 03_speed_cost.py  # 실제 지연시간·비용 측정, 순차 vs 병렬
.venv/bin/python 04_can_triage.py  # BMS/CAN 이벤트 분류 (state를 구조체로)
```

## API 원형 (SDK 없이)

```bash
curl -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "3일째 연동이 실패합니다. 급합니다.",
    "model": "jev-latest",
    "questions": { "urgency": { "type": "noul", "instructions": "긴급한가?" } }
  }'
```

- 엔드포인트: `POST https://api.typesafe.ai/v1/systemone`
- 컨텍스트: 64k (state + 최장 질문은 32k)
- 레이트리밋: 250,000 tok/s, 1,200 req/min

---

# 로컬에서 돌리기 (jev 없이)

**Jev 자체는 가중치 비공개 · 호스팅 전용**이다. on-prem도 다운로드도 없다.
대신 **[jeff](https://github.com/logan-markewich/jeff)** 가 같은 API를 그대로 구현한다
(GLiFormer 400M, `knowledgator/gliformer-large-v1`).
`TYPESAFE_BASE_URL`만 바꾸면 **이 폴더의 코드를 한 줄도 안 고치고** 로컬로 돌아간다.

## 설치 (이미 완료됨)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv
git clone https://github.com/logan-markewich/jeff.git
cd jeff && uv sync --extra dev
uv run hf download knowledgator/gliformer-large-v1 --local-dir models/gliformer-large-v1
```

## 서버 띄우기

```bash
cd jeff && JEFF_API_KEYS=devkey uv run jeff     # localhost:8000, Mac은 MPS 자동 선택
```

## 예제 실행

```bash
./run_local.sh 01_basics.py      # 클라우드로 쓰려면 .env 에 실제 키 넣고 .venv/bin/python 직접 실행
```

---

# 실측 결과 (Apple M5 / 24GB / MPS)

| 항목 | 값 |
|---|---|
| 모델 로드 | 6.2 s |
| 건당 지연 | **중앙값 78 ms** (최소 67 / 최대 847) |
| 순차 10건 | 1.78 s |
| 병렬 10건 | 0.59 s (3.0배) |
| 비용 | **$0** (전기값만) |

## ⚠ 반드시 지킬 것 — instructions는 영어로

`state`(평가 대상)는 한국어여도 되지만, **`instructions`와 `criteria`는 영어로 써야 한다.**
같은 입력에 질문문 언어만 바꿔 측정한 결과:

| state | instructions | urgent (정답은 1에 가까움) |
|---|---|---|
| KO | KO | 0.333 ❌ |
| KO | **EN** | **0.836** ✅ |
| EN | KO | 0.033 ❌❌ |
| EN | **EN** | **0.823** ✅ |

질문문을 한국어로 쓰면 영어 입력에서도 0.033까지 붕괴한다. state 언어는 거의 영향이 없다.

## 로컬 모델이 되는 일 / 안 되는 일

**된다** — 텍스트 의미 기반의 단순 판별:
```
"서버가 죽었어요 지금 당장"        긴급도 0.794
"결제가 3번 중복됐습니다 급합니다"   긴급도 0.722
"그냥 인사드립니다"                긴급도 0.202
"로그인이 안 됩니다"               긴급도 0.172
```

**안 된다** — 4지선다 도메인 분류, 숫자 기준 판단 (BMS 스냅샷 분류는 3건 중 1건만 정답,
숫자 JSON이든 서술 문장이든 동일하게 실패). jeff README도 "reasoning-heavy 태스크에서
jev보다 부정확"이라고 명시한다.

## 그런데 이게 왜 안전한가 — confidence 게이트

약한 모델이어도 **틀린 답이 자동 처리로 새지 않는다.** 실측:

| 문의 | 판단 | 확신도 | 처리 |
|---|---|---|---|
| API가 500 에러를 계속 뱉습니다 | technical | 80.5% | 자동 라우팅 ✅ |
| 카드 결제가 두 번 청구됐어요 | billing | 58.9% | 사람 확인 |
| 요금제 올리면 웹훅 연동도 늘어나나요? | technical | 17.4% | 사람 확인 ✅ |
| 안녕하세요 | technical | 11.9% | 사람 확인 ✅ |

모델이 모르는 건 확신도로 정직하게 알려준다. 임계값 하나로 자동화율과 정확도를 맞바꾼다.

## 튜닝 포인트

| 환경변수 | 기본값 | 용도 |
|---|---|---|
| `JEFF_TEMPERATURE` | `3.2` | 확률 평탄화. **낮추면 확신도가 날카로워진다** |
| `JEFF_DEVICE` | auto | `mps` / `cpu` |
| `JEFF_MAX_BATCH` / `JEFF_MAX_WAIT_MS` | `16` / `5` | 배치 처리량 |
| `JEFF_ISOLATE` | `nouls` | 질문별 인코더 분리 (`none`/`nouls`/`all`) |

## 다른 선택지

- **[SemIf / openjev.com](https://openjev.com/)** — 브라우저에서 GGUF(Qwen3 0.6B / MiniCPM5 2B / Qwen3.5 4B)를 받아
  logit 직접 읽기. 백엔드 없음. 서버/API는 제공 안 함.
- **직접 구현** — 어떤 로컬 LLM이든 보기 토큰의 logprob을 읽어 정규화하면 Choice/Noul이 된다.
  Jev의 본질이 그것이다.
