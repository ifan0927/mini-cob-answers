# 07｜同一營業日重跑 COB，利息被計了兩次：解答

## 根本原因

COB 用 `CobLoanRepository.findIdsToClose(cobDate)` 決定要處理哪些貸款，查詢條件少了：

```
and (l.lastClosedBusinessDate is null or l.lastClosedBusinessDate < :cobDate)
```

`lastClosedBusinessDate` 是每筆貸款的處理進度標記（watermark）。少了這個條件，重跑同一天時會把**所有**未結清的貸款再處理一次。business step 本身不是冪等的（`accruedInterest += 當日利息`，並新增一筆 `INTEREST_ACCRUAL`），所以利息就被計了兩次。

為什麼 Spring Batch 沒有擋下來？`CobService` 每次啟動都帶一個隨機的 `runId` job parameter，所以每次都是新的 `JobInstance`。這是刻意的設計，為了允許「部分失敗後重跑」。代價是冪等性必須由業務邏輯自己保證。

## 修正

```diff
diff --git a/src/main/java/com/minicob/cob/CobLoanRepository.java b/src/main/java/com/minicob/cob/CobLoanRepository.java
index 928a952..c68245d 100644
--- a/src/main/java/com/minicob/cob/CobLoanRepository.java
+++ b/src/main/java/com/minicob/cob/CobLoanRepository.java
@@ -12,10 +12,12 @@ import org.springframework.data.repository.query.Param;
 /** Queries used by the COB job. */
 public interface CobLoanRepository extends Repository<Loan, Long> {
 
+    // Loans already closed for cobDate are left out, which makes re-running a date safe.
     @Query("""
             select l.id from Loan l
             where l.status <> com.minicob.loan.LoanStatus.CLOSED
               and l.disbursementDate <= :cobDate
+              and (l.lastClosedBusinessDate is null or l.lastClosedBusinessDate < :cobDate)
             order by l.id
             """)
     List<Long> findIdsToClose(@Param("cobDate") LocalDate cobDate);
```

建議再加一層防護（不在本題的 diff 內）：

- 對 `loan_transaction(loan_id, type, transaction_date)` 建唯一約束（只針對提列類型），讓資料庫成為最後一道防線。
- 或在 processor 檢查 `lastClosedBusinessDate >= cobDate` 時直接略過，並記一筆 warning。

## 怎麼找到它

1. 第二次執行時，`BATCH_STEP_EXECUTION` 的 `READ_COUNT` 不是 0。一個已經全部關帳的日期，重跑理應沒有東西可讀。
2. 往回追「要處理哪些貸款」是誰決定的：partitioner 呼叫 `findIdsToClose`。
3. 看查詢條件：有 `status` 和 `disbursementDate`，卻沒有用到處理進度。

## 面試時可以怎麼講

> 批次的冪等性要靠業務層的進度標記，不能只靠框架。我們每筆貸款都有 `lastClosedBusinessDate`，選取條件只挑還沒關到這一天的。Spring Batch 的 JobInstance 唯一性管的是「同一組參數不能重跑已完成的 job」，但我們需要部分失敗後重跑，所以每次都用新參數，冪等就得自己保證。我還會在資料庫加唯一約束當保險。

可以準備的追問：

- **Spring Batch 的 restart 和 rerun 有什麼不同？** restart 是用**同一組參數**重啟 FAILED 的 JobInstance，從失敗的 step 和 checkpoint（ExecutionContext）接續。rerun 是新的 JobInstance，從頭開始。COB 這種以每筆 watermark 為準的設計，兩種都可以安全使用。
- **如果中途停電？** 已提交的 chunk 中，貸款的 `lastClosedBusinessDate` 已經前進，重跑時會被略過；未提交的 chunk 會整個 rollback，重跑時再處理。前提是 watermark 和業務資料在**同一個交易**裡更新（本專案的 writer 做到了）。
- **catch-up（落後好幾天）怎麼辦？** 逐日處理，每天都以同樣的 watermark 規則推進。Fineract 有 COB catch-up 機制。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-provider/src/main/java/org/apache/fineract/cob/loan/RetrieveAllNonClosedIdServiceImpl.java`：`retrieveAllNonClosedLoansByLastClosedBusinessDateAndMinAndMaxLoanId(...)`、`retrieveLoanIdsBehindDate(...)`。以 `lastClosedBusinessDate` 篩選要處理的貸款。
- `fineract-loan/src/main/java/org/apache/fineract/portfolio/loanaccount/domain/LoanRepository.java`：`findAllLoansByLastClosedBusinessDate...` 系列查詢。
- `fineract-provider/src/main/java/org/apache/fineract/cob/service/CommonCOBCatchUpService.java`：落後多天時的 catch-up。
