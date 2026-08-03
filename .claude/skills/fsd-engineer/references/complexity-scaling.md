# Complexity Scaling Rules

The skill dynamically scales the FSD depth based on inferred system complexity.

## Complexity Tiers

| Tier | Characteristics | Target Length | Phases |
|------|----------------|---------------|--------|
| **Low** | Single MCU/service, simple data flows, 1-2 interfaces | 3-5 pages | 1-2 |
| **Medium** | MCU + app, or multi-service, OTA, 2-4 protocols | 6-12 pages | 2-3 |
| **High** | Distributed system, multi-protocol, real-time constraints, regulatory | 15-25+ pages | 3-5 |

## Complexity Signals

Infer complexity from:
- Number of distinct components (devices, services, apps)
- Number of protocols (BLE, WiFi, MQTT, HTTP, LoRa, OCPP, Modbus, etc.)
- Number of external integrations (cloud, Home Assistant, third-party APIs)
- Presence of real-time constraints or safety requirements
- Domain (SDR, energy systems, medical -> automatically higher complexity)
- Multi-user or multi-tenant requirements

## Confirm the estimate against the output

Complexity is inferred **before** drafting and confirmed **after**. The estimate
is a guess made from a description; the document is evidence.

The requirement count is the cheapest check — Low 5–15 FRs, Medium 15–30, High
30+. If the draft lands outside the band the initial estimate implied, the
estimate was wrong: reclassify, then check the structure matches the new tier
(Part dividers used, phase count, chapter depth, whether the V&V chapter carries
acceptance scenarios).

**Report the correction rather than quietly keeping the original label.** Someone
planning phases from "Medium" needs to know it produced a High-complexity
document — the phase count, review effort and test budget all follow from the
tier, not from the word used at the start.

The signals below are easy to under-weight in combination. A single MCU reads as
Low until you count four protocols, an external integration, and a domain that
carries its own bump — energy, medical and SDR are High before anything else is
considered.

## Scaling Behavior

| FSD Section | Low | Medium | High |
|------------|-----|--------|------|
| **Body organization** | Chapters in layer order, **Part dividers dropped** | Part dividers used; a handful of chapters per Part | Full Parts scheme, every interface its own chapter, depth to `####` |
| System Overview | Brief paragraph | Full section | Full + stakeholder analysis |
| Architecture | Single diagram description | Logical + platform + software | All subsections, detailed |
| Phases | 1-2 phases, brief | 2-3 phases, full exit criteria | 3-5 phases, dependencies mapped |
| Requirements (in chapters) | 5-15 FRs, 3-5 NFRs | 15-30 FRs, 5-10 NFRs | 30+ FRs, 10+ NFRs, constraints |
| Risks & Assumptions | Bullet list | Table with mitigations | Full risk register |
| Interface chapters | Inline descriptions | Tables per protocol | Full schemas, sequence descriptions |
| Operational Procedures | Bullet reading path | Numbered procedures | Detailed with recovery paths |
| V&V | Tiers + generated-matrix pointer | + acceptance scenarios | Full test architecture + acceptance, generated matrix |
| Troubleshooting | 3-5 common issues | Symptom-cause-fix table | Categorized diagnostic guide |
| Appendix | Constants only | Constants + examples | Constants + schemas + diagrams + logs |

Regardless of tier: requirements live in their component chapter (no global FR
section), the body follows **layer order** (application → … → foundation →
cross-cutting → operations & verification), and V&V traceability is a **pointer to
the generated matrix**, never a hand-filled status table. See
`references/canonical-fsd-structure.md`.

The **layer count itself scales with complexity**: three layers (L0/L1/L2) is the
common default, but a High-complexity system may warrant more (L0..Ln) — e.g. an
orchestration layer over domain logic, or a shared-services layer. Each layer is
one body Part; add layers only where a real one-way dependency boundary exists
(see `references/test-architecture.md`, "Scale the layer count to the system").
