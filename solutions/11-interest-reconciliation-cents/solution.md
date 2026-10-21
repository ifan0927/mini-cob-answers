# 11｜美元貸款的每日利息和對帳試算表差幾分錢：解答

## 根本原因

learner 版本的 `InterestCalculator.dailyInterest`：

```java
BigDecimal dailyRate = annualRate.divide(DAYS_IN_YEAR, RoundingMode.HALF_UP);
return base.multiply(dailyRate).setScale(scale, RoundingMode.HALF_UP);
```

`BigDecimal.divide(BigDecimal divisor, RoundingMode mode)` 的結果 **scale 等於被除數的 scale**。年利率存成 `numeric(9,6)`，scale 是 6，所以：

- 0.030000 / 365 = 0.0000821917…，四捨五入到 6 位是 **0.000082**，相對誤差約 0.2%
- 250,000.00 × 0.000082 = 20.50，正確值是 20.547945… → **20.55**
- 1,000,000.00 × 0.050000 / 365：日利率被捨入成 0.000137，算出 137.00，正確值是 136.99

誤差最大可達 0.5×10⁻⁶ × 本金：本金 25 萬時每天最多約 0.125 美元，而且方向隨利率變化。台幣貸款看起來「大多對得上」，是因為四捨五入到整數，把小誤差蓋掉了。至於 7.3%、10.95% 這類利率，除以 365 剛好能在 6 位內除盡，完全沒有誤差。

## 修正

```diff
diff --git a/src/main/java/com/minicob/loan/InterestCalculator.java b/src/main/java/com/minicob/loan/InterestCalculator.java
index 1bda68a..5834372 100644
--- a/src/main/java/com/minicob/loan/InterestCalculator.java
+++ b/src/main/java/com/minicob/loan/InterestCalculator.java
@@ -1,6 +1,7 @@
 package com.minicob.loan;
 
 import java.math.BigDecimal;
+import java.math.MathContext;
 import java.math.RoundingMode;
 import org.springframework.stereotype.Component;
 
@@ -18,7 +19,8 @@ public class InterestCalculator {
      */
     public BigDecimal dailyInterest(BigDecimal base, BigDecimal annualRate, String currency) {
         int scale = Currencies.scaleOf(currency);
-        BigDecimal dailyRate = annualRate.divide(DAYS_IN_YEAR, RoundingMode.HALF_UP);
-        return base.multiply(dailyRate).setScale(scale, RoundingMode.HALF_UP);
+        // Divide last, with a MathContext: dividing the rate first would round it to the rate's own scale.
+        BigDecimal exact = base.multiply(annualRate).divide(DAYS_IN_YEAR, MathContext.DECIMAL64);
+        return exact.setScale(scale, RoundingMode.HALF_UP);
     }
 }
```

- **先乘後除**：避免先捨入中間值。
- 除法用 **`MathContext.DECIMAL64`**（16 位有效數字），或明確指定足夠大的 scale。
- **最後只捨入一次**，捨入到幣別的最小單位。

## 怎麼找到它

1. 「差幾分錢、方向不固定、隨利率變化」是捨入或精度問題，不是公式錯誤。
2. 用失敗的案例在 debugger 或 jshell 逐步算：`new BigDecimal("0.030000").divide(BigDecimal.valueOf(365), RoundingMode.HALF_UP)` 得到 `0.000082`。
3. 查 `divide` 各個 overload 的 javadoc，確認結果 scale 的規則。

## 面試時可以怎麼講

> 金額計算一律用 `BigDecimal`，而且要清楚每一步的 scale。`divide(divisor, RoundingMode)` 會沿用被除數的 scale，利率只有 6 位小數時，除以 365 就會被捨入掉一大截。我們的修正是先乘後除、除法用 `MathContext`、最後才依幣別捨入一次。這類問題用對帳試算表的數字寫單元測試就能釘住。

可以準備的追問：

- **`divide` 的四個 overload？** `divide(d)` 遇到除不盡會丟 `ArithmeticException`；`divide(d, roundingMode)` 用 `this.scale()`；`divide(d, scale, roundingMode)` 指定 scale；`divide(d, mathContext)` 指定有效位數。
- **`equals` 和 `compareTo` 的差別？** `new BigDecimal("2.0").equals(new BigDecimal("2.00"))` 是 `false`，因為 scale 不同。比較金額要用 `compareTo`（測試裡用 `isEqualByComparingTo` 也是這個原因）。
- **`HALF_UP` 和 `HALF_EVEN`？** `HALF_EVEN`（銀行家捨入）在大量加總時沒有系統性偏差。用哪一種要依產品或法規決定，並且全系統一致。
- **day count convention？** 本專案用 Actual/365 Fixed。市場上還有 Actual/360、30/360、Actual/Actual 等，換算方式不同。這屬於產品參數，不應該寫死。
- **`new BigDecimal(0.1)` 有什麼問題？** 它會帶入 double 的二進位誤差。要用 `BigDecimal.valueOf(0.1)` 或字串建構子。

## 對應的 Fineract 程式碼（commit b94b2dd）

- `fineract-core/src/main/java/org/apache/fineract/organisation/monetary/domain/Money.java`：所有金額運算都帶 `MathContext`（欄位 `mc`）。
- `fineract-core/src/main/java/org/apache/fineract/organisation/monetary/domain/MoneyHelper.java`：`getMathContext()`、`getRoundingMode()`。精度和捨入模式集中設定、全系統一致。
