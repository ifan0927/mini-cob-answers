# 12｜程式碼審查：參考答案

以下以「11 題都修好之後」的 baseline 為準，依嚴重程度排序。每一點都說明位置、風險、建議和代價。題目要求至少 8 點，這裡列出 16 點作為參考。

## A. 正確性與資料一致性

### A1. 還款冪等鍵的並發競爭（`RepaymentService.repay`）

**問題**：先 `findByIdempotencyKey` 再寫入是 check-then-act。同一把鍵的兩個請求幾乎同時到達時，兩邊都查不到，其中一邊會撞上 `idempotency_key` 的唯一約束。這時丟出的是 `DataIntegrityViolationException`，被 `ApiExceptionHandler` 歸類為 500，客戶端只會看到伺服器錯誤，不知道其實已經成功。

**建議**：捕捉唯一約束違反，重新查詢後回傳原本的結果（`replayed=true`）；或先插入一筆「處理中」的冪等紀錄，用資料庫唯一約束搶佔，再處理業務。Fineract 用 `IdempotencyStoreFilter` 配合 command source 表處理。

**代價**：需要定義「處理中」狀態的逾時，以及卡住時的回收機制。

### A2. 冪等鍵的範圍與保存期限

**問題**：鍵是全域唯一，沒有綁定呼叫者或通路，不同客戶端可能剛好用到同一把鍵。紀錄永久保存，也沒有清除機制。比對「是否同一請求」只看 `loanId + amount`。

**建議**：鍵的範圍改為 `(client_id, key)`；儲存請求內容的雜湊；設定保存期限（例如 24 到 72 小時）並定期清除。

### A3. 還款沒有樂觀鎖衝突的處理（`RepaymentService` / `ApiExceptionHandler`）

**問題**：兩筆不同鍵的還款同時修改同一筆貸款時，一筆會遇到 `ObjectOptimisticLockingFailureException`，API 回 409，但沒有說明可以重試。

**建議**：服務層對樂觀鎖衝突自動重試幾次（`@Retryable` 或手寫迴圈，重試時要開新交易並重讀）；或回傳明確的 `Retry-After`。Fineract 的 `SynchronousCommandProcessingService` 對 command 有 retry 機制。

### A4. 鎖檢查和入帳之間的時間窗（`RepaymentService.repay`）

**問題**：`isLocked` 檢查通過之後、交易提交之前，COB 可能已經替這筆貸款上了鎖並開始處理。雖然 `@Version` 最後會擋住其中一方，但 COB 那邊會被迫 retry，而且鎖的語意（COB 期間拒絕交易）沒有被嚴格執行。

**建議**：還款交易內對鎖表做 `SELECT ... FOR SHARE`，或對貸款做 `PESSIMISTIC_WRITE`，讓「檢查」和「寫入」在同一個鎖之下完成；或接受現狀，在文件中寫明樂觀鎖是最終防線。

### A5. 營業日推進與 COB 結果不是原子的（`CobService.closeBusinessDay`）

**問題**：job 成功之後才呼叫 `advanceTo`。如果中間程序掛掉，營業日沒有推進，但所有貸款都已經關帳。再次執行時 watermark 會跳過它們，所以不會重複計息，但會產生一次空跑，也需要人工確認。另外兩個請求同時呼叫 close-business-day 時，可能同時啟動兩個 job。

**建議**：用 job 狀態加上一個 `cob_run` 表（記錄日期、狀態、使用唯一約束）來序列化；或改用 Spring Batch 的 JobInstance 唯一性（以 cobDate 作為 identifying parameter，rerun 時改用 restart）。

### A6. 「同一天重跑」缺少資料庫層防護（`loan_transaction`）

**問題**：第 07 題修好後，冪等性只靠查詢條件。未來只要有人寫出另一條選取路徑，就可能再次重複提列。

**建議**：對提列類交易建立唯一約束 `(loan_id, type, transaction_date)`（只限 ACCRUAL 類型，可以用部分索引或分表）。

## B. 並發與鎖

### B1. 鎖的 take-over 沒有檢查 owner 和日期（`AccountLockService.lockForCob`）

**問題**：任何 COB 執行都會無條件接手既有的鎖，包括另一個仍在執行中的 COB（例如兩個實例誤啟動）。

**建議**：take-over 時檢查 `owner`、`cobBusinessDate`、`lockedAt` 的年齡，並用 `@Version` 防止兩邊同時接手。Fineract 有 `AccountLockCannotBeOverruledException` 處理這種情況。

### B2. 連線池容量沒有和 COB 並發度一起設計

**問題**：每條 COB worker 在 chunk 交易之外，錯誤處理還需要第二條連線（`REQUIRES_NEW`）。再加上 manager、API 流量，Hikari 預設 10 條在 `worker-threads` 調大時就可能不夠，也就是第 10 題的另一種觸發方式。

**建議**：啟動時驗證 `maximumPoolSize ≥ workerThreads × 2 + 預留量`；或讓 COB 使用獨立的 DataSource。

## C. 營運與可觀測性

### C1. 失敗資訊只在鎖表，沒有告警或彙總

**建議**：COB 結束時輸出「仍然被鎖住的貸款」事件或 metric（Fineract 有 `LoanAccountsStayedLockedBusinessEvent`）；提供查詢和解鎖的營運 API；用 Micrometer 輸出處理量、跳過數、耗時。

### C2. 錯誤回應洩漏內部資訊（`ApiExceptionHandler.unexpected`）

**問題**：500 錯誤時把 `e.toString()` 放進 `detail`，可能洩漏 SQL、類別名稱等內部細節。

**建議**：對外只回 correlation id，詳細內容寫進 log。

### C3. schema 由 Hibernate 自動產生（`ddl-auto: create-drop / update`）

**問題**：正式環境不應該用 `update`，它不會刪欄位、不處理資料遷移，也不會建立必要的索引。

**建議**：改用 Flyway 或 Liquibase。明確建立 `loan(status)`、`loan(last_closed_business_date)`、`installment(loan_id)`、`loan(customer_id, currency)` 等索引。Fineract 用 Liquibase。

## D. 效能

### D1. COB reader 逐筆查詢（`LoanItemReader.read`）

**問題**：每筆貸款各一次 `findForCob`（含攤還表），processor 再查一次。每個 chunk 會有 2 × chunk-size 條查詢。

**建議**：reader 依 chunk 批次 fetch（`where id in (...)`）；processor 的重讀只在 retry 時才做，或改為批次重讀。

### D2. 曝險加總查詢與索引（`LoanRepository.sumOutstandingPrincipal`）

**問題**：每次放款都要對客戶的貸款做加總，沒有 `(customer_id, currency, status)` 索引時會全表掃描。

## E. 可維護性與設計

### E1. 金額型別

**問題**：金額使用裸 `BigDecimal`，幣別與 scale 的規則散落在 `Currencies`、`Loan.disburse`、`InterestCalculator`。

**建議**：引入 `Money` value object，把幣別、scale、捨入規則集中管理（Fineract 的 `Money` 和 `MoneyHelper`）。

### E2. API 契約

- 金額 JSON 輸出為 `100001.0` 這種浮點表示，建議序列化成字串，或設定 `WRITE_BIGDECIMAL_AS_PLAIN`。
- `/api/cob/runs` 這類營運端點沒有授權保護。
- 建立放款沒有冪等鍵，用戶端重送會產生重複貸款。

### E3. 測試策略

- H2 和 PostgreSQL 在鎖、隔離等級、`FOR UPDATE` 的行為上有差異。並發相關的測試應該用 Testcontainers 跑 PostgreSQL。
- 缺少 Spring Batch restart 情境（JVM 中途停止後重啟）的測試。
