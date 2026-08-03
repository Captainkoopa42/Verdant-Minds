# Verdant Workbench Provider Connections — WB-08

External models are **teaching assistants**, not Verdant cognition.

The supported flow is:

```text
human goal / outside LLM / configured HTTP provider
    -> captured raw response
    -> immutable `.vpcap`
    -> editable `verdant.teaching.bundle.v1`
    -> human review
    -> deterministic curriculum compiler
    -> frozen `.vcurr`
    -> Verdant
```

## Manual / outside-website workflow

Use **Connections -> Manual / External LLM Paste**. Ask any external model to return `verdant.teaching.bundle.v1`, paste the response, and capture it. A capture does not teach Verdant. A valid capture can be opened in Curriculum Studio, edited, compiled, and frozen normally.

## HTTP JSON providers

A provider config may declare an endpoint, model identifier, generation settings, and the **name** of an environment variable containing a secret. Secret values are read only at call time and are not written to provider configs, captures, checkpoints, event logs, curricula, or experiment packages.

The generic adapter sends JSON containing `model`, `prompt`, `system_prompt`, `settings`, and `expected_schema`. It accepts either a raw teaching-bundle JSON response or `{ "output": "..." }` where `output` is the teaching-bundle JSON string.

## Reproducibility

Provider calls are never assumed repeatable. The immutable `.vpcap` stores request hash, response hash, raw response, parse result, provider/model metadata, and timestamp. Experiments should use the captured artifact rather than call the model again.
