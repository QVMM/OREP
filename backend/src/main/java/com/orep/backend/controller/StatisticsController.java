package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.StatisticsVO;
import com.orep.backend.service.StatisticsService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@RestController
@RequestMapping("/api/statistics")
public class StatisticsController {

    @Autowired
    private StatisticsService statisticsService;

    @GetMapping("/overview")
    public Result<StatisticsVO> overview(@RequestParam(value = "days", required = false) Integer days,
                                         @RequestParam(value = "start", required = false) String start,
                                         @RequestParam(value = "end", required = false) String end,
                                         @RequestParam(value = "scope", required = false) String scope,
                                         HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        LocalDate startDate = parseDate(start);
        LocalDate endDate = parseDate(end);
        return Result.success(statisticsService.getOverview(tenantId, userId, role, days, startDate, endDate, scope));
    }

    private LocalDate parseDate(String value) {
        if (value == null || value.isBlank()) return null;
        return LocalDate.parse(value);
    }
}
