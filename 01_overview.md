# Phase Construction: Overview

## 1. Task Definition

This project investigates whether knowledge graph (KG) augmentation improves
named entity recognition (NER) for Irish-language text. The base model is
gaBERT (`DCU-NLP/bert-base-irish-cased-v1`), a BERT-base model pre-trained on
Irish-language corpora. A Conditional Random Field (CRF) layer is placed on top
of the BERT encoder to model label sequence dependencies. The benchmark corpus
is the Adkins et al. (2025) Irish NER dataset, which provides train/validation/test
splits in CoNLL format with three entity classes: PER, LOC, and ORG. The
paper-reported baseline F1 is 0.7652.

---

## 2. The Unseen Entity Problem

Analysis of the Adkins corpus reveals that 75% of test set entity surface forms
do not appear in the training set. This is the primary motivation for KG
augmentation: a model fine-tuned on the training split has no parametric
knowledge of the majority of entities it will encounter at inference time.
Standard contextual encoders such as BERT can partially compensate through
surface form generalisation, but named entities — particularly Irish-language
proper nouns — resist this approach due to morphological mutation (see
Section 4).

---

## 3. Domain Context: Irish Parliamentary Text

The corpus is drawn from Dáil Éireann debate transcripts. This register has
several properties relevant to NER:

- Entity references are frequently partial: politicians are typically referred
  to by title and surname only (*an Teachta Ó Cuív*, *an tAire Martin*), making
  full-name coreference resolution necessary for reliable PER grounding
- Organisational names appear in both Irish and English forms and frequently
  as acronyms
- Location references include both anglicised and Irish-language placenames,
  often mutated

---

## 4. Irish Morphological Mutation

Irish initial mutation presents a canonicalisation challenge for entity lookup.
Two mutation processes are relevant.

Lenition inserts *h* after the initial consonant: *Páirc* → *Pháirc*. Reversal
removes the *h* to recover the canonical form.

Eclipsis prepends a new consonant and silences the original initial: *Baile Átha
Cliath* → *mBaile Átha Cliath*. Reversal removes the prepended consonant.

A canonicalisation function is applied to all surface form lookups to collapse
mutated variants to their canonical forms before KG matching. The function
handles both processes plus definite article stripping and genitive *d'* prefixes.
Full implementation is in `notebooks/01_kg_construction.ipynb`.

---

## 5. Knowledge Graph Construction: Phase A

Phase A constructs a KG from Wikidata using property-based lookup. Entities
from the Adkins corpus entity vocabulary are matched to Wikidata QIDs via the
Wikidata API. Three node types are populated: PER (politicians, public figures),
LOC (administrative regions, placenames), and ORG (government departments,
political parties, institutions).

Logainm (the Irish placenames database) is integrated for LOC nodes via Wikidata
property P6872, adding Irish and English name variants and a LOCATED_IN
geographic hierarchy. The Oireachtas API is used to cross-reference PER nodes,
confirming 65 politicians with constituency and committee membership edges.

The resulting graph contains 1,563 nodes and 6,944 triples across 7 relation
types. TransE embeddings (128 dimensions) are trained using PyKEEN. The
best-performing model achieves MRR=0.130, Hits@10=0.319. Embeddings are keyed
by Wikidata QID.

---

## 6. Knowledge Graph Construction: Phase B

Phase B constructs a KG from co-occurrence patterns in Irish parliamentary
debate corpora rather than structured Wikidata properties. Two corpora are used:

- Herzog et al. Dáil debates 1919–2013 (Harvard Dataverse), filtered to
  post-1980 speeches
- ParlEE Irish parliamentary speeches 2009–2019 (Harvard Dataverse)

For each sentence, entity surface forms from the corpus vocabulary are matched
using the canonicalisation lookup. Pairs of co-occurring entities generate
`(entity_A, CO_OCCURS_WITH, entity_B)` triples. After deduplication, noise
filtering, and frequency thresholding (minimum count = 3), the graph contains
575 entities and 9,622 triples across a single relation type.

TransE embeddings (128 dimensions) are trained on the Phase B triple set using
identical PyKEEN hyperparameters to Phase A. Embeddings are keyed by entity
surface string rather than QID.

Phase A and Phase B used different graph storage approaches reflecting their
different construction requirements. Phase A required multi-source integration
across seven relation types and was loaded into Neo4j for validation and
inspection during construction; the preserved graph is the dump file in
`phase_construction/neo4j/`. Phase B was constructed programmatically as a
flat triple file and passed directly to PyKEEN without Neo4j loading, as the
single relation type and uniform construction process required no graph
querying or topology validation. In both phases the graph itself is only used
during TransE embedding training — at inference time the model performs a
surface string lookup against a pre-computed embeddings file and injects the
retrieved vector, or a zero vector where no match is found. The Neo4j dump
therefore represents Phase A only; Phase B triples are documented in
`irish-ner-kg-consolidated/kg/phase_b/`.

---

## 7. Embedding Quality Assessment

UMAP projections of both embedding spaces are used as a diagnostic. A
well-trained TransE space should show spatial separation between entity types
(PER, LOC, ORG), as the relational structure of the graph encodes type-specific
patterns.

Phase A produces a structureless cloud with no visible type separation,
attributable to graph sparsity (2.09 edges per grounded node). Phase B produces
a similarly unstructured projection, attributable to the single relation type:
with only one relation vector, TransE has no structural signal to push entity
types into distinct regions.

Both phases fall below the 5–10 edges-per-node threshold identified in the
literature (Shi & Weninger, 2018) as necessary for reliable TransE signal.

---

## 8. NER Injection Architecture

KG embeddings are injected into the gaBERT-CRF model as an additional input
alongside the contextual BERT representations. Two fusion architectures are used
across phases.

**Phase A (Notebook 02):** Late fusion. The last four BERT hidden states are
concatenated (4×768 = 3,072 dimensions) and the KG embedding (128 dimensions)
is appended, giving a 3,200-dimensional input to the linear classifier.

**Phase B (Notebook 04):** Additive fusion. The KG embedding is projected to
BERT dimensionality (768) via a learned linear layer and added elementwise to
the last hidden state before the classifier.

Both architectures inject KG signal before the CRF layer. The architectural
difference is documented for transparency; results across phases are not
strictly architecturally comparable.

---

## 9. Evaluation Protocol

Each phase is evaluated over 20 random seeds using identical hyperparameters.
The primary metric is entity-level F1 computed by the CoNLL evaluation script
(conlleval), which requires correct span boundaries and correct entity type for
a prediction to count as a true positive.

Statistical significance is assessed using a one-sample Wilcoxon signed-rank
test comparing each phase's 20-seed F1 distribution against the fixed paper
baseline of 0.7652. A two-sample Wilcoxon test compares Phase A and Phase B
distributions directly.

---

## 10. Phase Construction Summary

| Component | Location |
|---|---|
| KG construction pipeline | `notebooks/01_kg_construction.ipynb` |
| NER training (pre-ablation runs) | `notebooks/02_NER_Training.ipynb` |
| XAI error analysis | `notebooks/03_xai_interpretations.ipynb` |
| Phase B evaluation | `notebooks/04_ner_evaluation_phase_b.ipynb` |
| Critical assessment | `docs/02_critical_assessment.md` |

---

## References

Adkins, J. R., Collins, H., Wagner, J., Walsh, A., & Davis, B. (2025). Named
entity recognition for the Irish language. *Proceedings of the 21st Workshop on
Multiword Expressions (MWE 2025)*.

Shi, B., & Weninger, T. (2018). Open-world knowledge graph completion.
*Proceedings of the 32nd AAAI Conference on Artificial Intelligence, 32*(1).
https://doi.org/10.1609/aaai.v32i1.11535
