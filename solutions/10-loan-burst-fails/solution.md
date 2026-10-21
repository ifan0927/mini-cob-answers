# 10｜申請量瞬間湧入時，服務卡住幾秒後大量失敗：解答

## 根本原因

`LoanService.createLoan` 有交易（外層），它在最後呼叫 `AccountNumberGenerator.nextLoanAccountNumber()` 配發帳號。learner 版本的配號方法是 `REQUIRES_NEW`：先暫停外層交易，再**另外向連線池借一條連線**開新交易。

每筆申請在配號的瞬間需要 **2 條連線**：外層交易的那條沒有歸還，又要再借一條。

連線池只有 4 條，同時來了 8 筆申請：

1. 前 4 筆各自開始外層交易，借走 4 條連線，池子空了。
2. 這 4 筆做完寫入，走到配號，各自要借第 5 條連線，全部在 `HikariPool.getConnection()` 等待。
3. 沒有任何人會歸還連線，因為每個人都在等別人歸還。這是不涉及資料庫鎖的**連線池飢餓死結**。
4. 2 秒後（`connection-timeout`）全部逾時，丟出 `SQLTransientConnectionException`，Spring 包成 `CannotCreateTransactionException`，API 回 500。另外 4 筆在等外層連線，也大多跟著逾時。

單筆申請永遠不會出事，因為 1 筆只需要 2 條連線。這也是為什麼「流量一降就恢復正常」。

## 修正

```diff
diff --git a/src/main/java/com/minicob/loan/AccountNumberGenerator.java b/src/main/java/com/minicob/loan/AccountNumberGenerator.java
index 13f4e57..9bad550 100644
--- a/src/main/java/com/minicob/loan/AccountNumberGenerator.java
+++ b/src/main/java/com/minicob/loan/AccountNumberGenerator.java
@@ -1,7 +1,6 @@
 package com.minicob.loan;
 
 import org.springframework.stereotype.Service;
-import org.springframework.transaction.annotation.Propagation;
 import org.springframework.transaction.annotation.Transactional;
 
 /**
@@ -18,9 +17,8 @@ public class AccountNumberGenerator {
         this.repository = repository;
     }
 
-    // Allocate in a short transaction of its own so the counter row lock is released
-    // immediately instead of being held until the whole loan booking commits.
-    @Transactional(propagation = Propagation.REQUIRES_NEW)
+    // Joins the caller's transaction. REQUIRES_NEW here would hold two pooled connections per booking.
+    @Transactional
     public String nextLoanAccountNumber() {
         NumberSequence sequence = repository.findForUpdate(LOAN_ACCOUNT_SEQUENCE)
                 .orElseThrow(() -> new IllegalStateException("Sequence " + LOAN_ACCOUNT_SEQUENCE + " is missing"));
```

配號加入外層交易。代價是計數列的列鎖（`SELECT ... FOR UPDATE`）會持有到整筆申請提交。配號已經放在流程的最後一步，持有時間很短，同時申請的請求會在這裡依序排隊，但不會死結。

其他做法：

| 做法 | 優點 | 代價 |
|---|---|---|
| `REQUIRED`（本修正） | 不跳號，不需要額外連線 | 計數列成為序列化點 |
| 資料庫 sequence（`nextval`） | 不需要鎖、不需要額外交易 | 交易 rollback 時會跳號（法規要求連號時不適用） |
| 由主鍵推導帳號（Fineract 做法） | 不需要額外資源 | 帳號格式受主鍵限制 |
| 保留 `REQUIRES_NEW` 但放大連線池 | 程式不用改 | 池大小要 ≥ Tn × (Cm − 1) + 1（HikariCP 的公式：Tn 是最大並發執行緒數，Cm 是單一執行緒同時需要的連線數），而且只是延後問題 |

## 怎麼找到它

1. 「卡住剛好 2 秒，然後失敗」：2 秒就是 `connection-timeout`。錯誤訊息 `Connection is not available, request timed out after 2000ms` 直接指向連線池。
2. DBA 說資料庫很閒，表示瓶頸在應用端的連線池。看 Hikari 的 metrics（`hikaricp.connections.active=4`、`pending>0`），或在卡住時做 thread dump：多條執行緒停在 `HikariPool.getConnection`，而它們的堆疊上層**已經在一個交易裡**（`TransactionInterceptor` → ... → `JpaTransactionManager.doBegin`）。
3. 往上追是誰在交易裡又要新連線：`REQUIRES_NEW`。
4. `JpaTransactionManager` DEBUG log：`Suspending current transaction, creating new transaction with name [...nextLoanAccountNumber]`。

## 面試時可以怎麼講

> `REQUIRES_NEW` 會在持有一條連線的情況下再借一條。並發數大於等於連線池大小時，所有執行緒都拿著一條、等著第二條，就形成和資料庫無關的連線池死結，症狀是剛好卡住 connection-timeout 那麼久，然後大量失敗。我們的配號原本用 `REQUIRES_NEW`，想縮短計數列的鎖定時間，結果活動一來就爆了。修法是改回加入外層交易，並把配號放在最後；也可以改用資料庫 sequence。評估連線池時要用 HikariCP 的公式，把巢狀交易算進去。

可以準備的追問：

- **怎麼在測試中抓到這類問題？** 用小連線池加並發測試，就像本題。也可以開 Hikari 的 `leakDetectionThreshold` 抓長時間持有的連線。
- **第 03 題的 `REQUIRES_NEW` 為什麼可以？** 一樣需要兩條連線，所以 COB worker 數和連線池大小要一起設計：worker 數 × 2 + manager + API 流量。它只在出錯時才觸發，但出錯時往往是大量出錯，仍然要算進去。
- **連線池是不是越大越好？** 不是。資料庫能有效並行的連線數有限（約為 CPU 核心數 × 2 加上磁碟數這個量級），太大的池子反而增加 context switch 和鎖競爭。正確做法是消除不必要的巢狀連線需求。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-provider/src/main/java/org/apache/fineract/portfolio/account/service/AccountNumberGenerator.java`：`generate(Loan loan, ...)` 以 `loan.getId()` 組出帳號，在同一個交易內完成。沒有計數列，也不需要額外的交易或連線。
- `fineract-provider/src/main/java/org/apache/fineract/infrastructure/core/config/JdbcTransactionConfig.java`：Fineract 也有 `REQUIRES_NEW` 的 `TransactionTemplate`，只用在 COB 上鎖和錯誤記錄這類必要的地方。
