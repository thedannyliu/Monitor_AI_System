# Redaction Guideline

## Purpose

This document defines how to derive `Redacted Spec` from `Full Spec` without destroying task solvability.

## Redaction Goal

A good redaction removes information that creates a meaningful assumption gap while preserving:

1. Core task identity
2. Basic executability
3. Main interface or bug localization clues

## Required Properties

A redacted task must satisfy all of the following:

1. The task still makes sense to a coding agent.
2. The removed information creates at least one reasonable design fork.
3. The removed information can later be recovered as one or more `Gold Assumptions`.
4. The task is not reduced to blind guessing.

## Recommended Redaction Targets

Prefer removing:

1. Backend or persistence requirements
2. Deployment targets
3. Validation constraints
4. Edge-case behavior
5. Compatibility requirements
6. API output semantics
7. Performance or accessibility constraints

## Prohibited Redaction Targets

Do not remove:

1. The main task objective
2. Required file or module references
3. Core reproduction clues for bug-fix tasks
4. Benchmark execution prerequisites
5. Any information that would make the task impossible to understand

## Benchmark-Specific Notes

### Self Bench

Redaction should focus on product and engineering choices, such as:

- static versus dynamic implementation
- storage requirements
- deployment target
- validation and non-functional requirements

### FEA-Bench

Redaction should focus on text-level constraints while keeping the benchmark's structural hints intact.

Keep:

- repository context
- required component signatures
- main feature request

Remove when possible:

- edge-case descriptions
- compatibility notes
- behavior examples
- documentation-only clarifications

### SWE-bench

Redaction should preserve bug localization but remove specification details.

Keep:

- affected module names
- bug symptom
- key reproduction clue

Remove when possible:

- version-specific clarifications
- exact expected behavior examples
- failure-mode details
- comment-thread acceptance clues

## Review Checklist

Before accepting a redacted task, confirm:

1. `Full Spec` and `Redacted Spec` differ on 2 to 5 important points.
2. Every removed point maps to at least one candidate gold assumption.
3. The task is still readable without the removed points.
4. The redaction targets the research question rather than general task difficulty.
