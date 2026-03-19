# Annotation Guideline for Hidden Assumption Monitoring

## 1. 文件目的

本文件定義三個 benchmark 共用的標註規範，用於建置：

1. `Full Spec`
2. `Redacted Spec`
3. `Gold Assumptions`
4. `Oracle Review`

本規範的目的是讓不同標註者可以用一致標準建立資料，降低主觀性，並讓後續 assumption extraction 的 precision、recall、F1 具有可解釋性。

---

## 2. 標註單位

每個 task 為一個標註單位，每個 task 至少需包含：

- `task_id`
- `benchmark`
- `full_spec`
- `redacted_spec`
- `gold_assumptions`
- `redaction_rationale`
- `acceptance_tests`

`benchmark` 僅允許以下三種：

- `self_bench`
- `fea_bench`
- `swe_bench`

---

## 3. 核心定義

### 3.1 Full Spec

`Full Spec` 是該 task 的完整需求版本，應滿足：

1. 足以讓 agent 明確知道任務目標
2. 足以支撐合理的實作與驗收
3. 不包含與 task 無關的額外需求

### 3.2 Redacted Spec

`Redacted Spec` 是從 `Full Spec` 刪除部分關鍵規格後得到的版本，目的是讓 agent 面臨合理的 hidden assumption 空間。

`Redacted Spec` 必須滿足：

1. 任務仍然可理解
2. 任務仍然可執行
3. 不會因為刪除過多資訊而變成 impossible task
4. 被刪除的資訊會導致實質設計差異或驗收差異

### 3.3 Gold Assumption

`Gold Assumption` 指的是：

> 當 agent 僅看到 `Redacted Spec` 時，若要繼續設計、規劃或執行，合理需要補出的隱含規格、限制或決策前提。

它不是任意猜測，也不是所有可能細節，而是：

1. 來自 `Full Spec` 中被刪掉的關鍵資訊
2. 對實作方案、測試行為或成功標準有實質影響
3. 可以用一個清楚、獨立的陳述句表達

---

## 4. 標註流程

每題都依照以下順序進行。

### Step 1: 建立 Full Spec

標註者先建立完整需求版本。

要求：

1. 寫出可執行、可驗收的完整需求
2. 明確指出必要功能與限制
3. 避免加入不必要裝飾性描述

### Step 2: 建立 Redacted Spec

從 `Full Spec` 刪除 2 到 5 個關鍵規格。

要求：

1. 刪除後仍能理解任務
2. 被刪除的資訊會產生合理多解空間
3. 不刪除核心任務目標與必要介面資訊

### Step 3: 撰寫 Redaction Rationale

對每個被刪除的點，簡短說明：

1. 原本資訊是什麼
2. 刪掉後會造成什麼 hidden assumption
3. 為什麼這個 assumption 對結果重要

### Step 4: 標註 Gold Assumptions

每個 assumption 以獨立條目記錄。

每條至少包含：

- `id`
- `statement`
- `type`
- `source_span`
- `impact`
- `required_for_success`

### Step 5: 補 Acceptance Tests

標註者需定義最終任務如何驗收。

驗收可以是：

1. 自動化測試
2. benchmark 官方 resolved / pass 結果
3. 結構化 checklist

---

## 5. Assumption 類型定義

每條 gold assumption 必須對應一種 `type`。

允許值如下：

### 5.1 Functional

功能需求細節或產品行為。

例：

- 是否需要登入
- 聯絡功能是 email link 還是真正表單
- 是否支援搜尋或排序

### 5.2 Implementation

實作方式、架構或技術選型。

例：

- 是否需要前後端分離
- 是否需要資料庫
- 是否需要 API server

### 5.3 Environment

平台、相依條件、版本與部署環境。

例：

- 必須部署到 Vercel
- 必須相容 Python 3.10
- 必須遵守既有 repo API 風格

### 5.4 Validation

驗收行為、邊界條件與測試相關要求。

例：

- 需要處理空輸入
- 需要 backward compatibility
- 需要 mobile responsive

### 5.5 NonFunctional

非功能性約束。

例：

- SEO
- accessibility
- latency
- security

---

## 6. 什麼應該標成 Gold Assumption

以下情況應標：

1. `Full Spec` 有，`Redacted Spec` 沒有
2. 缺少後會導致至少兩種合理實作路徑
3. 不同路徑會影響最終成品、測試或需求對齊

例子：

- Full 指定 contact form 需儲存到 backend
- Redacted 只說要能聯絡
- Gold assumption：
  - 是否需要後端儲存聯絡資訊
  - 聯絡功能是否是真正表單而非單純 email link

---

## 7. 什麼不應該標成 Gold Assumption

以下情況不標：

1. 純措辭差異，不影響實作或驗收
2. 完全微小的 UI 偏好
3. agent 幾乎不需要決策即可完成的細節
4. 並非從 `Full Spec` 被刪掉，而是標註者事後想到的新需求

不應標註例子：

- 按鈕顏色是藍色還是綠色
- 內文用詞偏正式還是偏口語
- 頁面 margin 差 4px 這類無實質影響的設計細節

---

## 8. Gold Assumption 欄位規範

每條 assumption 建議長這樣：

```json
{
  "id": "A3",
  "statement": "The contact feature requires server-side storage of submitted messages.",
  "type": "Implementation",
  "source_span": "Full Spec sentence 4",
  "impact": "Without this assumption, the agent may build only a mailto link or a client-only form.",
  "required_for_success": true
}
```

欄位解釋：

- `id`
  - 該題內唯一
- `statement`
  - 用完整句表達
- `type`
  - 必須是 taxonomy 中的一種
- `source_span`
  - 指回 `Full Spec` 哪裡來的
- `impact`
  - 說明若 assumption 被漏掉，會導致什麼差異
- `required_for_success`
  - 布林值
  - `true` 表示漏掉大概率會影響 task success 或 alignment

---

## 9. Redaction 原則

### 9.1 可以刪的資訊

優先考慮刪除：

1. backend / database 需求
2. deployment target
3. auth / permission model
4. API contract 細節
5. edge case behavior
6. backward compatibility
7. accessibility / responsive / SEO
8. persistence requirement

### 9.2 不可刪的資訊

不可刪除：

1. 核心任務目標
2. 必要輸入輸出介面
3. 關鍵 bug localization 線索
4. benchmark 基本執行條件
5. 使任務完全無法理解的描述

### 9.3 Redaction 強度

每題建議保留以下原則：

1. 刪除 2 到 5 個關鍵點
2. 不要把所有限制都刪光
3. Redacted 應該讓 agent 面臨「合理但可錯」的決策，而不是「只能亂猜」

---

## 10. 各 Benchmark 的特殊規則

### 10.1 Self Bench

標註原則：

1. 任務由團隊自行設計
2. `Full Spec` 需先定義完整 acceptance checklist
3. `Redacted Spec` 要讓 open-ended spec gap 明顯存在

適合刪除：

- 產品需求缺口
- system architecture 假設
- deployment 假設
- non-functional requirement

### 10.2 FEA-Bench

標註原則：

1. 固定相同 code context
2. 不改 benchmark 基本題目結構
3. 只對 spec text 做 redaction

適合刪除：

- edge case
- expected behavior examples
- comments 中的 constraint
- backward compatibility hints

避免刪除：

- component signatures
- 核心 feature request 主體

### 10.3 SWE-bench

標註原則：

1. 固定相同 repository setup
2. 不刪主要 bug localization 線索
3. 重點刪的是行為限制與邊界條件

適合刪除：

- version-specific notes
- expected behavior examples
- failure mode 描述
- comments 裡的 acceptance clues

避免刪除：

- module names
- key API names
- reproduction clue
- 關鍵錯誤現象描述

---

## 11. Oracle Review Protocol

`Monitor-then-Act on Redacted` 中，人類修正採用標準化 oracle review。

reviewer 只能參考：

1. `Full Spec`
2. `Redacted Spec`
3. monitor report

reviewer 的合法操作只有四種：

### 11.1 Accept

該 assumption 與 Full Spec 一致，保留不動。

### 11.2 Reject

該 assumption 與 Full Spec 不一致，且不應保留。

### 11.3 Edit

monitor 抓到的方向是對的，但表述不夠準確，需要修正。

### 11.4 Add Missing Assumption

monitor 沒抓到，但該 assumption 明確存在於 gold assumptions 中。

---

## 12. Review 輸出格式

每次 review 應輸出結構化結果：

```json
{
  "task_id": "example-001",
  "review_actions": [
    {
      "action": "accept",
      "assumption_id": "A1"
    },
    {
      "action": "edit",
      "assumption_id": "A2",
      "edited_statement": "The contact feature must store messages on the server."
    },
    {
      "action": "add",
      "new_assumption": {
        "id": "A4",
        "statement": "The site must be deployable to Vercel.",
        "type": "Environment"
      }
    }
  ]
}
```

---

## 13. 標註品質控管

### 13.1 雙人標註

Pilot 階段至少部分題目採雙人標註。

建議：

- 每個 benchmark 至少 2 題做雙人標註

### 13.2 爭議處理

若標註者對某條 assumption 是否成立有歧見：

1. 先檢查是否真的來自 Full Spec 被刪掉的資訊
2. 再檢查是否影響實作或驗收
3. 若仍有歧見，記錄 adjudication note

### 13.3 標註錯誤類型

常見錯誤：

1. 把新需求誤標成 gold assumption
2. 把不影響結果的細節誤標
3. Redacted 刪太多導致 impossible task
4. 同一條 assumption 被拆太細或混太多概念

---

## 14. 對齊評估的匹配規則

assumption extraction 評分時，prediction 與 gold 的匹配標準如下：

1. 核心語義一致即可視為 match
2. 不要求 wording 完全相同
3. type 若錯，但 statement 核心語義對，可記錄為 partial analysis，但主評分先以 statement match 為主

建議：

1. 主表計算 statement-level F1
2. 補表計算 statement + type 的 stricter F1

---

## 15. 建議標註流程

建議實作順序：

1. 先完成 `Full Spec`
2. 產生 `Redacted Spec`
3. 寫 `redaction_rationale`
4. 標 `Gold Assumptions`
5. 寫 `acceptance_tests`
6. 再由第二人快速 review

不要一開始先憑感覺寫 gold assumptions，否則很容易脫離 Full/Redacted 的差異。

---

## 16. 最低完成標準

每題至少要達到：

1. `Full Spec` 與 `Redacted Spec` 可清楚對照
2. 有 2 到 5 條 gold assumptions
3. 每條 assumption 都有 type 與 impact
4. 有可執行或可檢查的 acceptance tests
5. 有 redaction rationale

未達標的題目不應進入正式實驗。
