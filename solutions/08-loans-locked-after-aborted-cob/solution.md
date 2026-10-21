# 08｜COB 中止後，健康的貸款整天無法還款：解答

## 根本原因

鎖的生命週期：

1. worker step 開始前（`beforeStep`）：替整個 partition 的貸款上鎖，並在獨立交易中提交。
2. 每個 chunk 寫入時：writer 在 chunk 交易內刪掉**已處理**貸款的鎖。
3. step 結束後（`afterStep`）：釋放 partition 內所有**沒有錯誤**的鎖，也就是「沒輪到處理」或「處理被 rollback」的那些。

learner 版本的 `afterStep` 只在 `stepExecution.getStatus() == COMPLETED` 時才釋放。

這次的情境：攤還表毀損的貸款觸發 `LoanDataCorruptedException`，這是 `noSkip`，step 直接 `FAILED`。

- 和它同一個 chunk 的健康貸款：處理結果和鎖的刪除都跟著 chunk rollback，鎖還在。
- 同一個 partition 裡還沒輪到的貸款：從來沒被處理，鎖也還在。
- `afterStep` 因為狀態是 `FAILED` 而什麼都不做。

這些健康的貸款就一直被鎖著，還款 API 回 409，直到有人手動清表。

## 修正

```diff
diff --git a/src/main/java/com/minicob/cob/CobLockingStepListener.java b/src/main/java/com/minicob/cob/CobLockingStepListener.java
index 01e935b..354867b 100644
--- a/src/main/java/com/minicob/cob/CobLockingStepListener.java
+++ b/src/main/java/com/minicob/cob/CobLockingStepListener.java
@@ -4,7 +4,6 @@ import java.time.LocalDate;
 import java.util.List;
 import org.slf4j.Logger;
 import org.slf4j.LoggerFactory;
-import org.springframework.batch.core.BatchStatus;
 import org.springframework.batch.core.ExitStatus;
 import org.springframework.batch.core.StepExecution;
 import org.springframework.batch.core.StepExecutionListener;
@@ -34,12 +33,11 @@ public class CobLockingStepListener implements StepExecutionListener {
 
     @Override
     public ExitStatus afterStep(StepExecution stepExecution) {
-        if (stepExecution.getStatus() == BatchStatus.COMPLETED) {
-            List<Long> loanIds = LoanCobPartitioner.loanIdsOf(stepExecution.getExecutionContext());
-            int released = lockService.releaseErrorFree(loanIds);
-            log.debug("{} finished with {}; released {} remaining locks", stepExecution.getStepName(),
-                    stepExecution.getStatus(), released);
-        }
+        // Runs whatever the outcome: a failed step must not leave the rest of its partition locked.
+        List<Long> loanIds = LoanCobPartitioner.loanIdsOf(stepExecution.getExecutionContext());
+        int released = lockService.releaseErrorFree(loanIds);
+        log.debug("{} finished with {}; released {} remaining locks", stepExecution.getStepName(),
+                stepExecution.getStatus(), released);
         return null;
     }
 }
```

不論成功或失敗都要釋放。帶錯誤的鎖（毀損的那筆）刻意保留，讓營運調查。下一次 COB 會用 `lockForCob` 的 take-over 邏輯重新接手。

## 怎麼找到它

1. COB 失敗後查 `account_lock`：多筆 `error_message IS NULL` 的鎖。沒有錯誤卻沒被釋放，表示釋放的程式沒有執行。
2. 找出所有刪鎖的地方：writer（只處理成功提交的 chunk）和 `afterStep`。
3. 在 `afterStep` 設中斷點：有進來，`status = FAILED`，然後被條件擋掉。

## 面試時可以怎麼講

> 資源清理要放在「一定會執行」的路徑上，概念和 `finally` 一樣。COB 會鎖住要處理的帳戶，正常情況由 writer 解鎖，失敗時靠 step listener 收尾。原本的實作只在成功時收尾，結果一筆壞資料讓整個 partition 的客戶整天無法還款。修正後無論成功或失敗都釋放無錯誤的鎖，有錯誤的保留下來調查。

可以準備的追問：

- **如果 JVM 直接被 kill，`afterStep` 也不會執行，怎麼辦？** 需要第二層機制：下一次 COB 開始時接手同一個 owner 的舊鎖（本專案的 `takeOver`）；監控 `locked_at` 太舊的鎖並告警；提供營運用的解鎖 API。Fineract 有 `StayedLockedLoansTasklet` 找出「應該解鎖卻還鎖著」的貸款並發出事件。
- **為什麼不在一個大交易裡上鎖、處理、解鎖？** 那樣鎖就沒有意義了。鎖必須先提交，其他交易（還款 API）才看得到。而且整個 partition 會變成一個超長交易。
- **listener 執行的順序？** `beforeStep` → stream `open` → chunks → stream `close` → `afterStep`。`afterStep` 在 step 狀態已經確定之後才被呼叫，所以可以依狀態決定行為。只是這題的正確做法是不依賴狀態。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/ApplyLoanLockTasklet.java`：worker 開始時上鎖，以 `requiresNewTransactionJdbcTemplate` 提交。
- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/LoanItemWriter.java`、`AbstractLoanItemWriter.java`：寫入成功後解除該批貸款的鎖。
- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/UnlockProcessedLoansTasklet.java`、`StayedLockedLoansTasklet.java`、`LoanAccountsStayedLockedBusinessEvent.java`：收尾，以及「仍然被鎖住」的偵測和通知。
- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/LoanLockingServiceImpl.java`：鎖的建立、刪除、錯誤更新。
