# ASTRA CANON PROTECTION POLICY

You may:
- read canon code;
- refactor or optimize implementation;
- replace implementation while preserving the contract;
- add behavior compatible with every applicable ASTRA contract.

You must not:
- weaken ASTRA contracts;
- remove or bypass sentinel tests;
- change expected values merely to make tests green;
- reinterpret CANON as optional;
- promote RESEARCH_ONLY or UNRESOLVED claims to validated capability;
- import hidden ground truth into product runtime.

If a requested change conflicts with ASTRA_CANON:
1. stop only the conflicting change;
2. report `ASTRA_CONFLICT` with contract ID, code evidence, conflict reason and the minimal human question;
3. require explicit human authorization plus a versioned decision, evidence and review;
4. continue independent non-conflicting work.

CODEOWNERS is advisory unless repository rules require Code Owner review.

## Historical research non-authority

Historical and research branches are evidence archives, not canon. Superseded
branches or reports (including prior hardening/research lines such as
`fix/b1-b10-clean`) MUST NOT be merged or cited as current capability without
revalidation against current `main`, current `ASTRA_CANON`, and a reviewed
versioned decision. A historical status such as PASS or implemented is never
promoted merely because the branch or report still exists.
