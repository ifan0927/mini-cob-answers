# 06｜逾期報表越來越慢：解答

## 根本原因

報表用 `loanRepository.findByStatusOrderById(OVERDUE)` 取出貸款，再對每一筆讀取 `loan.getInstallments()`。

`installments` 是 `@OneToMany`，預設 LAZY，而這個查詢方法沒有指定要一併抓取攤還表。結果是典型的 **N+1**：

- 1 條 SQL 查出 N 筆逾期貸款
- 每筆貸款第一次存取 `installments` 時，再各發 1 條 SQL

20 筆逾期就是 1 + 20 條，再加上取營業日的 1 條，總共 22 條。一萬筆就是一萬多條。

報表方法有 `@Transactional(readOnly = true)`，所以 lazy loading 能「成功」，問題才會一直藏到量大才被看見。如果沒有交易（`open-in-view` 也關閉），反而會直接丟 `LazyInitializationException`。

## 修正

```diff
diff --git a/src/main/java/com/minicob/loan/LoanRepository.java b/src/main/java/com/minicob/loan/LoanRepository.java
index ea60cd7..50b4a16 100644
--- a/src/main/java/com/minicob/loan/LoanRepository.java
+++ b/src/main/java/com/minicob/loan/LoanRepository.java
@@ -23,5 +23,7 @@ public interface LoanRepository extends JpaRepository<Loan, Long> {
 
     List<Loan> findByCustomerIdOrderById(String customerId);
 
+    // The overdue report reads every loan's schedule: fetch it together with the loans.
+    @EntityGraph(attributePaths = "installments")
     List<Loan> findByStatusOrderById(LoanStatus status);
 }
```

`@EntityGraph(attributePaths = "installments")` 會讓 Spring Data 產生 `left join fetch`，一條 SQL 就取回貸款和攤還表。

## 怎麼找到它

1. 開 `logging.level.org.hibernate.SQL=DEBUG`，或用 `hibernate.generate_statistics=true` 加 `Statistics.getPrepareStatementCount()`，也可以用 datasource-proxy 或 p6spy。會看到一長串幾乎一樣的 `select ... from installment where loan_id=?`。
2. 對照程式：查詢沒有 fetch，mapping 時卻走訪了集合。
3. 用測試把 SQL 數量釘住（本題的測試做法），防止日後退化。

## 面試時可以怎麼講

> N+1 是查父物件時沒有一起抓子集合，之後逐筆 lazy load。最常見的解法是 fetch join 或 `@EntityGraph`；資料量大或需要分頁時，改用 `hibernate.default_batch_fetch_size`（或 `@BatchSize`），把 N 次查詢變成 N/size 次 `IN` 查詢；報表類需求我會直接做 DTO projection，只查需要的欄位。另外我會用 Hibernate statistics 寫測試，把 SQL 數量鎖住。

可以準備的追問：

- **fetch join 加分頁的陷阱？** Hibernate 會警告 `HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory`，等於把全部資料載入記憶體後才分頁。解法是先分頁查 id，再 fetch，或改用 batch fetching。
- **同時 fetch 兩個 `List` 集合？** 會丟 `MultipleBagFetchException`，而且會產生笛卡兒積。改用 `Set`、分兩次查詢，或用 batch fetching。
- **`FetchType.EAGER` 能解決嗎？** 不能，反而更糟。它對所有查詢都生效，而且透過 JPQL 查詢時通常還是逐筆去抓。
- **為什麼關掉 open-in-view？** 避免在 view 或序列化階段意外觸發 lazy loading，也避免連線被佔用到請求結束。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-provider/src/main/java/org/apache/fineract/portfolio/loanaccount/service/LoanReadPlatformServiceImpl.java`：Fineract 的讀取端大多用 `JdbcTemplate` 搭配自訂 SQL 和 `RowMapper`，直接組出 DTO，不經過 JPA 實體走訪關聯。這是迴避 N+1、讓報表 SQL 可控的一種架構選擇（讀寫分離的 CQRS 風格）。
- `fineract-loan/src/main/java/org/apache/fineract/portfolio/loanaccount/domain/LoanRepository.java`：寫入端的 JPA repository。
