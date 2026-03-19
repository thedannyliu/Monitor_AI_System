# Monitor Report Schema

## 1. 文件目的

本文件定義 monitoring layer 的固定輸出格式，供以下模組共用：

1. assumption extraction
2. oracle review
3. revised spec generation
4. evaluation pipeline

第一版正式實驗中，monitor 必須輸出合法 JSON。若輸出無法解析，視為格式失敗，需重跑。

目前 schema 已接上兩種 backend：

1. `heuristic`
2. `OpenAI-compatible` serving backend，例如 `vLLM`

對於 OpenAI-compatible backend，系統會先要求模型直接輸出 canonical schema；若模型回傳的是可解析 JSON 但欄位名稱略有偏差，runtime 會做一次 constrained normalization，把 near-miss payload 轉成固定 schema 後再驗證。這是為了降低 7B 級模型的格式漂移對 pilot 的影響，不改變「assumption content 來自模型」這個實驗設定。

---

## 2. 設計原則

schema 設計遵守以下原則：

1. 同時支援三個 benchmark
2. 欄位足夠支撐人工審核
3. 欄位足夠支撐 assumption-level evaluation
4. 避免自由文字過多，方便後處理

---

## 3. Top-level Schema

第一版 monitor report 的 top-level 欄位如下：

```json
{
  "task_id": "string",
  "benchmark": "self_bench | fea_bench | swe_bench",
  "spec_variant": "redacted",
  "task_summary": "string",
  "assumptions": [],
  "open_questions": [],
  "monitor_notes": [],
  "schema_version": "v1"
}
```

欄位說明：

- `task_id`
  - 對應 benchmark task id
- `benchmark`
  - 來源 benchmark
- `spec_variant`
  - 第一版固定為 `redacted`
- `task_summary`
  - 對當前任務的簡短摘要
- `assumptions`
  - assumption 條目列表
- `open_questions`
  - monitor 建議由使用者或 reviewer 回答的問題
- `monitor_notes`
  - 補充說明
- `schema_version`
  - 版本號

---

## 4. Assumption Item Schema

每個 assumption 條目格式如下：

```json
{
  "id": "A1",
  "statement": "The task likely requires a backend service to store user-submitted messages.",
  "type": "Implementation",
  "evidence": [
    "The task asks for a contact feature but does not specify whether submissions must be stored.",
    "No static-only constraint is given."
  ],
  "risk_if_wrong": "A static-only implementation may fail to satisfy the intended contact workflow.",
  "needs_confirmation": true,
  "confidence": 0.78,
  "proposed_resolution": "Confirm whether the contact feature should persist submissions on the server.",
  "linked_decisions": [
    "Whether to add backend routes",
    "Whether to add a database or external form service"
  ]
}
```

---

## 5. Assumption 欄位定義

### 5.1 `id`

- 型別：`string`
- 規則：同一份 report 中唯一
- 建議格式：`A1`, `A2`, `A3`

### 5.2 `statement`

- 型別：`string`
- 必填
- 用完整句表達 assumption
- 不可只寫關鍵字

好例子：

- `The feature must remain backward compatible with the existing API behavior.`

壞例子：

- `backward compatibility`

### 5.3 `type`

- 型別：`string`
- 必填
- 合法值：
  - `Functional`
  - `Implementation`
  - `Environment`
  - `Validation`
  - `NonFunctional`

### 5.4 `evidence`

- 型別：`array[string]`
- 至少 1 條
- 說明 monitor 為什麼推定這個 assumption
- 來源可以是：
  - prompt 內容
  - plan 內容
  - code context
  - benchmark metadata

### 5.5 `risk_if_wrong`

- 型別：`string`
- 必填
- 說明若 assumption 錯了，可能導致什麼錯誤後果

### 5.6 `needs_confirmation`

- 型別：`boolean`
- 必填
- `true` 表示這條 assumption 應被 reviewer 特別檢查

### 5.7 `confidence`

- 型別：`number`
- 範圍：`0.0` 到 `1.0`
- 第一版只是輔助欄位，不直接用於主評分

### 5.8 `proposed_resolution`

- 型別：`string`
- 必填
- 說明 monitor 建議如何消解這條 assumption
- 可以是：
  - 問一個澄清問題
  - 指定一個保守預設
  - 建議 reviewer 決策

### 5.9 `linked_decisions`

- 型別：`array[string]`
- 選填
- 表示這條 assumption 會影響哪些後續設計決策

---

## 6. Open Question Schema

`open_questions` 為 monitor 認為仍需要確認的問題。

格式如下：

```json
[
  {
    "id": "Q1",
    "question": "Should the contact feature store submitted messages on the server?",
    "related_assumptions": ["A1"],
    "priority": "high"
  }
]
```

欄位規則：

- `id`
  - 唯一字串
- `question`
  - 明確、可回答
- `related_assumptions`
  - 對應 assumption id 陣列
- `priority`
  - 合法值：
    - `high`
    - `medium`
    - `low`

---

## 7. Monitor Notes Schema

`monitor_notes` 用於補充不適合放在 assumption 裡的系統觀察。

格式如下：

```json
[
  {
    "category": "coverage_warning",
    "message": "The spec omits deployment constraints and validation requirements."
  }
]
```

第一版允許的 `category`：

- `coverage_warning`
- `execution_risk`
- `context_gap`

---

## 8. Oracle Review Schema

reviewer 對 monitor report 的修正結果必須輸出為 JSON。

格式如下：

```json
{
  "task_id": "string",
  "benchmark": "self_bench",
  "review_actions": [
    {
      "action": "accept",
      "assumption_id": "A1"
    },
    {
      "action": "reject",
      "assumption_id": "A2",
      "reason": "Not supported by the full spec"
    },
    {
      "action": "edit",
      "assumption_id": "A3",
      "edited_assumption": {
        "statement": "The site needs a contact form that stores submissions server-side.",
        "type": "Implementation"
      }
    },
    {
      "action": "add",
      "new_assumption": {
        "id": "A4",
        "statement": "The application must be deployable to Vercel.",
        "type": "Environment",
        "reason": "Explicitly present in the full spec"
      }
    }
  ]
}
```

---

## 9. Revised Spec Schema

review 後，系統要生成一份 revised spec 給 execution agent。

格式如下：

```json
{
  "task_id": "string",
  "benchmark": "self_bench",
  "base_spec": "original redacted spec text",
  "confirmed_assumptions": [
    "The application must store contact form submissions on the server.",
    "The project must be deployable to Vercel."
  ],
  "rejected_assumptions": [
    "A backend is unnecessary."
  ],
  "execution_constraints": [
    "Preserve backward compatibility",
    "Implement mobile responsive UI"
  ]
}
```

這份 revised spec 的目的是把 human correction 轉成 agent 可消化的結構化約束。

---

## 10. 最低合法輸出條件

一份 monitor report 至少要滿足：

1. 可被 JSON parser 成功解析
2. 包含 top-level 必填欄位
3. `assumptions` 為 array
4. 每條 assumption 至少有：
   - `id`
   - `statement`
   - `type`
   - `evidence`
   - `risk_if_wrong`
   - `needs_confirmation`
   - `confidence`
   - `proposed_resolution`

否則該次輸出視為格式失敗。

---

## 11. 建議 JSON Schema 草案

以下是第一版可直接轉成程式驗證的簡化 schema：

```json
{
  "type": "object",
  "required": [
    "task_id",
    "benchmark",
    "spec_variant",
    "task_summary",
    "assumptions",
    "open_questions",
    "monitor_notes",
    "schema_version"
  ],
  "properties": {
    "task_id": { "type": "string" },
    "benchmark": {
      "type": "string",
      "enum": ["self_bench", "fea_bench", "swe_bench"]
    },
    "spec_variant": {
      "type": "string",
      "enum": ["redacted"]
    },
    "task_summary": { "type": "string" },
    "assumptions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "statement",
          "type",
          "evidence",
          "risk_if_wrong",
          "needs_confirmation",
          "confidence",
          "proposed_resolution"
        ],
        "properties": {
          "id": { "type": "string" },
          "statement": { "type": "string" },
          "type": {
            "type": "string",
            "enum": [
              "Functional",
              "Implementation",
              "Environment",
              "Validation",
              "NonFunctional"
            ]
          },
          "evidence": {
            "type": "array",
            "items": { "type": "string" },
            "minItems": 1
          },
          "risk_if_wrong": { "type": "string" },
          "needs_confirmation": { "type": "boolean" },
          "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
          },
          "proposed_resolution": { "type": "string" },
          "linked_decisions": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    },
    "open_questions": {
      "type": "array",
      "items": { "type": "object" }
    },
    "monitor_notes": {
      "type": "array",
      "items": { "type": "object" }
    },
    "schema_version": { "type": "string" }
  }
}
```

---

## 12. Prompting 約束

為了提高格式穩定性，monitor prompt 應明確要求：

1. 僅輸出 JSON
2. 不要輸出 markdown code fence
3. 不要補充自然語言前言或結語
4. `confidence` 必須在 0 到 1 之間
5. `type` 必須是五類之一

---

## 13. Evaluation 對接欄位

以下欄位會直接被 evaluation 使用：

- `assumptions[*].statement`
- `assumptions[*].type`
- `assumptions[*].needs_confirmation`
- `open_questions`

assumption-level F1 主評估使用：

- `statement`

較嚴格分析可加上：

- `statement + type`

---

## 14. 錯誤處理

若 monitor 輸出不合法：

1. 第一次：自動重試一次
2. 第二次仍失敗：記錄為 `format_failure`
3. 正式評測時不可人工修補 JSON 後再算成功

---

## 15. 範例完整輸出

```json
{
  "task_id": "self-portfolio-001",
  "benchmark": "self_bench",
  "spec_variant": "redacted",
  "task_summary": "Build a personal portfolio website with a way for visitors to contact the owner.",
  "assumptions": [
    {
      "id": "A1",
      "statement": "The contact feature can be implemented as a static mailto link rather than a form with server-side storage.",
      "type": "Implementation",
      "evidence": [
        "The redacted spec only mentions contact capability.",
        "No persistence requirement is stated."
      ],
      "risk_if_wrong": "A static-only implementation may fail if the intended behavior requires form submission storage.",
      "needs_confirmation": true,
      "confidence": 0.71,
      "proposed_resolution": "Confirm whether the contact feature needs a real form and message persistence.",
      "linked_decisions": [
        "Whether to build a backend",
        "Whether to add a database or third-party form service"
      ]
    },
    {
      "id": "A2",
      "statement": "The site does not need explicit mobile responsive validation.",
      "type": "Validation",
      "evidence": [
        "No responsive behavior is mentioned in the redacted spec."
      ],
      "risk_if_wrong": "The final site may fail usability expectations on mobile devices.",
      "needs_confirmation": true,
      "confidence": 0.63,
      "proposed_resolution": "Ask whether the site must be responsive across mobile and desktop layouts.",
      "linked_decisions": [
        "Whether to include responsive breakpoints and layout testing"
      ]
    }
  ],
  "open_questions": [
    {
      "id": "Q1",
      "question": "Should the contact feature store submitted messages on the server?",
      "related_assumptions": ["A1"],
      "priority": "high"
    },
    {
      "id": "Q2",
      "question": "Does the site need to be explicitly mobile responsive?",
      "related_assumptions": ["A2"],
      "priority": "medium"
    }
  ],
  "monitor_notes": [
    {
      "category": "coverage_warning",
      "message": "The redacted spec omits deployment and validation constraints."
    }
  ],
  "schema_version": "v1"
}
```
