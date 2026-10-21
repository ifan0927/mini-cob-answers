package com.minicob.cob;

import com.minicob.cob.step.CobStepContext;
import com.minicob.cob.step.LoanCobBusinessStep;
import com.minicob.context.BusinessDateContext;
import com.minicob.loan.Loan;
import com.minicob.loan.LoanNotFoundException;
import java.util.List;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.stereotype.Component;

/**
 * Runs the configured business steps against one loan.
 */
@Component
public class LoanCobItemProcessor implements ItemProcessor<Loan, ProcessedLoan> {

    private final CobLoanRepository repository;
    private final List<LoanCobBusinessStep> steps;

    public LoanCobItemProcessor(CobLoanRepository repository, List<LoanCobBusinessStep> steps) {
        this.repository = repository;
        this.steps = steps;
    }

    @Override
    public ProcessedLoan process(Loan item) {
        // On a retry the item is the detached instance from the rolled-back attempt; work on the current row.
        Loan loan = repository.findForCob(item.getId()).orElseThrow(() -> new LoanNotFoundException(item.getId()));
        CobStepContext context = new CobStepContext(BusinessDateContext.getCobDate());
        for (LoanCobBusinessStep step : steps) {
            step.execute(loan, context);
        }
        loan.markBusinessDayClosed(context.cobDate());
        return new ProcessedLoan(loan, context.newTransactions());
    }
}
