---
type: Template
title: Experiment Record Template
description: Copy this note to capture a reproducible attempt without fabricated results.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
record_state: template
---

# Experiment Record Template

This template is not an experiment result. Copy into `experiments/`, assign a unique experiment and attempt ID, and start with `experiment_state: not_run`.

Include the question/hypothesis, eligibility criteria, subject split, input checksums, software versions, hardware, random seed where relevant, exact command/configuration, start/end conditions, logs, exit status, output location, measured values, failures, and interpretation limits. Preserve independent test isolation.

Report what actually happened. Use `running`, `completed`, or `failed` only when evidence supports it. Keep actual measurements separate from acceptance targets. Record deviations and repeated attempts rather than replacing inconvenient outcomes.

[Maintenance](../playbooks/knowledge-maintenance.md) · [Example protocol](../experiments/ernie-baseline.md)
