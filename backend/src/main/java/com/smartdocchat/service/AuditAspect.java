package com.smartdocchat.service;

import lombok.RequiredArgsConstructor;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.AfterReturning;
import org.aspectj.lang.annotation.AfterThrowing;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.stream.Collectors;

@Aspect
@Component
@RequiredArgsConstructor
public class AuditAspect {

    private final AuditService auditService;

    @Pointcut("within(@org.springframework.web.bind.annotation.RestController *)")
    public void controllerMethods() {}

    @AfterReturning(pointcut = "controllerMethods()", returning = "result")
    public void logControllerSuccess(JoinPoint jp, Object result) {
        String className = jp.getTarget().getClass().getSimpleName();
        String methodName = jp.getSignature().getName();
        String action = className + "." + methodName;
        String args = Arrays.stream(jp.getArgs())
                .map(a -> a != null ? a.getClass().getSimpleName() : "null")
                .collect(Collectors.joining(", "));
        auditService.logSuccess(action, className, null, "Args: [" + args + "]");
    }

    @AfterThrowing(pointcut = "controllerMethods()", throwing = "ex")
    public void logControllerFailure(JoinPoint jp, Throwable ex) {
        String className = jp.getTarget().getClass().getSimpleName();
        String methodName = jp.getSignature().getName();
        String action = className + "." + methodName;
        String args = Arrays.stream(jp.getArgs())
                .map(a -> a != null ? a.getClass().getSimpleName() : "null")
                .collect(Collectors.joining(", "));
        auditService.logFailure(action, className, null, "Args: [" + args + "]", ex.getMessage());
    }
}