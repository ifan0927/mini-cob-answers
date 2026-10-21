# mini-cob verification matrix

Run at 2026-10-21T12:36:03

```
PASS  delivered learner src == baseline + bug patches 
PASS  [round 1] (a) baseline: 14 test classes, all pass (24s) 
PASS  [round 1] (b) learner: non-exercise CobJobTest passes
PASS  [round 1] (b) learner: non-exercise LoanApiTest passes
PASS  [round 1] (b) learner: non-exercise RepaymentApiTest passes
PASS  [round 1] (b) learner: Ex01 fails for its own reason -> [repayment history after the API answered 422 to the only repayment attempt] Expecting empty but was: [{"repaymentId":1,"loanId":1,"amount":100001.0,"principalP...
PASS  [round 1] (b) learner: Ex02 fails for its own reason -> [loans on the books of customer C-EX02 after the declined application] Expecting actual: [4000000.00, 2000000.00] to contain exactly (and in same order):
PASS  [round 1] (b) learner: Ex03 fails for its own reason -> [account lock of the loan COB could not process] Expecting Optional to contain a value but it was empty. java.lang.AssertionError: [account lock of the loan COB...
PASS  [round 1] (b) learner: Ex04 fails for its own reason -> [loans not closed exactly once for 2026-04-16 (289 of 400)] Expecting empty but was: ["loan 61: closed=null interest=0.00 (expected 20) accrual entries=0", "loa...
PASS  [round 1] (b) learner: Ex05 fails for its own reason -> [last closed business date of the loan] expected: 2026-04-16 (java.time.LocalDate) but was: null org.opentest4j.AssertionFailedError:
PASS  [round 1] (b) learner: Ex06 fails for its own reason -> [SQL statements executed by one overdue report call with 20 overdue loans] Expecting actual: 22L to be less than or equal to:
PASS  [round 1] (b) learner: Ex07 fails for its own reason -> [interest accrued for one day on loan 433] expected: 20 but was: 40.00 org.opentest4j.AssertionFailedError:
PASS  [round 1] (b) learner: Ex08 fails for its own reason -> [repayments on healthy loans the morning after the aborted COB] Expecting empty but was: ["loan 423 -> HTTP 409", "loan 424 -> HTTP 409", "loan 425 -> HTTP 409"...
PASS  [round 1] (b) learner: Ex09 fails for its own reason -> [last closed date after night two] expected: 2026-04-16 (java.time.LocalDate) but was: 2026-04-15 (java.time.LocalDate) org.opentest4j.AssertionFailedError:
PASS  [round 1] (b) learner: Ex10 fails for its own reason -> [loan applications that failed out of 8] Expecting empty but was: ["HTTP 500: {"type":"about:blank","title":"Internal Server Error","status":500,"detail":"org.s...
PASS  [round 1] (b) learner: Ex11 fails for its own reason -> [one day of interest on 250,000.00 USD at 3%] expected: 20.55 but was: 20.50 org.opentest4j.AssertionFailedError:
PASS  [round 1] (b) learner, run alone (-Dtest=Ex01RejectedRepaymentTest): fails for its own reason -> [repayment history after the API answered 422 to the only repayment attempt] Expecting empty but was: [{"repay...
PASS  [round 1] (b) learner, run alone (-Dtest=Ex02DeclinedLoanApplicationTest): fails for its own reason -> [loans on the books of customer C-EX02 after the declined application] Expecting actual: [4000000.00, 2000000....
PASS  [round 1] (b) learner, run alone (-Dtest=Ex03CobFailureDiagnosticsTest): fails for its own reason -> [account lock of the loan COB could not process] Expecting Optional to contain a value but it was empty. java....
PASS  [round 1] (b) learner, run alone (-Dtest=Ex04LargeCobRunTest): fails for its own reason -> [loans not closed exactly once for 2026-04-16 (289 of 400)] Expecting empty but was: ["loan 3: closed=null int...
PASS  [round 1] (b) learner, run alone (-Dtest=Ex05TellerDuringCobTest): fails for its own reason -> [last closed business date of the loan] expected: 2026-04-16 (java.time.LocalDate) but was: null org.opentest4...
PASS  [round 1] (b) learner, run alone (-Dtest=Ex06OverdueReportTest): fails for its own reason -> [SQL statements executed by one overdue report call with 20 overdue loans] Expecting actual: 22L to be less th...
PASS  [round 1] (b) learner, run alone (-Dtest=Ex07CobRerunTest): fails for its own reason -> [interest accrued for one day on loan 1] expected: 20 but was: 40.00 org.opentest4j.AssertionFailedError:
PASS  [round 1] (b) learner, run alone (-Dtest=Ex08AbortedCobTest): fails for its own reason -> [repayments on healthy loans the morning after the aborted COB] Expecting empty but was: ["loan 2 -> HTTP 409"...
PASS  [round 1] (b) learner, run alone (-Dtest=Ex09ConsecutiveBusinessDaysTest): fails for its own reason -> [last closed date after night two] expected: 2026-04-16 (java.time.LocalDate) but was: 2026-04-15 (java.time.L...
PASS  [round 1] (b) learner, run alone (-Dtest=Ex10LoanApplicationBurstTest): fails for its own reason -> [loan applications that failed out of 8] Expecting empty but was: ["HTTP 500: {"type":"about:blank","title":"I...
PASS  [round 1] (b) learner, run alone (-Dtest=Ex11InterestReconciliationTest): fails for its own reason -> [one day of interest on 250,000.00 USD at 3%] expected: 20.55 but was: 20.50 org.opentest4j.AssertionFailedErr...
PASS  [round 1] (c) fix only 01: Ex01 passes (22s)
PASS  [round 1] (c) fix only 01: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 01: non-exercise tests pass
PASS  [round 1] (c) fix only 02: Ex02 passes (24s)
PASS  [round 1] (c) fix only 02: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 02: non-exercise tests pass
PASS  [round 1] (c) fix only 03: Ex03 passes (23s)
PASS  [round 1] (c) fix only 03: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 03: non-exercise tests pass
PASS  [round 1] (c) fix only 04: Ex04 passes (23s)
PASS  [round 1] (c) fix only 04: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 04: non-exercise tests pass
PASS  [round 1] (c) fix only 05: Ex05 passes (23s)
PASS  [round 1] (c) fix only 05: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 05: non-exercise tests pass
PASS  [round 1] (c) fix only 06: Ex06 passes (24s)
PASS  [round 1] (c) fix only 06: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 06: non-exercise tests pass
PASS  [round 1] (c) fix only 07: Ex07 passes (24s)
PASS  [round 1] (c) fix only 07: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 07: non-exercise tests pass
PASS  [round 1] (c) fix only 08: Ex08 passes (23s)
PASS  [round 1] (c) fix only 08: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 08: non-exercise tests pass
PASS  [round 1] (c) fix only 09: Ex09 passes (23s)
PASS  [round 1] (c) fix only 09: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 09: non-exercise tests pass
PASS  [round 1] (c) fix only 10: Ex10 passes (21s)
PASS  [round 1] (c) fix only 10: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 10: non-exercise tests pass
PASS  [round 1] (c) fix only 11: Ex11 passes (25s)
PASS  [round 1] (c) fix only 11: the other 10 exercises still fail (10 failing)
PASS  [round 1] (c) fix only 11: non-exercise tests pass
PASS  [round 2] (a) baseline: 14 test classes, all pass (19s) 
PASS  [round 2] (b) learner: non-exercise CobJobTest passes
PASS  [round 2] (b) learner: non-exercise LoanApiTest passes
PASS  [round 2] (b) learner: non-exercise RepaymentApiTest passes
PASS  [round 2] (b) learner: Ex01 fails for its own reason -> [repayment history after the API answered 422 to the only repayment attempt] Expecting empty but was: [{"repaymentId":1,"loanId":1,"amount":100001.0,"principalP...
PASS  [round 2] (b) learner: Ex02 fails for its own reason -> [loans on the books of customer C-EX02 after the declined application] Expecting actual: [4000000.00, 2000000.00] to contain exactly (and in same order):
PASS  [round 2] (b) learner: Ex03 fails for its own reason -> [account lock of the loan COB could not process] Expecting Optional to contain a value but it was empty. java.lang.AssertionError: [account lock of the loan COB...
PASS  [round 2] (b) learner: Ex04 fails for its own reason -> [loans not closed exactly once for 2026-04-16 (289 of 400)] Expecting empty but was: ["loan 2: closed=null interest=0.00 (expected 20) accrual entries=0", "loan...
PASS  [round 2] (b) learner: Ex05 fails for its own reason -> [last closed business date of the loan] expected: 2026-04-16 (java.time.LocalDate) but was: null org.opentest4j.AssertionFailedError:
PASS  [round 2] (b) learner: Ex06 fails for its own reason -> [SQL statements executed by one overdue report call with 20 overdue loans] Expecting actual: 22L to be less than or equal to:
PASS  [round 2] (b) learner: Ex07 fails for its own reason -> [interest accrued for one day on loan 433] expected: 20 but was: 40.00 org.opentest4j.AssertionFailedError:
PASS  [round 2] (b) learner: Ex08 fails for its own reason -> [repayments on healthy loans the morning after the aborted COB] Expecting empty but was: ["loan 423 -> HTTP 409", "loan 424 -> HTTP 409", "loan 425 -> HTTP 409"...
PASS  [round 2] (b) learner: Ex09 fails for its own reason -> [last closed date after night two] expected: 2026-04-16 (java.time.LocalDate) but was: 2026-04-15 (java.time.LocalDate) org.opentest4j.AssertionFailedError:
PASS  [round 2] (b) learner: Ex10 fails for its own reason -> [loan applications that failed out of 8] Expecting empty but was: ["HTTP 500: {"type":"about:blank","title":"Internal Server Error","status":500,"detail":"org.s...
PASS  [round 2] (b) learner: Ex11 fails for its own reason -> [one day of interest on 250,000.00 USD at 3%] expected: 20.55 but was: 20.50 org.opentest4j.AssertionFailedError:
PASS  [round 2] (b) learner, run alone (-Dtest=Ex01RejectedRepaymentTest): fails for its own reason -> [repayment history after the API answered 422 to the only repayment attempt] Expecting empty but was: [{"repay...
PASS  [round 2] (b) learner, run alone (-Dtest=Ex02DeclinedLoanApplicationTest): fails for its own reason -> [loans on the books of customer C-EX02 after the declined application] Expecting actual: [4000000.00, 2000000....
PASS  [round 2] (b) learner, run alone (-Dtest=Ex03CobFailureDiagnosticsTest): fails for its own reason -> [account lock of the loan COB could not process] Expecting Optional to contain a value but it was empty. java....
PASS  [round 2] (b) learner, run alone (-Dtest=Ex04LargeCobRunTest): fails for its own reason -> [loans not closed exactly once for 2026-04-16 (296 of 400)] Expecting empty but was: ["loan 1: closed=null int...
PASS  [round 2] (b) learner, run alone (-Dtest=Ex05TellerDuringCobTest): fails for its own reason -> [last closed business date of the loan] expected: 2026-04-16 (java.time.LocalDate) but was: null org.opentest4...
PASS  [round 2] (b) learner, run alone (-Dtest=Ex06OverdueReportTest): fails for its own reason -> [SQL statements executed by one overdue report call with 20 overdue loans] Expecting actual: 22L to be less th...
PASS  [round 2] (b) learner, run alone (-Dtest=Ex07CobRerunTest): fails for its own reason -> [interest accrued for one day on loan 1] expected: 20 but was: 40.00 org.opentest4j.AssertionFailedError:
PASS  [round 2] (b) learner, run alone (-Dtest=Ex08AbortedCobTest): fails for its own reason -> [repayments on healthy loans the morning after the aborted COB] Expecting empty but was: ["loan 2 -> HTTP 409"...
PASS  [round 2] (b) learner, run alone (-Dtest=Ex09ConsecutiveBusinessDaysTest): fails for its own reason -> [last closed date after night two] expected: 2026-04-16 (java.time.LocalDate) but was: 2026-04-15 (java.time.L...
PASS  [round 2] (b) learner, run alone (-Dtest=Ex10LoanApplicationBurstTest): fails for its own reason -> [loan applications that failed out of 8] Expecting empty but was: ["HTTP 500: {"type":"about:blank","title":"I...
PASS  [round 2] (b) learner, run alone (-Dtest=Ex11InterestReconciliationTest): fails for its own reason -> [one day of interest on 250,000.00 USD at 3%] expected: 20.55 but was: 20.50 org.opentest4j.AssertionFailedErr...
PASS  [round 2] (c) fix only 01: Ex01 passes (24s)
PASS  [round 2] (c) fix only 01: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 01: non-exercise tests pass
PASS  [round 2] (c) fix only 02: Ex02 passes (24s)
PASS  [round 2] (c) fix only 02: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 02: non-exercise tests pass
PASS  [round 2] (c) fix only 03: Ex03 passes (25s)
PASS  [round 2] (c) fix only 03: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 03: non-exercise tests pass
PASS  [round 2] (c) fix only 04: Ex04 passes (25s)
PASS  [round 2] (c) fix only 04: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 04: non-exercise tests pass
PASS  [round 2] (c) fix only 05: Ex05 passes (25s)
PASS  [round 2] (c) fix only 05: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 05: non-exercise tests pass
PASS  [round 2] (c) fix only 06: Ex06 passes (24s)
PASS  [round 2] (c) fix only 06: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 06: non-exercise tests pass
PASS  [round 2] (c) fix only 07: Ex07 passes (24s)
PASS  [round 2] (c) fix only 07: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 07: non-exercise tests pass
PASS  [round 2] (c) fix only 08: Ex08 passes (26s)
PASS  [round 2] (c) fix only 08: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 08: non-exercise tests pass
PASS  [round 2] (c) fix only 09: Ex09 passes (25s)
PASS  [round 2] (c) fix only 09: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 09: non-exercise tests pass
PASS  [round 2] (c) fix only 10: Ex10 passes (22s)
PASS  [round 2] (c) fix only 10: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 10: non-exercise tests pass
PASS  [round 2] (c) fix only 11: Ex11 passes (24s)
PASS  [round 2] (c) fix only 11: the other 10 exercises still fail (10 failing)
PASS  [round 2] (c) fix only 11: non-exercise tests pass
PASS  [round 3] (a) baseline: 14 test classes, all pass (20s) 
PASS  [round 3] (b) learner: non-exercise CobJobTest passes
PASS  [round 3] (b) learner: non-exercise LoanApiTest passes
PASS  [round 3] (b) learner: non-exercise RepaymentApiTest passes
PASS  [round 3] (b) learner: Ex01 fails for its own reason -> [repayment history after the API answered 422 to the only repayment attempt] Expecting empty but was: [{"repaymentId":1,"loanId":1,"amount":100001.0,"principalP...
PASS  [round 3] (b) learner: Ex02 fails for its own reason -> [loans on the books of customer C-EX02 after the declined application] Expecting actual: [4000000.00, 2000000.00] to contain exactly (and in same order):
PASS  [round 3] (b) learner: Ex03 fails for its own reason -> [account lock of the loan COB could not process] Expecting Optional to contain a value but it was empty. java.lang.AssertionError: [account lock of the loan COB...
PASS  [round 3] (b) learner: Ex04 fails for its own reason -> [loans not closed exactly once for 2026-04-16 (295 of 400)] Expecting empty but was: ["loan 2: closed=null interest=0.00 (expected 20) accrual entries=0", "loan...
PASS  [round 3] (b) learner: Ex05 fails for its own reason -> [last closed business date of the loan] expected: 2026-04-16 (java.time.LocalDate) but was: null org.opentest4j.AssertionFailedError:
PASS  [round 3] (b) learner: Ex06 fails for its own reason -> [SQL statements executed by one overdue report call with 20 overdue loans] Expecting actual: 22L to be less than or equal to:
PASS  [round 3] (b) learner: Ex07 fails for its own reason -> [interest accrued for one day on loan 433] expected: 20 but was: 40.00 org.opentest4j.AssertionFailedError:
PASS  [round 3] (b) learner: Ex08 fails for its own reason -> [repayments on healthy loans the morning after the aborted COB] Expecting empty but was: ["loan 423 -> HTTP 409", "loan 424 -> HTTP 409", "loan 425 -> HTTP 409"...
PASS  [round 3] (b) learner: Ex09 fails for its own reason -> [last closed date after night two] expected: 2026-04-16 (java.time.LocalDate) but was: 2026-04-15 (java.time.LocalDate) org.opentest4j.AssertionFailedError:
PASS  [round 3] (b) learner: Ex10 fails for its own reason -> [loan applications that failed out of 8] Expecting empty but was: ["HTTP 500: {"type":"about:blank","title":"Internal Server Error","status":500,"detail":"org.s...
PASS  [round 3] (b) learner: Ex11 fails for its own reason -> [one day of interest on 250,000.00 USD at 3%] expected: 20.55 but was: 20.50 org.opentest4j.AssertionFailedError:
PASS  [round 3] (b) learner, run alone (-Dtest=Ex01RejectedRepaymentTest): fails for its own reason -> [repayment history after the API answered 422 to the only repayment attempt] Expecting empty but was: [{"repay...
PASS  [round 3] (b) learner, run alone (-Dtest=Ex02DeclinedLoanApplicationTest): fails for its own reason -> [loans on the books of customer C-EX02 after the declined application] Expecting actual: [4000000.00, 2000000....
PASS  [round 3] (b) learner, run alone (-Dtest=Ex03CobFailureDiagnosticsTest): fails for its own reason -> [account lock of the loan COB could not process] Expecting Optional to contain a value but it was empty. java....
PASS  [round 3] (b) learner, run alone (-Dtest=Ex04LargeCobRunTest): fails for its own reason -> [loans not closed exactly once for 2026-04-16 (297 of 400)] Expecting empty but was: ["loan 3: closed=null int...
PASS  [round 3] (b) learner, run alone (-Dtest=Ex05TellerDuringCobTest): fails for its own reason -> [last closed business date of the loan] expected: 2026-04-16 (java.time.LocalDate) but was: null org.opentest4...
PASS  [round 3] (b) learner, run alone (-Dtest=Ex06OverdueReportTest): fails for its own reason -> [SQL statements executed by one overdue report call with 20 overdue loans] Expecting actual: 22L to be less th...
PASS  [round 3] (b) learner, run alone (-Dtest=Ex07CobRerunTest): fails for its own reason -> [interest accrued for one day on loan 1] expected: 20 but was: 40.00 org.opentest4j.AssertionFailedError:
PASS  [round 3] (b) learner, run alone (-Dtest=Ex08AbortedCobTest): fails for its own reason -> [repayments on healthy loans the morning after the aborted COB] Expecting empty but was: ["loan 2 -> HTTP 409"...
PASS  [round 3] (b) learner, run alone (-Dtest=Ex09ConsecutiveBusinessDaysTest): fails for its own reason -> [last closed date after night two] expected: 2026-04-16 (java.time.LocalDate) but was: 2026-04-15 (java.time.L...
PASS  [round 3] (b) learner, run alone (-Dtest=Ex10LoanApplicationBurstTest): fails for its own reason -> [loan applications that failed out of 8] Expecting empty but was: ["HTTP 500: {"type":"about:blank","title":"I...
PASS  [round 3] (b) learner, run alone (-Dtest=Ex11InterestReconciliationTest): fails for its own reason -> [one day of interest on 250,000.00 USD at 3%] expected: 20.55 but was: 20.50 org.opentest4j.AssertionFailedErr...
PASS  [round 3] (c) fix only 01: Ex01 passes (21s)
PASS  [round 3] (c) fix only 01: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 01: non-exercise tests pass
PASS  [round 3] (c) fix only 02: Ex02 passes (21s)
PASS  [round 3] (c) fix only 02: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 02: non-exercise tests pass
PASS  [round 3] (c) fix only 03: Ex03 passes (20s)
PASS  [round 3] (c) fix only 03: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 03: non-exercise tests pass
PASS  [round 3] (c) fix only 04: Ex04 passes (20s)
PASS  [round 3] (c) fix only 04: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 04: non-exercise tests pass
PASS  [round 3] (c) fix only 05: Ex05 passes (19s)
PASS  [round 3] (c) fix only 05: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 05: non-exercise tests pass
PASS  [round 3] (c) fix only 06: Ex06 passes (19s)
PASS  [round 3] (c) fix only 06: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 06: non-exercise tests pass
PASS  [round 3] (c) fix only 07: Ex07 passes (20s)
PASS  [round 3] (c) fix only 07: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 07: non-exercise tests pass
PASS  [round 3] (c) fix only 08: Ex08 passes (20s)
PASS  [round 3] (c) fix only 08: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 08: non-exercise tests pass
PASS  [round 3] (c) fix only 09: Ex09 passes (20s)
PASS  [round 3] (c) fix only 09: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 09: non-exercise tests pass
PASS  [round 3] (c) fix only 10: Ex10 passes (18s)
PASS  [round 3] (c) fix only 10: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 10: non-exercise tests pass
PASS  [round 3] (c) fix only 11: Ex11 passes (20s)
PASS  [round 3] (c) fix only 11: the other 10 exercises still fail (10 failing)
PASS  [round 3] (c) fix only 11: non-exercise tests pass
```

Result: ALL CHECKS PASSED

Logs: /tmp/mini-cob-matrix-f5yb9hzs/logs
