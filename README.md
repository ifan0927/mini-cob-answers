# mini-cob：解答與驗證

這個 repo 是 [mini-cob-learner](https://github.com/ifan0927/mini-cob-learner) 的解答。**做完題目之前請不要看。**

## 內容

```
baseline/                 全部正確的版本（含 exercises/ 題目），整套測試全部通過
solutions/NN-*/solution.md
                          每題的根本原因、修正 diff、怎麼找到它、面試時可以怎麼講、
                          對應的 Fineract 程式碼位置
solutions/12-code-review/ 程式碼審查的參考答案
patches/bugs/NN.patch     baseline → 埋入第 NN 題 bug 的 diff
patches/fixes/NN.patch    learner → 只修第 NN 題的 diff（等於 bugs/NN.patch 的反向）
verification/
  REPORT.md               驗證報告（方法、結果、這次驗證過程中發現並修正的問題）
  matrix-result.md        最近一次矩陣執行的原始結果
  verify-matrix.sh        重跑驗證矩陣
  verify_matrix.py
  expected-failures.tsv   每題在 learner 版本中應該出現的失敗訊息（regex）
```

learner 版本 = `baseline/` 套用 `patches/bugs/*.patch`。

## 執行 baseline

```bash
cd baseline
./mvnw test        # 22 個測試全部通過，約 20～30 秒
```

## 重跑驗證矩陣

需要 Java 21、git、Python 3，第一次建置需要能連到 Maven Central。

```bash
cd verification
./verify-matrix.sh                                   # 完整矩陣，約 10 分鐘
./verify-matrix.sh --learner ../../mini-cob-learner  # 同時比對實際交付的 learner repo
./verify-matrix.sh --only 04,10 --repeat 5           # 只跑部分題目的 (c)，重複 5 次檢查是否不穩定
```

矩陣內容：

- **(a)** baseline：全部測試通過。
- **(b)** learner：每題測試都失敗，而且失敗訊息符合 `expected-failures.tsv`，證明失敗的原因就是該題的 bug，而不是編譯錯誤或其他題目的 bug。整套執行和單獨執行（`-Dtest=...`）都要檢查。非練習測試必須全部通過。
- **(c)** learner 只修第 i 題：第 i 題通過，其他 10 題仍然失敗，非練習測試全部通過。

## 題目一覽

| # | 症狀 | 主題 |
|---|---|---|
| 01 | 被拒絕的還款出現在還款明細裡 | `@Transactional` 代理機制 |
| 02 | 已婉拒的貸款申請仍然入帳 | rollback 規則 |
| 03 | COB 處理失敗，但查不到失敗原因 | 交易傳播與錯誤紀錄 |
| 04 | 貸款量一大，COB 就漏處理或重複處理 | singleton 可變狀態 × 分區多執行緒 |
| 05 | COB 期間分行入帳，該筆貸款當天沒有關帳 | 樂觀鎖與 retry |
| 06 | 逾期報表越來越慢 | N+1 查詢 |
| 07 | 同一營業日重跑 COB，利息被計了兩次 | 批次重跑冪等性 |
| 08 | COB 中止後，健康的貸款整天無法還款 | 失敗後的鎖釋放 |
| 09 | 連續兩晚的 COB，第二晚像是還停在第一晚 | thread-local context × 執行緒池 |
| 10 | 申請量瞬間湧入時，服務卡住幾秒後大量失敗 | 連線池耗盡（巢狀 REQUIRES_NEW） |
| 11 | 美元貸款的每日利息和對帳試算表差幾分錢 | BigDecimal 精度與捨入 |
| 12 | 程式碼審查 | － |

Fineract 的程式碼位置以 apache/fineract `develop` 分支 commit `b94b2dd` 為準。
