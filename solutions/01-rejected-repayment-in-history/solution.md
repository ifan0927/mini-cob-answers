# 01｜被拒絕的還款出現在還款明細裡：解答

## 根本原因

`@Transactional` 被放在 `RepaymentService.applyRepayment(...)` 上，可是它是由同一個 bean 的 `repay(...)` 以 `this.applyRepayment(...)` 呼叫的。`repay` 本身沒有 `@Transactional`。

Spring 的宣告式交易是靠**代理（proxy）**實作的。只有從 bean 外部經過代理進來的呼叫，才會被 `TransactionInterceptor` 攔截。`this.xxx()` 直接呼叫目標物件，完全不經過代理，所以 `applyRepayment` 實際上**沒有任何交易**。

沒有外層交易時，每個 repository 方法都會用 `SimpleJpaRepository` 自己的 `@Transactional` 各開一個短交易，並且**立即提交**：

1. `repaymentRepository.save(Repayment.received(...))`：已提交。
2. `loan.applyRepayment(amount)` 發現超額，丟出 `RepaymentExceedsOutstandingException`，API 回 422。
3. 第 1 步的還款列已經在資料庫裡，沒有東西會把它 rollback。

一般還款看起來也「正常」，因為每一步都各自成功。但它其實是非原子的：只要中途失敗，就會留下半套資料。

## 修正

```diff
diff --git a/src/main/java/com/minicob/repayment/RepaymentService.java b/src/main/java/com/minicob/repayment/RepaymentService.java
index 14be58a..40defa4 100644
--- a/src/main/java/com/minicob/repayment/RepaymentService.java
+++ b/src/main/java/com/minicob/repayment/RepaymentService.java
@@ -34,7 +34,11 @@ public class RepaymentService {
     /**
      * Applies a repayment exactly once per idempotency key. A retried request with the same key and
      * payload gets the original result back.
+     * <p>
+     * The transaction starts here. {@code applyRepayment} is called on {@code this}, which bypasses the
+     * transactional proxy, so the boundary has to be on this public entry point.
      */
+    @Transactional
     public RepaymentResult repay(Long loanId, String idempotencyKey, BigDecimal amount) {
         Optional<Repayment> previous = repaymentRepository.findByIdempotencyKey(idempotencyKey);
         if (previous.isPresent()) {
@@ -49,8 +53,7 @@ public class RepaymentService {
         return applyRepayment(loanId, idempotencyKey, amount);
     }
 
-    @Transactional
-    public RepaymentResult applyRepayment(Long loanId, String idempotencyKey, BigDecimal amount) {
+    RepaymentResult applyRepayment(Long loanId, String idempotencyKey, BigDecimal amount) {
         Loan loan = loanRepository.findWithInstallmentsById(loanId).orElseThrow(() -> new LoanNotFoundException(loanId));
         LocalDate businessDate = BusinessDateContext.getBusinessDate();
 
```

交易邊界放回對外的公開入口 `repay`。它包含冪等檢查、鎖檢查和入帳，全部在同一個交易裡完成。

## 怎麼找到它

1. 症狀是「失敗了卻有資料留下」，第一個要懷疑的就是交易邊界。
2. 打開 `logging.level.org.springframework.orm.jpa.JpaTransactionManager=DEBUG` 再重現一次。會看到 `Creating new transaction with name [org.springframework.data.jpa.repository.support.SimpleJpaRepository.save]`，卻**沒有**任何 `RepaymentService.*` 的交易。
3. 或在 `applyRepayment` 設中斷點，評估 `TransactionSynchronizationManager.isActualTransactionActive()`，結果是 `false`。
4. 回頭看呼叫路徑：`repay` → `this.applyRepayment`，就是自我呼叫（self-invocation）。

## 面試時可以怎麼講

> Spring 的 `@Transactional` 是 AOP 代理實作的，攔截點在代理上。同一個類別內部用 `this` 呼叫會繞過代理，所以註解形同不存在。我遇過的情境是還款服務：註解放在被內部呼叫的方法上，外層入口沒有交易，結果每個 repository 呼叫各自提交，業務驗證失敗時資料已經寫進去了。修法是把交易邊界放在對外入口；如果真的需要不同的交易屬性，就拆到另一個 bean，或用 `TransactionTemplate` 明確控制。

可以準備的追問：

- **還有哪些情況 `@Transactional` 不會生效？** `private` 方法。Spring 6 之後，class-based（CGLIB）代理也支援 protected 和 package-private，但 `private` 和 `final` 仍然無法攔截。另外還有物件不是 Spring bean（自己 `new` 出來的）、例外在方法內被吞掉、以及在 `@PostConstruct` 裡呼叫（代理可能還沒套上）。
- **JDK 動態代理和 CGLIB 有什麼差別？** Spring Boot 預設 `proxyTargetClass=true`，用 CGLIB 子類別。JDK 代理只能代理介面方法。
- **一定要用代理嗎？** 可以改用 AspectJ 編譯期或載入期織入（`mode = ASPECTJ`），自我呼叫也會生效，但建置比較複雜，團隊很少用。
- **只讀方法為什麼也建議加 `readOnly = true`？** Hibernate 會跳過 dirty checking 和 flush。有些 DataSource 或路由也會因此導向唯讀副本。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-core/src/main/java/org/apache/fineract/commands/service/SynchronousCommandProcessingService.java`：`executeCommandInTransaction(...)`。Fineract 的寫入都經過 command 處理管線，在**入口**統一包交易，handler 內部的方法不各自宣告交易邊界。
- `fineract-provider/src/main/java/org/apache/fineract/infrastructure/jobs/filter/LoanCOBApiFilter.java`：貸款被 COB 鎖住時拒絕寫入。對應本專案還款前的 `isLocked` 檢查。
