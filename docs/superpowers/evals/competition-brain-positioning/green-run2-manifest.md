# GREEN Run 2 Frozen Inputs

- Frozen at: `2026-08-02 20:43:56 CST`
- Context isolation: fresh agents with `fork_turns=none`
- Model: `not exposed by runtime`
- Rubric visibility during generation: `no`
- Skill source bundle SHA-256: `be15f2c599a52683e856bb4b40e6d9a1ef74e84f568c1a34f63c86ff045dbb6d`
- Bundle hash method: SHA-256 of the sorted per-file SHA-256 manifest below; generated cache files excluded.

## Skill source files

```text
6bf0bc4585ae349d54f5c2bc3f4b35f7bc0c091ebbedb91f9e3b270f7022610a  SKILL.md
49e250c4d176275cf10c7d9036cb6aed0c07a61fe04757b4bb1f691918723bb0  agents/openai.yaml
508b52781e54eeeaef16b93209a0d5bc997223ad528f78fedb5a7aad0a7823cd  references/output-contracts.md
f17de1b30f1a1a1502d9f9c4aa1ff435a972d47000a625e632293825c187dd20  references/product-growth-hypotheses.md
3ce0da83bfdd292977b005023c1b3ad3d5ca70e6f95a31f09b71ac337b15981e  references/product-truth.md
e63f7ab3db82116a661e990e0721c26f58350a335e16f7cb064d98f6edde8a0a  references/source-restricted-rewrite.md
8f866ccee972018b0027dd37b76bde8ffdccb28ba86160c78f0d5dc0e285e45f  references/value-extraction.md
0c4f73fe5da377db8f2201923109031e4a61f62c04112a02ee4ee1ccda4863e8  references/voice-and-quality.md
04849f389e136e1113287fb55e8ac151599d0dd02fc04405e87907e9f957fdef  scripts/lint-copy.py
```

## Scenarios

```text
29231ba8d4749c4fa32f57e83175b8e78a3a2bea4d7c7e16ae639b8cb1cdeac0  scenario-1-full-positioning.md
85ff7d573e3b1ed4a1d6b3c09669ff38847274ffbe0fdfc09c34df082ad1db16  scenario-2-feature-synthesis.md
74ca7f5e8f7e5a78067e6c22d6b97d522565238a098f1227ea9db66e40bb60da  scenario-3-copy-rewrite.md
```

## Expected route loads

- Scenario 1: C route; `product-truth.md`, `product-growth-hypotheses.md`, `value-extraction.md`, plus voice/output references needed for the requested artifact.
- Scenario 2: B route; current scenario input is the only fact source; `value-extraction.md`, `source-restricted-rewrite.md` for the shared fact boundary, `output-contracts.md`, and B/general sections of `voice-and-quality.md`.
- Scenario 3: A route; `source-restricted-rewrite.md` and general/A sections of `voice-and-quality.md` only.
