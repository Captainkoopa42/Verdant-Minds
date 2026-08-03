# Verdant Workbench — WB-08 Provider Connections

**Status:** Complete  
**Workbench line:** 1.0 implementation sequence  
**Purpose:** Allow optional external curriculum assistance without turning an LLM or other provider into part of Verdant cognition.

## Implemented boundary

WB-08 now uses one teaching path regardless of author:

```text
human typing / outside LLM paste / HTTP JSON provider / future adapter
    -> immutable provider capture (.vpcap)
    -> editable verdant.teaching.bundle.v1
    -> human review/edit
    -> deterministic compiler
    -> frozen .vcurr
    -> Verdant
```

A provider response does not mutate an organism. It is first preserved as an immutable capture. Only a valid editable teaching bundle can be handed to Curriculum Studio, and it still follows the existing review/freeze/teach path.

## Provider modes

### Manual / external LLM paste

`provider_paste` is always available. This is the zero-dependency path for using a separate ChatGPT/Claude/Gemini/local-model window: request a `verdant.teaching.bundle.v1`, paste the response into Workbench, capture it, inspect it, and open it as editable curriculum source.

### Generic HTTP JSON provider

Workbench also supports a provider configuration containing:

- endpoint URL;
- model identifier;
- timeout;
- non-secret headers;
- the **name** of an environment variable containing the provider secret.

The secret value is read only for the network call. It is not written into configuration, provider capture, curriculum, checkpoint, telemetry or experiment artifacts.

## Reproducibility

Provider calls are not assumed deterministic. Every accepted response is stored in a content-addressed `.vpcap` containing the request/response hashes, raw response, parsed teaching bundle when valid, provider metadata and timestamps.

A future run can replay the exact captured response without contacting the provider again.

## Controlled proof

The WB-08 proof exercises both paths:

1. Capture the Workbench editable-teaching template through the manual provider.
2. Recover it from the immutable `.vpcap`.
3. Recompile it successfully through the existing curriculum compiler.
4. Run a local HTTP provider fixture with a bearer secret supplied from an environment variable.
5. Verify the fixture actually received the secret.
6. Verify the secret value is absent from the persisted provider artifact.
7. Verify only the environment-variable *name* is retained for provenance/configuration.

`all_gates_pass = true` in `workbench/artifacts/wb08_provider_connections_proof.json`.

## API / UI

New API surfaces include:

```text
GET  /api/v1/providers
POST /api/v1/providers
POST /api/v1/providers/{id}/capture-paste
POST /api/v1/providers/{id}/propose
GET  /api/v1/provider-captures
GET  /api/v1/provider-captures/{id}
GET  /api/v1/provider-captures/{id}/curriculum-source
GET  /api/v1/provider-captures/{id}/package
```

The **Connections** page is now operational in the dependency-free Workbench UI. It supports manual paste capture, capture inspection, `.vpcap` download and handoff into Curriculum Studio.

## Scientific boundary

WB-08 does **not** establish that an external model is part of Verdant reasoning. Provider text is authored teaching material. Verdant receives only the reviewed, deterministic compiled curriculum.

No vendor-specific hosted-model SDK is required for Workbench 1.0; the generic HTTP JSON adapter and manual capture path preserve the architecture while allowing later adapters.
