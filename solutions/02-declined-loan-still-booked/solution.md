# 02｜已婉拒的貸款申請仍然入帳：解答

## 根本原因

`ExposureLimitExceededException` 繼承 `Exception`，是 **checked exception**。`LoanService.createLoan` 只標了 `@Transactional`。

Spring 的預設 rollback 規則沿襲 EJB 的慣例：**只有 `RuntimeException` 和 `Error` 會觸發 rollback**。checked exception 往外丟時，交易會照常**提交**。

`createLoan` 的流程是先 `saveAndFlush(loan)`，再用 SQL 加總曝險（包含剛寫入的這筆）。超過上限就丟例外，此時貸款和攤還表已經 flush 到資料庫。例外是 checked，交易提交，貸款就留下來了。帳號是空的，因為配號在丟例外之後才會執行。

## 修正

```diff
diff --git a/src/main/java/com/minicob/loan/LoanService.java b/src/main/java/com/minicob/loan/LoanService.java
index 176f093..5139100 100644
--- a/src/main/java/com/minicob/loan/LoanService.java
+++ b/src/main/java/com/minicob/loan/LoanService.java
@@ -24,7 +24,8 @@ public class LoanService {
                                     BigDecimal annualInterestRate, int termMonths) {
     }
 
-    @Transactional
+    // ExposureLimitExceededException is checked, and Spring rolls back only on unchecked exceptions by default.
+    @Transactional(rollbackFor = ExposureLimitExceededException.class)
     public Loan createLoan(CreateLoanCommand command) throws ExposureLimitExceededException {
         Loan loan = Loan.disburse(command.customerId(), command.currency(), command.principal(),
                 command.annualInterestRate(), command.termMonths(), BusinessDateContext.getBusinessDate());
```

## 怎麼找到它

1. 和第 01 題一樣，「API 失敗但資料留下」要先檢查交易。這次 `createLoan` 確實有交易，那就要看它為什麼沒有 rollback。
2. 打開 `JpaTransactionManager` 的 DEBUG log，會看到例外之後出現 `Committing JPA transaction on EntityManager`。
3. 看例外的型別：`extends Exception`。查 `@Transactional` 的 javadoc（`rollbackFor` 一節）或 `DefaultTransactionAttribute.rollbackOn` 就能確認預設規則。

## 面試時可以怎麼講

> Spring 預設只在 unchecked exception 時 rollback。checked exception 被視為「可預期的業務結果」，交易會提交。我遇過的案例是額度檢查：先寫入再加總，超額時丟 checked 例外，結果被拒絕的貸款還是入帳了。處理方式有三種：在註解上加 `rollbackFor`；讓業務例外改繼承 `RuntimeException`，例如 Fineract 的所有 platform exception 都是 unchecked；或在 catch 區塊呼叫 `setRollbackOnly()`。團隊層級我偏好統一規則，不要每個方法自己記。

可以準備的追問：

- **Spring 6.2 起可以全域改預設嗎？** 可以，`@EnableTransactionManagement(rollbackOn = RollbackOn.ALL_EXCEPTIONS)`。但要注意它會改變所有既有方法的行為。
- **`noRollbackFor` 的用途？** 某些 runtime 例外只是「通知」性質，不應該讓交易失敗。
- **例外在交易內被 catch 掉會怎樣？** 交易照常提交。但如果內層 `REQUIRED` 方法已經把交易標成 rollback-only，外層提交時會丟 `UnexpectedRollbackException`。
- **為什麼要先寫再檢查？** 用資料庫加總包含新貸款的曝險，最簡單也最一致。前提是整個流程在同一個交易裡，而且失敗時要確實 rollback。也可以先檢查再寫入，但要注意並發時兩筆申請同時通過檢查的問題，需要鎖客戶列或設計序列化的機制。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-core/src/main/java/org/apache/fineract/infrastructure/core/exception/AbstractPlatformException.java`：`extends RuntimeException`。Fineract 的業務規則例外（如 `AbstractPlatformDomainRuleException`）全部是 unchecked，所以預設就會 rollback，不需要在每個方法上寫 `rollbackFor`。
- `fineract-core/src/main/java/org/apache/fineract/commands/service/SynchronousCommandProcessingService.java`：handler 丟出的例外一路往上丟，讓入口的交易 rollback。
