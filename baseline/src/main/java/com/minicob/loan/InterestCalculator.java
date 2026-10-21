package com.minicob.loan;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import org.springframework.stereotype.Component;

/**
 * Simple-interest day calculation on an Actual/365 basis.
 */
@Component
public class InterestCalculator {

    static final BigDecimal DAYS_IN_YEAR = BigDecimal.valueOf(365);

    /**
     * One day of interest on {@code base} at {@code annualRate} (0.05 = 5% p.a.), rounded half-up to
     * the currency's minor unit.
     */
    public BigDecimal dailyInterest(BigDecimal base, BigDecimal annualRate, String currency) {
        int scale = Currencies.scaleOf(currency);
        // Divide last, with a MathContext: dividing the rate first would round it to the rate's own scale.
        BigDecimal exact = base.multiply(annualRate).divide(DAYS_IN_YEAR, MathContext.DECIMAL64);
        return exact.setScale(scale, RoundingMode.HALF_UP);
    }
}
