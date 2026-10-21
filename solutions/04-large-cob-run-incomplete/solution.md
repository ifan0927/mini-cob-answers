# 04｜貸款量一大，COB 就漏處理或重複處理：解答

## 根本原因

`cobLoanReader` 的 bean 定義少了 `@StepScope`，於是成為 **singleton**。所有 partition 的 worker step 共用同一個 `LoanItemReader` 實例。

`LoanItemReader` 是有狀態的，它的 `remaining` 佇列就是游標：

- 每個 partition 開始時，`open(executionContext)` 都會把 `remaining` 換成**自己那個 partition** 的 id。最後一個執行 `open` 的 partition 會蓋掉其他 partition 的游標，被蓋掉的 partition 剩下的貸款就不會被讀到。
- 多條 worker 執行緒同時對同一個 `ArrayDeque` 呼叫 `poll()`。`ArrayDeque` 不是執行緒安全的，結果可能重複拿到同一筆、跳過某些筆，或讓佇列的內部狀態錯亂。

為什麼只有量大時才出事：partition 大小是 50。只要貸款少於 50 筆，就只有一個 partition、只有一條 worker 執行緒，共用的 reader 不會被同時使用。QA 用十幾筆資料當然重現不出來。

沒被讀到的貸款雖然被上了鎖，但沒有被處理。step 結束時，`afterStep` 會把它們的鎖釋放掉，所以表面上看不到殘留的鎖，只看到「沒有關帳」。

## 修正

```diff
diff --git a/src/main/java/com/minicob/cob/CobJobConfiguration.java b/src/main/java/com/minicob/cob/CobJobConfiguration.java
index edf77ce..7febe4c 100644
--- a/src/main/java/com/minicob/cob/CobJobConfiguration.java
+++ b/src/main/java/com/minicob/cob/CobJobConfiguration.java
@@ -87,7 +87,9 @@ public class CobJobConfiguration {
                 .build();
     }
 
+    // One reader per partition: the reader keeps a cursor and partitions run concurrently.
     @Bean
+    @StepScope
     public LoanItemReader cobLoanReader(CobLoanRepository repository) {
         return new LoanItemReader(repository);
     }
```

`@StepScope` 會讓 Spring 注入一個代理。每個 `StepExecution`（也就是每個 partition）第一次使用時，才建立**屬於它自己的** reader 實例，partition 結束時一起銷毀。

## 怎麼找到它

1. 「資料量小正常、量大出錯、每次結果不同」是典型的並發特徵。先找出量大時才出現的差異：partition 數量和執行緒數量。
2. 看 Spring Batch 的 metadata：`BATCH_STEP_EXECUTION` 每個 `loanCobWorkerStep:partitionN` 的 `READ_COUNT`、`WRITE_COUNT`。加總和貸款數對不上，有的 partition 讀了 0 筆，有的讀超過 50 筆。
3. 在 reader 的 `open` 和 `read` 加 log，印出 `Thread.currentThread().getName()` 和 `System.identityHashCode(this)`。會發現所有 worker 執行緒用的是同一個 reader 實例。
4. 檢查所有在 worker step 中使用、而且**有欄位會變動**的 bean，確認它的 scope。

## 面試時可以怎麼講

> Spring 預設是 singleton，所以 bean 裡不能放「每次執行」的可變狀態。在 Spring Batch 的分區情境中最容易踩到，因為同一個 Step 物件會被多條執行緒同時拿去跑不同的 partition。reader 和 writer 這種有游標的元件要 `@StepScope`，讓每個 StepExecution 拿到自己的實例。我們的 COB 少了這個註解，資料一多、partition 一變多，就開始漏處理和重複處理。

可以準備的追問：

- **`@StepScope` 的其他作用？** late binding，可以用 `#{stepExecutionContext['...']}`、`#{jobParameters['...']}` 注入參數。這也是 partitioner 在這裡是 step-scoped 的原因。
- **如果 reader 一定要共用（multi-threaded step，而不是 partition）？** 要用執行緒安全的 reader，或用 `SynchronizedItemStreamReader` 包起來。但這樣就失去 restart 時的狀態保存。
- **processor 和 writer 為什麼可以是 singleton？** 它們沒有可變欄位，所有狀態都在方法參數和區域變數裡。這是 singleton 安全的前提。
- **怎麼預防？** code review 時檢查 batch 元件的欄位是否為 `final` 而且不可變；寫一個多 partition 的整合測試，就像本題的 400 筆。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/LoanCOBWorkerConfiguration.java`：`cobWorkerItemReader()`、`cobWorkerItemProcessor()`、`cobWorkerItemWriter()` 都是 `@Bean @StepScope`。
- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/AbstractLoanItemReader.java`、`LoanItemReader.java`：reader 持有該 partition 剩餘的 loan id，是有狀態的元件。
- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/LoanCOBPartitioner.java`：依 partition size 切分。
