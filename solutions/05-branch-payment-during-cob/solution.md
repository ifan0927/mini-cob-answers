# 05｜COB 期間分行入帳，該筆貸款當天沒有關帳：解答

## 根本原因

`Loan` 有 `@Version`，所以分行入帳和 COB 同時改同一列時，會被樂觀鎖抓到。這部分設計是對的。問題出在 **retry 時用的是過期的物件**：

1. reader 在 chunk 交易內讀到貸款（version = v1）。
2. 分行從另一條連線入帳並提交（version = v2）。
3. writer `flush` 時執行 `UPDATE ... WHERE id = ? AND version = v1`，影響 0 列，丟出 `ObjectOptimisticLockingFailureException`。step 設定會 retry 這類例外。
4. chunk 交易 rollback。Spring Batch 重試這個 chunk 時，會把**緩衝住的同一批 item** 再交給 processor。預設 `processorTransactional = true`，所以會重新處理，但 item 本身不會重讀。
5. 這個 item 是上一個（已關閉的）EntityManager 留下的 **detached 物件，version 仍是 v1**。processor 直接拿它算，writer 做 `merge` 時發現版本不符，又一次樂觀鎖例外。
6. 每一次 retry 都一樣，次數用完之後 skip，這筆貸款當天沒有關帳。

retry 只有在「每次重試都重新讀取最新狀態」時才有意義。

## 修正

```diff
diff --git a/src/main/java/com/minicob/cob/LoanCobItemProcessor.java b/src/main/java/com/minicob/cob/LoanCobItemProcessor.java
index 1c4e144..82e2bab 100644
--- a/src/main/java/com/minicob/cob/LoanCobItemProcessor.java
+++ b/src/main/java/com/minicob/cob/LoanCobItemProcessor.java
@@ -4,6 +4,7 @@ import com.minicob.cob.step.CobStepContext;
 import com.minicob.cob.step.LoanCobBusinessStep;
 import com.minicob.context.BusinessDateContext;
 import com.minicob.loan.Loan;
+import com.minicob.loan.LoanNotFoundException;
 import java.util.List;
 import org.springframework.batch.item.ItemProcessor;
 import org.springframework.stereotype.Component;
@@ -14,14 +15,18 @@ import org.springframework.stereotype.Component;
 @Component
 public class LoanCobItemProcessor implements ItemProcessor<Loan, ProcessedLoan> {
 
+    private final CobLoanRepository repository;
     private final List<LoanCobBusinessStep> steps;
 
-    public LoanCobItemProcessor(List<LoanCobBusinessStep> steps) {
+    public LoanCobItemProcessor(CobLoanRepository repository, List<LoanCobBusinessStep> steps) {
+        this.repository = repository;
         this.steps = steps;
     }
 
     @Override
-    public ProcessedLoan process(Loan loan) {
+    public ProcessedLoan process(Loan item) {
+        // On a retry the item is the detached instance from the rolled-back attempt; work on the current row.
+        Loan loan = repository.findForCob(item.getId()).orElseThrow(() -> new LoanNotFoundException(item.getId()));
         CobStepContext context = new CobStepContext(BusinessDateContext.getCobDate());
         for (LoanCobBusinessStep step : steps) {
             step.execute(loan, context);
```

processor 一開始先在**目前的交易**內依 id 重讀貸款：

- 第一次嘗試時，這筆貸款已經在 persistence context 裡，查詢回傳的是同一個 managed 物件，不會讀到不同的狀態。
- retry 時是新的交易、新的 EntityManager，讀到的是 v2。COB 在 90,000 的基礎上計息，分行的入帳也保留下來。

## 怎麼找到它

1. log 裡同一筆貸款連續出現 3 次 `Row was updated or deleted by another transaction`（或 `StaleObjectStateException`），然後被 skip。可見「有 retry，但每次都失敗」。
2. 在 processor 設中斷點看 `item.getVersion()`，會發現 retry 時版本一直是舊的，和資料庫不一致。
3. 讀 Spring Batch `FaultTolerantChunkProcessor` 的 retry 流程：重試的是同一批 input item，不會重新呼叫 reader。
4. 結論：retry 前必須重讀實體。Fineract 用 `ReloaderService` 做的正是這件事。

## 面試時可以怎麼講

> 我們用 `@Version` 防止 lost update，衝突時讓 Spring Batch retry。但 Spring Batch retry 時，丟回 processor 的是上次 rollback 留下的 detached 實體，版本還是舊的，所以 retry 每次都撞同一個衝突，最後 skip。修法是 processor 先依 id 在當前交易重讀。Fineract 的 COB 也是這樣做的，每個 business step 執行前都會 reload item。

可以準備的追問：

- **樂觀鎖和悲觀鎖怎麼選？** COB 處理單筆貸款很快，衝突很少，樂觀鎖成本低。如果衝突頻繁，或重做的成本很高，可以在 reader 用 `SELECT ... FOR UPDATE`（`@Lock(PESSIMISTIC_WRITE)`）。代價是阻塞，而且要注意死結和逾時。
- **如果沒有 `@Version` 會怎樣？** 會變成 lost update：COB 的 UPDATE 是整列覆寫，會把分行扣掉的本金加回去，而且不會有任何錯誤。
- **為什麼 writer 要 `flush`？** 讓衝突在 write 階段就丟出來，才會經過 retry 和 skip 的政策。如果拖到 commit 才發現，例外會直接讓 step 失敗。
- **外部系統直接寫 DB 的風險？** 繞過了應用層的鎖檢查（本專案的帳戶鎖只擋得住走 API 的寫入）。所以資料庫層的保護（版本欄位、約束）是最後一道防線。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-cob/src/main/java/org/apache/fineract/cob/COBBusinessStepServiceImpl.java`：`executeBusinessSteps(...)` 在每個 business step 執行前呼叫 `item = reloaderService.reload(item)`。
- `fineract-cob/src/main/java/org/apache/fineract/cob/service/ReloaderService.java`、`ReloadService.java`：依型別重新載入實體。
- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/LoanCOBWorkerConfiguration.java`：`faultTolerant().retryPolicy(...)`、`skip(...)`、`skipLimit(...)` 的設定。
