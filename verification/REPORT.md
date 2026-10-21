# mini-cob 驗證報告

- 驗證日期：2026-10-21
- 環境：OpenJDK 21.0.12、Apache Maven 3.9.11（透過 `./mvnw`）、Spring Boot 3.5.16、H2（記憶體）
- 方法：`verification/verify_matrix.py`，連續跑 **3 輪**，用來偵測不穩定的測試
- 原始輸出：`verification/matrix-result.md`

## 驗證項目

| 項目 | 內容 | 每輪檢查數 |
|---|---|---|
| 交付一致性 | 交付的 learner repo 的 `src/` ＝ baseline ＋ `patches/bugs/*.patch`（逐檔比對） | 1（只跑一次） |
| (a) | baseline：整套 22 個測試（14 個測試類別）全部通過 | 1 |
| (b) | learner：3 個非練習測試類別全部通過 | 3 |
| (b) | learner 整套執行：11 個練習測試都失敗，而且失敗訊息符合 `expected-failures.tsv` | 11 |
| (b) | learner **單獨執行**每題（`./mvnw test -Dtest=ExNN...`，也就是 task.md 教的跑法）：同樣失敗，而且原因相同 | 11 |
| (c) | learner 只修第 i 題：第 i 題通過 | 11 |
| (c) | learner 只修第 i 題：其他 10 題仍然失敗（確認 bug 彼此隔離） | 11 |
| (c) | learner 只修第 i 題：非練習測試全部通過 | 11 |

「失敗原因就是該題的 bug」的判定方式：每題的斷言訊息都帶有描述症狀的 `as(...)` 標籤，再用 regex 比對**標籤和實際值**。例如第 07 題必須是「interest accrued for one day … but was: 40」，第 10 題必須出現 `CannotCreateTransactionException`。編譯錯誤、其他題的 bug 或環境問題造成的失敗，都不會符合這些條件。

## 結果

**178 / 178 項檢查通過，0 項失敗**（3 輪 × 59 項 ＋ 交付一致性 1 項）。

| 項目 | 第 1 輪 | 第 2 輪 | 第 3 輪 |
|---|---|---|---|
| (a) baseline 全部通過 | 1/1 | 1/1 | 1/1 |
| (b) 非練習測試通過 | 3/3 | 3/3 | 3/3 |
| (b) 整套執行：各題因自身 bug 失敗 | 11/11 | 11/11 | 11/11 |
| (b) 單獨執行：各題因自身 bug 失敗 | 11/11 | 11/11 | 11/11 |
| (c) 只修 i → 第 i 題通過 | 11/11 | 11/11 | 11/11 |
| (c) 只修 i → 其他 10 題仍失敗 | 11/11 | 11/11 | 11/11 |
| (c) 只修 i → 非練習測試通過 | 11/11 | 11/11 | 11/11 |

交付一致性：通過。baseline 整套測試耗時 19～24 秒（含 Maven 啟動）。

## 各題在 learner 版本中的實際失敗訊息（第 1 輪，整套執行）

| # | 失敗訊息（節錄） |
|---|---|
| 01 | `[repayment history after the API answered 422 to the only repayment attempt] Expecting empty but was: [{"repaymentId":1,"loanId":1,"amount":100001.0,"principalP...` |
| 02 | `[loans on the books of customer C-EX02 after the declined application] Expecting actual: [4000000.00, 2000000.00] to contain exactly (and in same order):` |
| 03 | `[account lock of the loan COB could not process] Expecting Optional to contain a value but it was empty. java.lang.AssertionError: [account lock of the loan COB...` |
| 04 | `[loans not closed exactly once for 2026-04-16 (289 of 400)] Expecting empty but was: ["loan 61: closed=null interest=0.00 (expected 20) accrual entries=0", "loa...` |
| 05 | `[last closed business date of the loan] expected: 2026-04-16 (java.time.LocalDate) but was: null org.opentest4j.AssertionFailedError:` |
| 06 | `[SQL statements executed by one overdue report call with 20 overdue loans] Expecting actual: 22L to be less than or equal to:` |
| 07 | `[interest accrued for one day on loan 433] expected: 20 but was: 40.00 org.opentest4j.AssertionFailedError:` |
| 08 | `[repayments on healthy loans the morning after the aborted COB] Expecting empty but was: ["loan 423 -> HTTP 409", "loan 424 -> HTTP 409", "loan 425 -> HTTP 409"...` |
| 09 | `[last closed date after night two] expected: 2026-04-16 (java.time.LocalDate) but was: 2026-04-15 (java.time.LocalDate) org.opentest4j.AssertionFailedError:` |
| 10 | `[loan applications that failed out of 8] Expecting empty but was: ["HTTP 500: {"type":"about:blank","title":"Internal Server Error","status":500,"detail":"org.s...` |
| 11 | `[one day of interest on 250,000.00 USD at 3%] expected: 20.55 but was: 20.50 org.opentest4j.AssertionFailedError:` |

## 驗證過程中發現並修正的問題

1. **第 09 題單獨執行時不會失敗（已修正）。**
   第一版矩陣只做整套執行，全部通過。加入「單獨執行」檢查後發現，`./mvnw test -Dtest=Ex09...` 在 learner 版本上**會通過**：新建立的執行緒池在執行緒數還沒到 core size 之前，即使有閒置的執行緒也會開新的，而新執行緒在建立當下繼承到的是正確日期。整套執行時之所以會失敗，只是因為其他測試先把池子填滿了。
   第一次修正改成很多個小 partition，結果第一晚出現 `null`。原因是觸發了**第 04 題的 bug**，這會破壞隔離性（只修第 09 題時也不會通過）。
   最後的修正：該測試以 `mini-cob.cob.worker-threads=1` 執行，task.md 也同步說明正式環境是這個設定。這樣只有一個 partition，不會牽動第 04 題；第二晚一定會重用第一晚的執行緒。修正後 learner 不論整套或單獨執行，都穩定失敗在「第二晚 expected 2026-04-16 but was 2026-04-15」。
2. **expected-failures 的條件收緊。** 第 03、09 題原本的 regex 接受多種訊息，現在只接受該題 bug 實際會產生的那一種。

## 重跑方式

```bash
cd verification
./verify-matrix.sh --learner ../../mini-cob-learner --repeat 3
```
