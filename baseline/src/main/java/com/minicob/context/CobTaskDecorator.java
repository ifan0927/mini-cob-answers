package com.minicob.context;

import java.util.Map;
import org.slf4j.MDC;
import org.springframework.core.task.TaskDecorator;

/**
 * Carries the submitting thread's context over to pooled COB worker threads.
 */
public class CobTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // Captured on the submitting thread. A pooled worker thread may still carry a previous run's state.
        BusinessDates dates = BusinessDateContext.getOrNull();
        Map<String, String> mdc = MDC.getCopyOfContextMap();
        return () -> {
            BusinessDates previousDates = BusinessDateContext.getOrNull();
            Map<String, String> previousMdc = MDC.getCopyOfContextMap();
            BusinessDateContext.restore(dates);
            setMdc(mdc);
            try {
                runnable.run();
            } finally {
                BusinessDateContext.restore(previousDates);
                setMdc(previousMdc);
            }
        };
    }

    private static void setMdc(Map<String, String> context) {
        if (context == null) {
            MDC.clear();
        } else {
            MDC.setContextMap(context);
        }
    }
}
