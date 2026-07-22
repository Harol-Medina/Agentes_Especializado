package com.archaeologist.application.dto;

public record ErrorResponse(
    String error,
    String message
) {}
