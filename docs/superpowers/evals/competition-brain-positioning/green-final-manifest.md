# Final GREEN Frozen Inputs

- Frozen at: `2026-08-02 21:01:22 CST`
- Generation isolation: one fresh agent per scenario, `fork_turns=none`
- Model: `not exposed by runtime`
- Rubric visibility during generation: `no`
- Skill source bundle SHA-256: `4cdad79ddb3eb332601be7b5759f615543b59bd0361f085ef9d2e581f9f861a4`
- Bundle hash method: SHA-256 of the sorted per-file SHA-256 manifest generated with absolute file paths under `/Users/liuyixing/.codex/skills/competition-brain-positioning`; generated cache files excluded. The table below abbreviates that fixed root and is not the byte-for-byte hash input.

## Skill source files

```text
3f3b1bc1e4b834057219de73ac399fa2ac531e053d2fc95e8fa6d3c5839d20c5  SKILL.md
49e250c4d176275cf10c7d9036cb6aed0c07a61fe04757b4bb1f691918723bb0  agents/openai.yaml
9ec482c84db1dec8338c8bfd6e7b2ee3794efe2b6bc86a729c1b0e2eff3fa334  references/output-contracts.md
f17de1b30f1a1a1502d9f9c4aa1ff435a972d47000a625e632293825c187dd20  references/product-growth-hypotheses.md
3ce0da83bfdd292977b005023c1b3ad3d5ca70e6f95a31f09b71ac337b15981e  references/product-truth.md
e63f7ab3db82116a661e990e0721c26f58350a335e16f7cb064d98f6edde8a0a  references/source-restricted-rewrite.md
7bb5425184cd0d45b4564323d0e0448daeef6142ebc20dfea135040d9a94a772  references/value-extraction.md
0c4f73fe5da377db8f2201923109031e4a61f62c04112a02ee4ee1ccda4863e8  references/voice-and-quality.md
04849f389e136e1113287fb55e8ac151599d0dd02fc04405e87907e9f957fdef  scripts/lint-copy.py
```

## Scenario files

```text
29231ba8d4749c4fa32f57e83175b8e78a3a2bea4d7c7e16ae639b8cb1cdeac0  scenario-1-full-positioning.md
85ff7d573e3b1ed4a1d6b3c09669ff38847274ffbe0fdfc09c34df082ad1db16  scenario-2-feature-synthesis.md
74ca7f5e8f7e5a78067e6c22d6b97d522565238a098f1227ea9db66e40bb60da  scenario-3-copy-rewrite.md
940698fcdadcddea85840219f1bc27050b4bf7cbdd0c3fdeb14ba6cb72b166e0  scenario-4-c-route-smoke.md
```

## Expected route loads

- Scenario 1, B: the scenario explicitly limits evidence to three frozen product files; generic value method, shared source boundary, B output contract, and general/B voice only.
- Scenario 2, B: scenario input as the only fact source; generic value method, shared source boundary, B output contract, and general/B voice only.
- Scenario 3, A: source-restricted rewrite contract and general/A voice only.
- Scenario 4, C route smoke: no source restriction; product truth, product growth hypotheses, generic value method, and needed voice/output contracts.
