# Monitoring Hidden Assumptions in Coding Agents

## 1. 文件目的

本文件定義 Project 2 第一版實驗的固定執行規格，目標是讓三條 benchmark 線都在同一個研究框架下運作：

1. 自建 paired benchmark，20 題
2. FEA-Bench，20 題
3. SWE-bench，20 題

三條線都必須回答同一個核心問題：

> 在需求資訊被部分遮蔽時，`Monitor-then-Act on Redacted` 是否能逼近 `Direct on Full`？

本文件同時固定：

- 第一版 coder model
- benchmark 資料建置方式
- 三組對照實驗條件
- evaluation 指標
- 資料夾規劃
- 執行時程與風險控管

---

## 2. 第一版固定決策

### 2.1 Base coder model

第一版主模型固定為：

- `Qwen/Qwen2.5-Coder-7B-Instruct`

選擇理由：

1. 它是目前最實務、最容易部署的 7B 級開源 coder 模型之一。
2. 官方明確定位為 code generation、code reasoning、agentic coding 與 repository-level 任務可用。
3. 官方提供長 context，對 FEA-Bench 和 SWE-bench 這種 repo-level任務更實用。
4. 授權相對友善，第一版研究原型落地成本低。

第一版不要同時換很多模型。先固定一個 base coder，否則你最後無法分辨結果差異來自：

- monitoring layer
- benchmark 差異
- model 本身能力差異

### 2.2 Monitor model

第一版 monitor 也使用同一個模型：

- `Qwen/Qwen2.5-Coder-7B-Instruct`

理由：

1. 先隔離變因，只測「有沒有 monitoring step」，不要一開始混入第二個模型。
2. 7B 級模型成本較低，適合先做大量 pilot。
3. 後續若要做 ablation，再比較：
   - same-model monitor
   - separate auditor model

### 2.3 Inference backend

第一版建議：

- 優先：`vLLM`
- 備用：`transformers + bitsandbytes`

環境管理固定如下：

- base conda root: `/storage/ice1/2/9/eliu354/miniconda3`
- project env: `monitor-ai-system`
- Python: `3.12`

原則：

1. `base` 只保留 conda 本體與最小修復套件，不安裝 GPU 推論套件。
2. 專案依賴安裝到 `monitor-ai-system`。
3. `vLLM` 這類 GPU 相關依賴只安裝到專案 env，不裝到 base。
4. 既有外部 env 保持原路徑，不搬移、不重寫 prefix。

建議策略：

1. 有穩定 GPU 時，使用 `vLLM` 單卡推論。
2. 若 queue 壓力大或資源零碎，退回 `transformers + 4-bit quantization`。
3. 所有正式評測條件必須固定同一種 backend，避免 runtime 差異影響結果。

### 2.4 PACE ICE 資源策略

已知可用 GPU 類型：

- H100
- H200
- A100
- L40S

但供給不穩定，因此第一版設計原則如下：

1. 模型必須能在單卡完成。
2. 不依賴 H100/H200 才能跑。
3. 中斷後可從單題 checkpoint 恢復。
4. 任務執行切成小批次，不做超長單一 job。

建議排程優先順序：

1. `A100` 或 `L40S` 作為主力
2. `H100/H200` 視 queue 情況加速批次執行
3. 不假設多卡

第一版最低建議：

- `A100 40GB` 或 `L40S 48GB` 單卡

這對 7B 模型非常足夠，也比較符合實際排程彈性。

### 2.5 Benchmark 選擇

第一版固定如下：

1. 自建 paired benchmark：20 題
2. `FEA-Bench Lite` 中挑選 20 題
3. `SWE-bench Lite` 中挑選 20 題

注意：

- FEA-Bench 與 SWE-bench 都只作為外部驗證，不是主 benchmark。
- 主 benchmark 仍然是自建 paired benchmark，因為只有這條線可以最乾淨地定義 gold assumptions。

---

## 3. 共同研究框架

### 3.1 每題固定三個版本

每個 task 都必須包含：

1. `Full Spec`
   - 完整需求
   - 作為 oracle version

2. `Redacted Spec`
   - 從 Full Spec 刻意移除部分關鍵規格
   - 用來創造 hidden assumption 空間

3. `Gold Assumptions`
   - 人工標註：當 agent 看到 Redacted Spec 時，合理需要補上的 assumptions

### 3.2 每題固定三組條件

所有 benchmark 都跑同一套三組：

1. `Direct on Redacted`
   - 直接用 Redacted Spec 執行 agent

2. `Direct on Full`
   - 直接用 Full Spec 執行 agent
   - 作為 upper bound

3. `Monitor-then-Act on Redacted`
   - 先由 monitor 對 Redacted Spec 產生 assumption report
   - 經過 oracle-style review 修正
   - 再交回 agent 執行

核心比較不是：

- Redacted vs Full

而是：

- `Monitor-then-Act on Redacted` 是否接近 `Direct on Full`

### 3.3 Human-in-the-loop 的可重現化

正式實驗不使用自由的人類 prompt editing。

改用 `oracle-style review`：

1. reviewer 只能依據 `Full Spec` 中被刪掉的資訊修正 assumption report
2. reviewer 行為限制為：
   - `accept`
   - `reject`
   - `edit`
   - `add missing assumption`
3. reviewer 不得額外加入 Full Spec 之外的新需求

這樣做的目的：

1. 減少 reviewer 能力差異
2. 保持實驗可重現
3. 讓 benchmark 間結果更可比

---

## 4. Assumption Taxonomy

第一版固定用以下五類：

1. `Functional`
   - 功能需求細節
   - 例：是否需要登入、是否需要 contact form

2. `Implementation`
   - 技術選型、架構決策
   - 例：前後端分離、是否使用資料庫、是否需要 API server

3. `Environment`
   - 平台、執行環境、部署與相依限制
   - 例：部署到 Vercel、Python 版本、現有 repo API 慣例

4. `Validation`
   - 驗收方式、測試範圍、edge cases
   - 例：是否需要 mobile responsive、error handling、backward compatibility

5. `NonFunctional`
   - 效能、安全、可維護性、可存取性等
   - 例：SEO、a11y、rate limiting、latency requirement

---

## 5. Monitor Report Schema

第一版 monitor 統一輸出 JSON，格式如下：

```json
{
  "task_id": "example-001",
  "task_summary": "Build a portfolio website",
  "assumptions": [
    {
      "id": "A1",
      "statement": "The website can be implemented as a static site without a backend",
      "type": "Implementation",
      "evidence": [
        "Prompt mentions portfolio pages but no persistence requirement",
        "No server-side behavior is specified"
      ],
      "risk_if_wrong": "A contact form with message storage would fail to meet requirements",
      "needs_confirmation": true,
      "confidence": 0.72,
      "proposed_resolution": "Ask whether the contact feature must store submissions"
    }
  ],
  "open_questions": [
    "Should contact information be an email link or a real submission form?"
  ]
}
```

正式實驗中，若 monitor 不是輸出 JSON，該次結果視為格式失敗，需重跑。

---

## 6. 推論與執行預設

### 6.1 Generation defaults

第一版建議固定：

- `temperature = 0.0`
- `top_p = 1.0`
- `max_new_tokens = 4096`
- `seed = fixed`

若 benchmark 題目需要較長輸出，可對 agent execution 提高到：

- `max_new_tokens = 8192`

但 monitor report 仍維持較短輸出，以降低不穩定性。

### 6.2 Context strategy

各 benchmark 原則：

1. 自建 paired benchmark
   - 直接提供完整任務描述與 starter repo

2. FEA-Bench
   - 固定相同 code context 載入策略
   - 不讓 `Full` 和 `Redacted` 的 code context 不一致

3. SWE-bench
   - 固定相同 retrieval / repository setup
   - 差異只能來自 spec text，而不是工具行為差異

### 6.3 Randomness control

正式結果每題至少跑一次 deterministic setting。

若資源允許，之後可補：

- 每題 3 seeds

但第一版主結果先不做多 seed，避免成本失控。

---

## 7. Benchmark 1: 自建 Paired Benchmark

### 7.1 角色定位

這是主 benchmark，用來直接驗證：

1. monitor 能不能抽出 hidden assumptions
2. human correction 是否能改善結果
3. 整個流程是否適用於開放式 coding-spec 任務

### 7.2 題目組成

總共 20 題，建議分成四類，每類 5 題：

1. portfolio / personal website
2. small web app / dashboard
3. backend service / API
4. CLI / automation / data utility

### 7.3 每題必備欄位

每題至少包含：

- `task_id`
- `domain`
- `starter_repo`
- `full_spec`
- `redacted_spec`
- `gold_assumptions`
- `acceptance_tests`
- `redaction_rationale`
- `difficulty`

### 7.4 Redaction 原則

優先刪除：

- 是否需要 backend
- 是否需要 persistent storage
- contact 功能的具體形式
- auth / session
- deployment target
- accessibility / responsive / SEO
- data format / API contract
- edge case handling

不要刪除：

- 核心任務目標
- 執行方式
- 必要輸入輸出介面

### 7.5 Ground truth 標註規則

`Gold Assumptions` 必須是：

1. 從 Full Spec 被刪掉後，在 Redacted Spec 下形成合理多解空間的資訊
2. 對最終設計或驗收結果有實質影響
3. 能以簡短陳述句表達

不標註：

- 無關緊要的小偏好
- 只是措辭不同但不影響結果的差異

### 7.6 評估

這條 benchmark 的主要指標：

1. `Assumption Precision`
2. `Assumption Recall`
3. `Assumption F1`
4. `Task Success Rate`
5. `Requirement Alignment Score`
6. `Human Review Time`
7. `Over-report Rate`

---

## 8. Benchmark 2: FEA-Bench

### 8.1 角色定位

FEA-Bench 用來驗證方法在真實 repository-level feature implementation 環境中是否仍成立。

第一版使用：

- `FEA-Bench Lite` 中挑選 20 題

### 8.2 任務挑選標準

挑題標準：

1. 題目文字描述足夠長，可做 redaction
2. 有明確 feature behavior 或 edge case 可被刪除
3. 官方 evaluation 可在可接受時間內完成
4. 不全來自同一 repo

### 8.3 Full / Redacted 建置原則

`Full Spec` 建議包含：

- 原始 issue / request 文字
- 必要的 doc changes
- 相關 edge case 說明
- 必要 comments 中的限制條件

`Redacted Spec` 則移除：

- edge case 描述
- example-specific behavior
- backward compatibility hints
- implementation constraints 文字說明

重要：

- code context 必須固定
- new component signatures 若是 benchmark 基本設定的一部分，應保留

### 8.4 Gold assumptions 類型

常見標註方向：

- 邊界行為
- 既有模組整合方式
- 回傳格式語義
- backward compatibility
- failure handling

### 8.5 評估

這條 benchmark 主要看：

1. `Official Resolved Rate`
2. `Assumption F1`
3. `Gap Closure Rate`

其中：

```text
Gap Closure Rate =
(MonitorRedacted - DirectRedacted) / (DirectFull - DirectRedacted)
```

這個值越高，代表 monitor 越能補回被 redaction 拿掉的資訊價值。

---

## 9. Benchmark 3: SWE-bench

### 9.1 角色定位

SWE-bench 用來驗證方法在真實 issue-resolution 型 coding task 上是否成立。

第一版使用：

- `SWE-bench Lite` 中挑選 20 題

不使用 Verified 作為主集，原因是：

1. Lite 成本更低
2. 更適合第一版方法驗證
3. 可降低測試與題述不一致所帶來的噪音

### 9.2 任務挑選標準

挑題標準：

1. issue statement 可被切成 `Full` 與 `Redacted`
2. 保留主要 bug localization 線索後仍可執行
3. 問題描述中包含可被刪除的行為限制、邊界條件或版本要求

避免選：

1. 完全仰賴測試細節才能理解的題目
2. 題目敘述過短，無法形成 assumption 空間的 task
3. 已知題意與測試不完全一致的高風險 task

### 9.3 Full / Redacted 建置原則

`Full Spec` 包含：

- 原始 problem statement
- 必要 comments 或補充說明

`Redacted Spec` 移除：

- edge-case behavior
- version-specific constraints
- expected output examples
- failure mode 細節

不要移除：

- 關鍵檔案線索
- 主要 module / API 名稱
- 必要 reproduction clue

否則你測到的是定位能力下降，不是 hidden assumption。

### 9.4 Gold assumptions 類型

常見標註方向：

- expected semantics of output
- version compatibility
- edge case handling
- backward compatibility
- API contract interpretation

### 9.5 評估

這條 benchmark 主要看：

1. `Official Resolved Rate`
2. `Assumption F1`
3. `Error Taxonomy`

建議將失敗分成：

- assumption missed
- assumption extracted but ignored in execution
- execution/tool failure
- benchmark ambiguity

---

## 10. Pilot 與正式實驗

### 10.1 Pilot

不要直接跑 20 + 20 + 20。

先跑：

- 自建 benchmark：5 題
- FEA-Bench：5 題
- SWE-bench：5 題

Pilot 目標：

1. 檢查 Full / Redacted / Gold 定義是否穩定
2. 檢查 monitor report 是否可讀
3. 檢查 evaluation pipeline 是否跑通
4. 檢查 redaction 是否過強或過弱

### 10.2 Pilot 通過標準

至少滿足：

1. 超過 80% 題目能成功產生合法 JSON report
2. 超過 80% 題目能順利完成 benchmark evaluation
3. 標註者在 pilot 後能穩定區分 gold assumptions

若未達標，不擴充到正式 20 題。

### 10.3 正式實驗

Pilot 通過後再擴充至：

- 自建 20 題
- FEA 20 題
- SWE 20 題

總共 60 題，每題三個條件。

總 run 數：

```text
60 tasks x 3 conditions = 180 runs
```

如果正式實驗做 3 seeds，則變成：

```text
180 x 3 = 540 runs
```

第一版先不要做 3 seeds 全量跑。

---

## 11. 資料夾規劃

建議 repo 結構如下：

```text
docs/
  benchmark_execution_plan.md
  annotation_guideline.md
  report_schema.md

data/
  self_bench/
    tasks/
    pilot/
  fea_bench/
    raw/
    curated/
  swe_bench/
    raw/
    curated/

configs/
  models/
    qwen25_coder_7b.yaml
  experiments/
    direct_redacted.yaml
    direct_full.yaml
    monitor_then_act.yaml

src/
  monitor/
  agents/
  benchmarks/
  eval/

results/
  pilot/
  main/
```

---

## 12. 結果表欄位

每個 run 至少記錄：

- `benchmark`
- `task_id`
- `condition`
- `model_name`
- `spec_variant`
- `resolved`
- `assumption_tp`
- `assumption_fp`
- `assumption_fn`
- `review_edits`
- `review_time_sec`
- `tokens_input`
- `tokens_output`
- `runtime_sec`
- `failure_type`
- `notes`

---

## 13. 主要指標

### 13.1 Assumption-level

- Precision
- Recall
- F1

### 13.2 Task-level

- Success Rate
- Official benchmark pass / resolved rate
- Requirement Alignment Score

### 13.3 Human-cost

- Review time
- Number of edits
- Number of added assumptions

### 13.4 Efficiency

- Tokens
- Runtime
- Cost per successful task

### 13.5 Gap Closure

最重要的綜合指標之一：

```text
Gap Closure Rate =
(MonitorRedacted - DirectRedacted) / (DirectFull - DirectRedacted)
```

解釋：

- 0 表示 monitor 沒補回任何被拿掉資訊的價值
- 1 表示 monitor 完全補回 Full Spec 帶來的提升

---

## 14. 執行排程

### Week 1

1. 完成 taxonomy
2. 完成 report schema
3. 固定 model 與 inference backend
4. 跑通 FEA / SWE 基本環境
5. 起草自建 benchmark 前 3 題

### Week 2

1. 完成 pilot 所需 5 + 5 + 5 題
2. 完成 annotation guideline
3. 完成 redaction guideline
4. 實作 monitor report 產生流程

### Week 3

1. 跑 pilot 三組條件
2. 修正 schema 與標註規則
3. 修正 prompt 與 review protocol

### Week 4

1. 擴充到 20 + 20 + 20 題
2. 完成 benchmark curate
3. 開始正式實驗

### Week 5

1. 跑完全部三組條件
2. 匯總結果
3. 做 error taxonomy

### Week 6

1. 寫報告
2. 做 case study
3. 準備 demo

---

## 15. 風險與控管

### 15.1 GPU queue 不穩

控管方式：

1. 選單卡可跑的 7B 模型
2. 每題獨立存檔，可中斷續跑
3. 先完成 pilot，再批次擴充

### 15.2 Redaction 不乾淨

控管方式：

1. 每題要有 redaction rationale
2. pilot 後做一次人工 review
3. 不允許刪除核心 bug localization 線索

### 15.3 Gold assumptions 太主觀

控管方式：

1. 寫 annotation guideline
2. 至少兩人 review pilot 題目
3. 對爭議項目保留 adjudication 記錄

### 15.4 Benchmark 過度異質

控管方式：

1. 三條 benchmark 使用同一個核心 protocol
2. 結果先做 benchmark 內分析，再做 benchmark 間比較
3. 不直接把不同 benchmark 的 raw success rate 混成單一結論

---

## 16. 第一版不做的事

為了控制 scope，第一版先不做：

1. 多模型大規模比較
2. 多輪互動式澄清對話
3. 即時前端 dashboard
4. 大量 multi-seed 正式統計
5. 完全自動化 assumption verification

---

## 17. 下一步待完成文件

本文件落地後，應立即補兩份文件：

1. `docs/annotation_guideline.md`
   - 定義 gold assumptions 的標註規則
   - 定義 accept / reject / edit / add 的 oracle review protocol

2. `docs/report_schema.md`
   - 固定 monitor JSON schema
   - 固定欄位型別與合法值

---

## 18. 已確認的重要執行決策

本專案第一版目前已固定：

1. 主模型：`Qwen/Qwen2.5-Coder-7B-Instruct`
2. Monitor 與 coder 先使用同一模型
3. Benchmark：自建 20、FEA 20、SWE 20
4. FEA 與 SWE 先用 Lite 子集
5. 所有 benchmark 統一跑三組條件
6. PACE ICE GPU 不穩定，因此設計為單卡、可恢復、批次化執行

---

## 19. 參考來源

以下來源用於固定第一版規格：

1. Qwen 官方 Qwen2.5-Coder 頁面：
   - https://qwen2.org/qwen2-5-coder/
2. FEA-Bench 官方 repo：
   - https://github.com/microsoft/FEA-Bench
3. FEA-Bench 論文：
   - https://aclanthology.org/2025.acl-long.839/
4. SWE-bench 官方網站：
   - https://www.swebench.com/
5. SWE-bench Lite 頁面：
   - https://www.swebench.com/lite.html
6. OpenAI 對 SWE-bench Verified 的近期分析：
   - https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
