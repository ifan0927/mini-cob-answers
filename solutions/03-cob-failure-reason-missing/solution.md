# 03｜COB 處理失敗，但查不到失敗原因：解答

## 根本原因

`LockErrorRecorder.recordError` 用的是預設傳播行為 `REQUIRED`。它是在 `ItemProcessListener.onProcessError` 裡被呼叫的，而這個 listener 執行在 **chunk 交易**之內，所以錯誤寫入直接加入了 chunk 交易。

接著發生的事：

1. processor 丟出 `UnsupportedCurrencyException`，Spring Batch 讓整個 chunk 交易 **rollback**，錯誤訊息的 UPDATE 也一起被撤銷。
2. 下一輪（stateful retry 的 recovery）判定這個 item 可以 skip，跳過後重新處理 chunk 裡其餘的 item，然後提交。這一輪不會再呼叫 `onProcessError`。
3. 步驟結束時，`CobLockingStepListener.afterStep` 釋放所有「沒有錯誤」的鎖。這筆貸款的鎖上沒有錯誤（被 rollback 掉了），所以**連鎖也一起被釋放**。

最後的結果就是「skipped: 1，但鎖表裡什麼都沒有」。

## 修正

```diff
diff --git a/src/main/java/com/minicob/cob/LockErrorRecorder.java b/src/main/java/com/minicob/cob/LockErrorRecorder.java
index a6a1836..257e302 100644
--- a/src/main/java/com/minicob/cob/LockErrorRecorder.java
+++ b/src/main/java/com/minicob/cob/LockErrorRecorder.java
@@ -5,6 +5,7 @@ import java.io.StringWriter;
 import org.slf4j.Logger;
 import org.slf4j.LoggerFactory;
 import org.springframework.stereotype.Service;
+import org.springframework.transaction.annotation.Propagation;
 import org.springframework.transaction.annotation.Transactional;
 
 /**
@@ -21,7 +22,8 @@ public class LockErrorRecorder {
         this.repository = repository;
     }
 
-    @Transactional
+    // The caller's chunk transaction is about to roll back; the error has to be committed on its own.
+    @Transactional(propagation = Propagation.REQUIRES_NEW)
     public void recordError(Long loanId, String message, Throwable error) {
         repository.findById(loanId).ifPresentOrElse(
                 lock -> lock.recordError(message, stacktraceOf(error)),
```

`REQUIRES_NEW` 會暫停外層交易、另開一個新交易（**另一條資料庫連線**），寫完立即提交，不受外層 rollback 影響。

使用 `REQUIRES_NEW` 的注意事項：

- **需要第二條連線**。worker 執行緒數乘以 2，再加上 manager，連線池要夠大，否則就是第 10 題。
- **不能更新外層交易已經鎖住的列**，否則內層要等外層釋放，外層卻在等內層返回，等於自己和自己死結。本專案的 chunk 交易在 process 階段還沒碰過 `account_lock`，所以安全。
- **看不到外層尚未提交的資料**。

## 怎麼找到它

1. 先確認錯誤有被記錄的動作：listener 的 WARN log 有印出來，可見 `recordError` 有被呼叫，但資料庫沒有結果。也就是「做了但沒留下來」，問題在交易。
2. `JpaTransactionManager` DEBUG log 會顯示 `Participating in existing transaction`，表示加入了 chunk 交易，而不是 `Suspending current transaction, creating new transaction`。
3. 再對照 Spring Batch 的行為：processor 例外會讓 chunk rollback（`FaultTolerantChunkProcessor` 預設 `rollbackClassifier` 對所有例外都 rollback）。
4. 「連鎖都不見了」這個線索，可以追到 `afterStep` 釋放的是「無錯誤」的鎖。

## 面試時可以怎麼講

> 批次裡的錯誤紀錄要用獨立交易寫，因為觸發錯誤的那個交易本身就要 rollback。我們的 COB 在 `onProcessError` 寫鎖表錯誤，原本用 `REQUIRED` 加入 chunk 交易，結果跟著 rollback，營運完全看不到失敗原因。改成 `REQUIRES_NEW` 之後就保留下來了。代價是每次要多一條連線，所以連線池也要一起評估。

可以準備的追問：

- **`REQUIRES_NEW` 和 `NESTED` 的差別？** `NESTED` 用 savepoint，仍然是同一個實體交易，外層 rollback 時內層也會被撤銷，所以不適合「一定要留下來」的紀錄。另外 JPA/Hibernate 對 savepoint 的支援有限，`NESTED` 主要用在 `DataSourceTransactionManager`。
- **其他做法？** 寫到交易外的通道，例如非同步的事件或訊息佇列；也可以在 `afterChunk`、`afterStep` 這類已經在交易外的時間點彙整錯誤。
- **Spring Batch 的 skip listener（`onSkipInProcess`）不是更適合嗎？** skip listener 會在 chunk 提交前、於交易內被呼叫，所以會和成功的 item 一起提交，也是可行的做法。但它只在「確定 skip」時觸發，拿不到每一次失敗嘗試的資訊。Fineract 選擇在 `onProcessError` 用獨立交易記錄。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-cob/src/main/java/org/apache/fineract/cob/listener/AbstractLoanItemListener.java`：`updateAccountLockWithError(...)` 透過 `requiresNewTransactionJdbcTemplate.executeWithoutResult(...)` 把錯誤和堆疊寫回鎖表；`onReadError`、`onProcessError`、`onWriteError` 都走這條路。
- `fineract-provider/src/main/java/org/apache/fineract/infrastructure/core/config/JdbcTransactionConfig.java`：`requiresNewTransactionJdbcTemplate` bean，`setPropagationBehavior(PROPAGATION_REQUIRES_NEW)`。
- `fineract-cob/src/main/java/org/apache/fineract/cob/domain/AccountLock.java`：`error`、`stacktrace` 欄位與 `setError(...)`。
