package com.orep.backend.service;

import java.time.LocalDate;

/** 日报可写日期：允许补最近若干天，不能写未来。 */
public final class DailyReportDatePolicy {

    public static final int MAX_BACKFILL_DAYS = 14;

    private DailyReportDatePolicy() {}

    public static LocalDate resolveWritableDate(LocalDate today, LocalDate requested) {
        LocalDate day = today == null ? LocalDate.now() : today;
        LocalDate target = requested == null ? day : requested;
        if (target.isAfter(day)) return day;
        LocalDate earliest = day.minusDays(MAX_BACKFILL_DAYS);
        if (target.isBefore(earliest)) {
            throw new IllegalArgumentException("只能补最近 " + MAX_BACKFILL_DAYS + " 天的日报");
        }
        return target;
    }

    public static boolean isBackfillAllowed(LocalDate today, LocalDate requested) {
        try {
            resolveWritableDate(today, requested);
            return true;
        } catch (IllegalArgumentException ignored) {
            return false;
        }
    }
}
