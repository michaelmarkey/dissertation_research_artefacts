# Irish NER Knowledge Graph Augmentation — Research Repository

This repository contains the notebooks, source code and data files supporting the methodology described in Chapter 3 of the dissertation *Structured Knowledge and Morphological Complexity: An Empirical Investigation of Knowledge Graph Augmentation for Irish Named Entity Recognition*. It is intended to provide a traceable record of the research pipeline. Re-executable components are identified below; cells requiring Neo4j, live Wikidata API access or local PyKEEN training runs are documented records of the original execution and are not intended to be re-run. Outputs from non-executable cells are preserved in the accompanying Kaggle datasets: `irish-ner-kg-consolidated` and `irish-ner-model-checkpoints`.

---

## Repository structure and narrative guide

### Phase 1: Entity vocabulary extraction and corpus inspection

**`Dissertation_2705_Phase1.ipynb`**

The starting point of the pipeline. The Adkins et al. (2025) CoNLL-format corpus is inspected and an extraction script walks the training, validation, and test splits token by token, reconstructing BIO-tagged entity spans and writing per-class vocabulary files (651 PER, 656 ORG, 573 LOC unique strings across all three splits). This notebook also contains the Oireachtas API query that retrieved the full historical membership list (1,928 records) and the fuzzy matching procedure used to assess PER entity coverage, and the Logainm enrichment pipeline that retrieved Irish-language placename data via Wikidata's P6872 property. These three procedures establish the entity pool from which the knowledge graph is seeded.

---

### Phase 2: Knowledge graph construction

**`01_kg_construction.ipynb`**

Documents the full Phase A KG construction: Wikidata property lookups for PER, LOC, and ORG entities; Neo4j MERGE loading; edge construction including the string-matched REPRESENTS fallback; and PyKEEN TransE embedding training. The notebook is a documented record of the original local run. Cells requiring Neo4j or the Wikidata REST API are not re-executable; outputs (per_nodes.csv, loc_nodes.csv, org_nodes.csv, stub_nodes.csv, kg_triples_clean.tsv, TransE_phase_a_embeddings.pkl) are available in the `irish-ner-kg-consolidated` Kaggle dataset.

**`gaBERT_RDA_CRF.ipynb`**

Contains the Logainm node enrichment functions (updating LOC nodes with canonical Irish-language forms and geographic hierarchy), the Neo4j graph statistics queries that produced the node and edge counts reported in Table 3.3, and the definitive PyKEEN TransE training cell run on the cleaned 6,944-triple file.

**`01_overview.md`**

Conceptual documentation of the overall research design: the unseen entity problem, Irish morphological mutation, the rationale for Phase A and Phase B KG construction strategies, the injection architectures, and the evaluation protocol. No executable outputs.

---

### Phase 3: Ablation study

**`augmentation_strategies.ipynb`**

Contains the baseline gaBERT-CRF architecture without KG injection, establishing the model structure against which augmented conditions are compared.

**`notebook-05-domain-matched-kg-construction-bis.ipynb`**

Contains the GaBERTCRF class implementing both injection architectures — late fusion (concatenation) and additive fusion — as a single conditional model class, alongside the Phase C domain-matched KG construction from corpus entities. Cell 28 contains a placeholder for results pending final execution at time of submission.

**`notebook-02-training-loop.ipynb`**

The primary ablation training notebook. Runs all eight conditions (A0–A3, C0–C3) across seven random seeds, producing ablation_results.json. Model checkpoints are saved to the `irish-ner-model-checkpoints` Kaggle dataset.

**`KG_Augmented_Test.ipynb`**

The KG-augmented NER pipeline: embedding lookup, entity pool matching, and augmented training data construction for the injection experiments.

**`notebook-03-statistical-analysis.ipynb`**

Paired Wilcoxon signed-rank tests and rank-biserial effect sizes for all pairwise condition comparisons. This is the authoritative statistical record for Chapter 3.2. Interprets null results against the coverage ceiling established in notebook-00-data-preparation.ipynb.

**`XAI_Notebook.ipynb`**

Token-level fix and error analysis comparing baseline and KG-augmented model outputs at seed 42. Coverage-stratified accuracy for covered (n=25) and uncovered (n=388) entities. Note: the Wilcoxon figures in this notebook are from an earlier run and are not the authoritative statistical result; the canonical analysis is in notebook-03-statistical-analysis.ipynb.

**`02_critical_assessment.md`**

Documents the Phase A and Phase B findings that motivated the factorial ablation design, including the Phase A Wilcoxon result (W=150, p=0.0487, r=0.37), the coverage-stratified XAI finding, and the Phase A vs Phase B comparison (p=0.7012). No executable outputs.

---

### Phase 4: Morphological augmentation pipeline

**`morph_pipeline.py`**

The self-contained Irish NER morphological expansion pipeline. The public API — load_pipeline() and expand_entity() — applies up to six layers of morphological expansion: Logainm lookup, UD Irish-IDT attested variants, manual genitive lexicon, WikiAnn harvest, deterministic rule-based mutation expander, and aspell-ga validity filter. Replaces an earlier Udar-based expander, which targets Russian and produced no valid Irish expansions; results from experiments using the Udar expander are invalidated and are not reported as primary findings.

**`morphology-pipeline.ipynb`**

Development notebook for the morphological pipeline, including the Layer 4 WikiAnn implementation. WikiAnn forms are added directly to the augmentation pool rather than being called inside expand_entity(); this notebook documents that procedure and the asset serialisation step.

**`07-domain-filtered-kg-morph-rda-ter.ipynb`**

Pipeline execution and statistical analysis for the morphological augmentation experiments. Contains the Wilcoxon tests comparing morphological RDA conditions against the no-augmentation baseline, and the per-class F1 breakdown.

**`Morphology pipeline XAI.ipynb`**

XAI analysis of the morphological pipeline output, including per-class F1, FP/FN error analysis, and coverage analysis. Benchmark comparison across replicated baseline (mean F1 0.7580), morph RDA (0.7742, p=0.0156), and parsed context augmentation (0.7791, p=0.0312).

---

### Phase 5: LLM factual QA evaluation

**`04_ner_evaluation_phase_b.ipynb`**

The full LLM evaluation notebook. Contains Phase B co-occurrence KG construction from the Herzog (2013) and ParlEE corpora, PyKEEN TransE training on the co-occurrence graph, and the four-condition factual QA evaluation using Claude Sonnet 4.6 via the Anthropic API. Primary result: KG with Wikidata fact triples (Condition 4) achieved 57.5% accuracy against a raw baseline of 34.2%. Note: the 34.2/30.8/14.2 figures for Conditions 1–3 require a clean rerun to establish a verified execution record; the 57.5% figure is the primary reported result.

**`irish_qa_questions.json`**

The 120-question Irish-language factual QA benchmark used across all LLM evaluation conditions. Covers 45 PER, 45 LOC, and 30 ORG entities across 11 Wikidata relation types; 59 of 120 questions use morphologically mutated surface forms confirmed against Logainm and the UD Irish-IDT lexicon.

---

## Reproducibility note

The following components are re-executable given the dependencies listed below: the entity vocabulary extraction script, the morphological pipeline (morph_pipeline.py and morphology-pipeline.ipynb), the statistical analysis notebook, the XAI notebook, and the LLM evaluation conditions (given an Anthropic API key).

The following are documented records not intended for re-execution: Neo4j loading cells, Wikidata API fetch cells (results will drift as Wikidata is a live database), and PyKEEN training cells (outputs preserved in Kaggle datasets).

**Key dependencies:** Python 3.11, PyTorch, HuggingFace Transformers, PyKEEN, Neo4j Python driver, scipy, pandas, aspell-ga, Anthropic Python SDK.

## Kaggle Datasets (private - available on request)

- [irish-ner-kg-consolidated](https://www.kaggle.com/datasets/michaelmarkey64/irish-ner-kg-consolidated)
- [Irish NER Ablation Checkpoints](https://www.kaggle.com/datasets/michaelmarkey64/irish-ner-model-checkpoints)
- [Irish NER Ablation Results](https://www.kaggle.com/datasets/michaelmarkey64/irish-ner-ablation-results)
- [morph-pipeline-assets](https://www.kaggle.com/datasets/michaelmarkey64/morph-pipeline-assets)
- [dissertation-rerun-checkpoints-30-07](https://www.kaggle.com/datasets/michaelmarkey64/dissertation-rerun-checkpoints-30-07)
- [no-kg-baseline-checkpoints](https://www.kaggle.com/datasets/michaelmarkey64/no-kg-baseline-checkpoints)
- [Adkins et al. 2025 corpus](https://www.kaggle.com/datasets/michaelmarkey64/adkins-et-al-2025)
- [herzog-mikhaylov-dail-debates](https://www.kaggle.com/datasets/michaelmarkey64/herzog-mikhaylov-dail-debates)
- [ParlEE IE plenary speeches](https://www.kaggle.com/datasets/michaelmarkey64/parlee-ie-plenary-speeches)
