# Phase Construction: Critical Assessment

## 1. Summary of Phase A Results

Phase A produced a statistically significant improvement over the paper baseline.
The one-sample Wilcoxon signed-rank test against the fixed baseline of F1=0.7652
returned W=150, p=0.0487, with a medium effect size (r=0.37). The mean F1 across
20 seeds was 0.7704, with 13 of 20 seeds exceeding the baseline. This is a modest
but real improvement, and the result is directionally consistent across the
majority of seeds.

The per-class breakdown reveals that the aggregate improvement conceals opposing
effects. PER benefits most from augmentation (B-PER net +7 token-level corrections
in the seed 42 analysis). ORG is the primary source of degradation (B-ORG net −10,
I-ORG net −7). The dominant ORG error pattern is B-ORG → O (8 cases) and
I-ORG → I-LOC (7 cases), indicating a geometric problem in the embedding space:
organisations with strong locational associations in the Wikidata graph are embedded
in proximity to LOC vectors, causing the injected signal to pull ORG representations
toward the LOC region.

---

## 2. The Coverage-Stratified Finding

The most diagnostically important result from the Phase A XAI analysis is the
coverage-stratified accuracy comparison. KG-covered entities — those for which a
non-zero TransE embedding was successfully injected — performed worse under
augmentation than uncovered entities receiving zero vectors (delta −0.080, n=25
covered; delta −0.013, n=388 uncovered).

This inverts the intended mechanism. Covered entities are the ones for which the
KG should provide the most benefit. The finding indicates that gaBERT already
resolves well-known, frequently occurring entities correctly from sequence context
alone, and the injected TransE vectors introduce a conflicting signal rather than
new information. The uncovered entity result effectively rules out the injection
pipeline as the source of degradation — zero vectors produce negligible
interference, confirming that the problem lies in the content of the embeddings
rather than the augmentation mechanism itself.

---

## 3. Embedding Quality: Phase A

The UMAP projection of Phase A TransE embeddings shows a structureless cloud with
no visible separation between PER, LOC, and ORG entities. Embedding norm analysis
confirms that all 1,563 vectors have L2 norm exactly 1.0000, ruling out training
instability or degenerate vectors as an explanation. The poor geometric structure
is attributable to graph sparsity: Phase A has 2.09 edges per grounded node, well
below the 5–10 edges-per-node threshold associated with reliable TransE signal in
the literature. With so few relational constraints per entity, the training signal
is insufficient to learn geometrically meaningful positions.

The practical consequence is that the injected vectors carry no reliable type or
relational information. For the 18.6% of test entities that receive a non-zero
embedding, the signal is closer to structured noise than to useful world knowledge.

---

## 4. Phase B: Design Rationale and Limitations

Phase B was designed to address the coverage limitation of Phase A by constructing
a KG from parliamentary co-occurrence rather than Wikidata property lookup. The
hypothesis was that a larger triple set derived from domain-matched corpora would
increase entity-level coverage and improve the embedding signal for entities absent
from Wikidata.

The Phase B graph contains 9,622 triples — more than Phase A — but uses a single
relation type (CO\_OCCURS\_WITH). This is the critical limitation. TransE learns
entity positions by optimising h + r ≈ t for each triple. With only one relation
vector r, all entity pairs are pushed toward the same geometric relationship
regardless of their actual semantic type. The model has no structural signal to
differentiate PER, LOC, and ORG entities spatially, and the resulting UMAP
projection confirms this: the Phase B embedding space is as structureless as
Phase A despite the larger triple count.

Entity-level coverage on the test set is 19.6% for Phase B, slightly lower than
Phase A's 23.3%. PER coverage is particularly poor at approximately 1% — a
consequence of the lookup relying on surface string matching against QID-grounded
entities, and PER entities in parliamentary text appearing predominantly as
surname-only references that cannot be reliably matched without coreference
resolution.

The difference in graph storage between phases — Neo4j for Phase A, flat
triple files for Phase B — reflects a construction decision rather than a
methodological inconsistency. Phase A required multi-source integration and
topology validation across seven relation types; Neo4j was the appropriate
tool for that task. Phase B generated triples programmatically from
co-occurrence counts across a single relation type, making a flat file
sufficient. The consequence of this difference is that the two graphs cannot
be directly compared as graph structures — edge density, clustering, and
degree distribution figures for Phase B are computed from the triple file
rather than from a queryable graph database. This does not affect the NER
results, which depend only on the quality of the TransE embeddings produced
from each triple set, but it does mean that the Phase A graph is more fully
documented and inspectable than Phase B.

---

## 5. Phase A vs Phase B: Statistical Comparison

The two-sample Wilcoxon test comparing Phase A and Phase B F1 distributions finds
no statistically significant difference (p=0.7012, r=0.086, negligible effect). The
phases are statistically indistinguishable despite their different construction
approaches and triple counts. Phase B's mean F1 of 0.7771 is marginally higher than
Phase A's 0.7704, but this difference is within the noise of 20-seed variance.

Phase B did not reach significance against the paper baseline (W=133, p=0.1559,
small effect). The failure to replicate Phase A's significant result is attributable
to the single-relation-type limitation: the co-occurrence graph produces
lower-quality embeddings than the Wikidata property graph despite greater volume.

The key empirical finding across both phases is that relation diversity is a more
important driver of TransE embedding quality than triple volume. A graph with 7
relation types and 6,944 triples (Phase A) produces a statistically significant NER
improvement; a graph with 1 relation type and 9,622 triples (Phase B) does not.

---

## 6. Motivation for the Ablation Study

The phase construction work identifies two confounded variables that make it
difficult to isolate the source of KG augmentation effects:

1. **KG source** — Wikidata property graph (Phase A) vs parliamentary
   co-occurrence graph (Phase B)
2. **Injection architecture** — late fusion with four-layer concatenation
   (Phase A) vs additive fusion with single hidden state (Phase B)

Because both variables change simultaneously between phases, the observed
performance difference cannot be attributed unambiguously to either. The ablation
study is designed to disentangle these factors through a controlled factorial
comparison holding one variable constant while the other varies.

Additionally, the phase construction work motivates specific requirements for the
ablation study KG:

- Minimum edge density of 5–10 edges per grounded node before embedding training
- Multiple relation types to provide geometric diversity in the TransE space
- Domain-matched entity coverage prioritising the entity types where gaBERT is
  weakest and KG signal would provide genuinely new information
- No proxy embeddings — ungrounded entities should receive zero vectors

The ablation study design and its justification are documented separately in the
dissertation methodology chapter.

---

## References

Adkins, J. R., Collins, H., Wagner, J., Walsh, A., & Davis, B. (2025). Named
entity recognition for the Irish language. *Proceedings of the 21st Workshop on
Multiword Expressions (MWE 2025)*.

Shi, B., & Weninger, T. (2018). Open-world knowledge graph completion.
*Proceedings of the 32nd AAAI Conference on Artificial Intelligence, 32*(1).
https://doi.org/10.1609/aaai.v32i1.11535
