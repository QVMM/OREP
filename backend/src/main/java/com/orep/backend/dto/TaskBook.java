package com.orep.backend.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class TaskBook {
    private boolean published;
    private List<TaskBookItem> items = new ArrayList<>();
}
