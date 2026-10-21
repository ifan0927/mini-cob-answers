# 09｜連續兩晚的 COB，第二晚像是還停在第一晚：解答

## 根本原因

COB 的業務邏輯從 `BusinessDateContext`（thread-local）讀取關帳日。實際做事的是 `cobTaskExecutor` 執行緒池裡的 worker 執行緒，而不是呼叫 `runCob` 的那條執行緒。learner 版本有兩個問題，合起來造成這個症狀：

1. `BusinessDateContext` 用的是 **`InheritableThreadLocal`**。它的值是在**子執行緒建立的那一刻**從父執行緒複製過去的，之後不再同步。
2. `CobTaskDecorator` 只傳遞 MDC（log 的 run id），**沒有**傳遞營業日。

於是：

- 應用程式啟動後的第一次 COB：執行緒池裡還沒有執行緒，提交工作時才建立，建立時繼承到當晚的日期。第一晚正確。
- 第二晚：執行緒池**重用**同一條執行緒，它身上帶的還是第一晚的日期。關帳日、逾期判斷、`last_closed_business_date` 全部停在前一天。

為什麼正式環境（1 條 worker）第二晚就出錯，worker 數比較多時卻要好幾晚才出錯？`ThreadPoolExecutor` 在執行緒數還沒達到 `corePoolSize` 之前，**即使有閒置的執行緒，也會為新工作建立新執行緒**。新執行緒在建立當下繼承到的是正確日期，所以 4 條 worker 時，前幾晚可能剛好都用到新執行緒；等池子滿了開始重用，問題才出現，而且只影響部分 partition。這也是這類 bug 在開發環境很難重現的原因。

`InheritableThreadLocal` 讓問題在開發環境（每次重啟、只跑一晚）完全看不出來。

## 修正

```diff
diff --git a/src/main/java/com/minicob/context/BusinessDateContext.java b/src/main/java/com/minicob/context/BusinessDateContext.java
index bd2724c..1cc2210 100644
--- a/src/main/java/com/minicob/context/BusinessDateContext.java
+++ b/src/main/java/com/minicob/context/BusinessDateContext.java
@@ -5,11 +5,11 @@ import java.time.LocalDate;
 /**
  * Thread-bound business dates, in the spirit of Fineract's {@code ThreadLocalContextUtil}.
  * Whoever starts a unit of work (an HTTP request, a COB run) is responsible for setting and
- * clearing it.
+ * clearing it. Pooled COB worker threads receive it through {@link CobTaskDecorator}.
  */
 public final class BusinessDateContext {
 
-    private static final ThreadLocal<BusinessDates> CURRENT = new InheritableThreadLocal<>();
+    private static final ThreadLocal<BusinessDates> CURRENT = new ThreadLocal<>();
 
     private BusinessDateContext() {
     }
diff --git a/src/main/java/com/minicob/context/CobTaskDecorator.java b/src/main/java/com/minicob/context/CobTaskDecorator.java
index 22458f4..df42a02 100644
--- a/src/main/java/com/minicob/context/CobTaskDecorator.java
+++ b/src/main/java/com/minicob/context/CobTaskDecorator.java
@@ -5,19 +5,24 @@ import org.slf4j.MDC;
 import org.springframework.core.task.TaskDecorator;
 
 /**
- * Carries the submitting thread's logging context over to pooled COB worker threads.
+ * Carries the submitting thread's context over to pooled COB worker threads.
  */
 public class CobTaskDecorator implements TaskDecorator {
 
     @Override
     public Runnable decorate(Runnable runnable) {
+        // Captured on the submitting thread. A pooled worker thread may still carry a previous run's state.
+        BusinessDates dates = BusinessDateContext.getOrNull();
         Map<String, String> mdc = MDC.getCopyOfContextMap();
         return () -> {
+            BusinessDates previousDates = BusinessDateContext.getOrNull();
             Map<String, String> previousMdc = MDC.getCopyOfContextMap();
+            BusinessDateContext.restore(dates);
             setMdc(mdc);
             try {
                 runnable.run();
             } finally {
+                BusinessDateContext.restore(previousDates);
                 setMdc(previousMdc);
             }
         };
```

- 改回一般的 `ThreadLocal`，不再依賴執行緒建立時機這種偶然的繼承行為。
- `TaskDecorator` 在**提交工作的執行緒**上擷取當下的營業日，在 worker 執行緒上設定，執行完 `finally` 還原，不讓狀態殘留在池化執行緒上。

另一種做法（Fineract 的做法）：worker step 開始時，從 job parameter 或 job execution context 讀取日期，在 worker 執行緒上重新設定 context，結束時清掉。兩者的共同原則是：**池化執行緒上的 context，每個工作單位都要明確設定、明確清除**。

## 怎麼找到它

1. 線索是「重啟後第一晚正常，之後就錯」。重啟會重置的東西就那幾種：快取、執行緒池、static 狀態。
2. 在 processor 印出 `Thread.currentThread().getName()` 和 `BusinessDateContext.getCobDate()`。第二晚 `cob-worker-1` 印出的是前一天的日期，而 `runCob` 的呼叫端是正確的。
3. 檢查 context 怎麼進入 worker：decorator 只處理 MDC；`BusinessDateContext` 用的是 `InheritableThreadLocal`。查它的語意，就會知道它只在執行緒建立時複製一次。

## 面試時可以怎麼講

> thread-local context 遇到執行緒池時要特別小心：池化執行緒不會自動拿到呼叫端的 context，用完沒清還會留給下一個工作。`InheritableThreadLocal` 只在執行緒建立時複製一次，對池化執行緒來說等於是「第一次那個值永遠留著」。我們的 COB 就是這樣，重啟後第一晚正常，第二晚開始日期停住。修法是用 `TaskDecorator` 在提交時擷取、在 worker 上設定、在 `finally` 還原。

可以準備的追問：

- **`@Async`、`CompletableFuture`、parallel stream 也有同樣問題嗎？** 有。`@Async` 可以設定 `TaskDecorator`；`CompletableFuture.supplyAsync` 預設用 ForkJoinPool common pool，要自己傳 executor 並包裝；Micrometer 的 context-propagation 函式庫可以統一處理 MDC、tracing 和自訂 context。
- **Spring Security 的 `SecurityContext` 也一樣嗎？** 一樣，要用 `DelegatingSecurityContextExecutor` 或 `MODE_INHERITABLETHREADLOCAL`，而後者也有同樣的池化陷阱。
- **virtual threads 呢？** 每個工作一條新的 virtual thread，沒有池化，殘留問題比較少；但大量 thread-local 會佔記憶體。Java 25 正式化的 `ScopedValue` 是更適合的替代方案：不可變、有明確的作用範圍。
- **為什麼 Fineract 在 worker 端重設 context，而不是靠 decorator？** Fineract 支援 remote partitioning，worker 在另一個 JVM，context 必須序列化到訊息裡（`OutputChannelInterceptor`），再由 worker 端還原（`InitialisationTasklet`）。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-core/src/main/java/org/apache/fineract/infrastructure/core/service/ThreadLocalContextUtil.java`：`businessDateContext` 是一般的 `ThreadLocal`，不是 inheritable。
- `fineract-cob/src/main/java/org/apache/fineract/cob/common/InitialisationTasklet.java`：worker 開始時，從 job execution context 讀取 `BUSINESS_DATE` 參數，在**目前的執行緒**上設定 COB_DATE 和 BUSINESS_DATE。
- `fineract-cob/src/main/java/org/apache/fineract/cob/common/ResetContextTasklet.java`：結束時清除 context。
- `fineract-provider/src/main/java/org/apache/fineract/infrastructure/springbatch/OutputChannelInterceptor.java`：把 `ThreadLocalContextUtil.getContext()` 放進送往 remote worker 的訊息。
