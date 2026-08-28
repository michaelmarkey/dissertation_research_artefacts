# morph_pipeline.py
# Self-contained Irish NER morphological expansion pipeline.
# Usage:
#   from morph_pipeline import load_pipeline, expand_entity
#   load_pipeline("/kaggle/input/datasets/michaelmarkey64/morph-pipeline-assets/")
#   forms, layers = expand_entity("Seán Ó Briain", "PER")

import os, re, json, pickle, subprocess
from collections import defaultdict

# Module-level lookup tables — populated by load_pipeline()
logainm_lookup = {}
ud_lookup = {}
MANUAL_GENITIVE_LEXICON = {}
wikiann_per = set()
wikiann_loc = set()

_aspell_available = None


# =============================================================================
# Asset loader
# =============================================================================

def load_pipeline(assets_dir):
    """
    Load all serialised lookup tables from assets_dir into module globals.
    Call once per session before using expand_entity().
    """
    global logainm_lookup, ud_lookup, MANUAL_GENITIVE_LEXICON
    global wikiann_per, wikiann_loc, _aspell_available

    with open(f"{assets_dir}/logainm_lookup.pkl", "rb") as f:
        raw = pickle.load(f)
        logainm_lookup = {k: set(v) for k, v in raw.items()}
    print(f"Loaded logainm_lookup     : {len(logainm_lookup)} entries")

    with open(f"{assets_dir}/ud_lookup.pkl", "rb") as f:
        raw = pickle.load(f)
        ud_lookup = {k: set(v) for k, v in raw.items()}
    print(f"Loaded ud_lookup          : {len(ud_lookup)} entries")

    with open(f"{assets_dir}/manual_genitive_lexicon.json", encoding="utf-8") as f:
        raw = json.load(f)
        MANUAL_GENITIVE_LEXICON = {k: set(v) for k, v in raw.items()}
    print(f"Loaded manual lexicon     : {len(MANUAL_GENITIVE_LEXICON)} entries")

    with open(f"{assets_dir}/wikiann_per.txt", encoding="utf-8") as f:
        wikiann_per = {line.strip() for line in f if line.strip()}
    print(f"Loaded wikiann_per        : {len(wikiann_per)} entities")

    with open(f"{assets_dir}/wikiann_loc.txt", encoding="utf-8") as f:
        wikiann_loc = {line.strip() for line in f if line.strip()}
    print(f"Loaded wikiann_loc        : {len(wikiann_loc)} entities")

    _aspell_available = _check_aspell()
    print(f"aspell-ga available       : {_aspell_available}")


def _check_aspell():
    """Return True if aspell-ga is available, attempt install if not."""
    result = subprocess.run(
        ["aspell", "-l", "ga", "list"],
        input="", capture_output=True, text=True
    )
    if result.returncode == 0:
        return True
    subprocess.run(
        ["apt-get", "install", "-y", "-q", "aspell", "aspell-ga"],
        capture_output=True
    )
    result = subprocess.run(
        ["aspell", "-l", "ga", "list"],
        input="", capture_output=True, text=True
    )
    return result.returncode == 0


# =============================================================================
# Layer 1: Logainm
# =============================================================================

def _layer1_logainm(surface):
    return logainm_lookup.get(surface, set())


# =============================================================================
# Layer 2: UD Irish-IDT
# =============================================================================

def _layer2_ud_single(surface):
    return ud_lookup.get(surface, set())


def _layer2_ud_multi(tokens):
    """
    For multi-token surfaces, check each token against ud_lookup.
    Returns set of reconstructed full-surface variants.
    """
    variants = set()
    for i, token in enumerate(tokens):
        token_variants = ud_lookup.get(token, set()) - {token}
        for variant in token_variants:
            if variant == variant.upper() and len(variant) > 2:
                continue
            reconstructed = tokens[:i] + [variant] + tokens[i+1:]
            # skip if any non-mutated token lost capitalisation
            valid = True
            for j, (orig, new) in enumerate(zip(tokens, reconstructed)):
                if j == i:
                    continue
                if orig[0].isupper() and new[0].islower():
                    valid = False
                    break
            if valid:
                variants.add(' '.join(reconstructed))
    return variants


# =============================================================================
# Layer 3: Manual genitive lexicon
# =============================================================================

def _layer3_manual(surface, entity_type):
    forms = set()
    if surface in MANUAL_GENITIVE_LEXICON:
        forms.update(MANUAL_GENITIVE_LEXICON[surface])
    tokens = surface.split()
    if len(tokens) > 1 and tokens[0] in MANUAL_GENITIVE_LEXICON:
        for variant in MANUAL_GENITIVE_LEXICON[tokens[0]]:
            forms.add(variant + " " + " ".join(tokens[1:]))
    if entity_type == "PER" and len(tokens) > 1:
        if tokens[0] in {"Mac", "Mhic"} and len(tokens) > 1:
            second = tokens[1]
            already_lenited = second[:2] in {
                "Bh","Ch","Dh","Fh","Gh","Mh","Ph","Sh","Th",
                "bh","ch","dh","fh","gh","mh","ph","sh","th"
            }
            if not already_lenited:
                lenited = second[0] + "h" + second[1:]
                rest = (" " + " ".join(tokens[2:])) if len(tokens) > 2 else ""
                forms.add("Mhic " + lenited + rest)
    return forms


# =============================================================================
# Layer 5: Deterministic expander
# =============================================================================

LENITION = {
    'b':'bh','c':'ch','d':'dh','f':'fh','g':'gh',
    'm':'mh','p':'ph','s':'sh','t':'th',
    'B':'Bh','C':'Ch','D':'Dh','F':'Fh','G':'Gh',
    'M':'Mh','P':'Ph','S':'Sh','T':'Th',
}

ECLIPSIS = {
    'b':'mb','c':'gc','d':'nd','f':'bhf','g':'ng',
    'p':'bp','t':'dt',
    'B':'mB','C':'gC','D':'nD','F':'bhF','G':'nG',
    'P':'bP','T':'dT',
}

H_PREFIX_TRIGGERS = set('aeiouáéíóúAEIOUÁÉÍÓÚ')


def _lenite(token):
    c = token[0] if token else ''
    return LENITION[c] + token[1:] if c in LENITION else token


def _eclipse(token):
    c = token[0] if token else ''
    if c in ECLIPSIS:
        return ECLIPSIS[c] + token[1:]
    if c in H_PREFIX_TRIGGERS:
        return 'n-' + token
    return token


def _h_prefix(token):
    if token and token[0] in H_PREFIX_TRIGGERS:
        return 'h' + token
    return token


def _apply_mac_mhic(surface):
    if 'Mac ' in surface:
        mhic_form = surface.replace('Mac ', 'Mhic ', 1)
        tokens = surface.split()
        lenited_first = _lenite(tokens[0])
        if lenited_first != tokens[0]:
            rest = ' '.join(tokens[1:]).replace('Mac ', 'Mhic ', 1)
            return [mhic_form, (lenited_first + ' ' + rest).strip()]
        return [mhic_form]
    if 'mac ' in surface:
        return [surface.replace('mac ', 'mhic ', 1)]
    return []


def _apply_nic_nig(surface):
    if 'Nic ' in surface:
        return surface.replace('Nic ', 'Nig ', 1)
    return None


def _deterministic_expand(surface, entity_type):
    forms = {surface}
    tokens = surface.split()
    if not tokens:
        return forms
    first = tokens[0]
    rest = ' '.join(tokens[1:])

    def add(mutated):
        if mutated and mutated != first:
            forms.add((mutated + (' ' + rest if rest else '')).strip())

    add(_lenite(first))
    add(_h_prefix(first))

    if entity_type in ('LOC', 'ORG'):
        eclipsed = _eclipse(first)
        add(eclipsed)
        if eclipsed != first:
            forms.add(('i ' + eclipsed + (' ' + rest if rest else '')).strip())

    for mac_form in _apply_mac_mhic(surface):
        forms.add(mac_form)

    nic_form = _apply_nic_nig(surface)
    if nic_form:
        forms.add(nic_form)

    return forms


# =============================================================================
# Layer 6: aspell-ga validity filter
# =============================================================================

SKIP_TOKENS = {
    'i','a','na','an','in','ag','ar','as','de','do',
    'faoi','le','ó','thar','um','sa','sna'
}

_H_VOWEL = re.compile(r'^[nh]-[aeiouáéíóúAEIOUÁÉÍÓÚ]')


def _aspell_check_token(token):
    result = subprocess.run(
        ["aspell", "-l", "ga", "list"],
        input=token + "\n",
        capture_output=True, text=True
    )
    return result.stdout.strip() == ""


def _aspell_check_surface(surface):
    if not _aspell_available:
        return True
    for token in surface.split():
        clean = token.strip("'-")
        if not clean:
            continue
        if clean.upper() == clean and len(clean) <= 5:
            continue
        if clean.lower() in SKIP_TOKENS:
            continue
        if not any(c.isalpha() for c in clean):
            continue
        if clean[0].isupper():
            continue
        if _H_VOWEL.match(clean):
            continue
        if not _aspell_check_token(clean):
            return False
    return True


def _filter_forms_aspell(forms, original_surface):
    retained = {original_surface}
    for form in forms:
        if form == original_surface:
            continue
        if _aspell_check_surface(form):
            retained.add(form)
    return retained


# =============================================================================
# Public API
# =============================================================================

def expand_entity(surface, entity_type):
    """
    Return (forms, layers_hit) for a single entity surface form.

    Parameters
    ----------
    surface     : str   Irish-language surface form, e.g. "Seán Ó Briain"
    entity_type : str   One of 'PER', 'LOC', 'ORG'

    Returns
    -------
    forms       : set[str]   All attested and generated variant forms
    layers_hit  : list[str]  Which layers contributed
    """
    forms = {surface}
    layers_hit = []

    # Layer 1: Logainm
    if entity_type == 'LOC':
        lg = _layer1_logainm(surface)
        if lg:
            forms.update(lg)
            layers_hit.append('logainm')

    # Layer 2: UD Irish-IDT
    tokens = surface.split()
    ud_hit = False
    if len(tokens) == 1:
        ud_forms = _layer2_ud_single(surface)
        if ud_forms:
            forms.update(ud_forms)
            ud_hit = True
    else:
        ud_variants = _layer2_ud_multi(tokens)
        if ud_variants:
            forms.update(ud_variants)
            ud_hit = True
    if ud_hit:
        layers_hit.append('ud')

    # Layer 3: Manual genitive lexicon
    manual_forms = _layer3_manual(surface, entity_type)
    new_manual = manual_forms - forms
    if new_manual:
        forms.update(new_manual)
        layers_hit.append('manual')

    # Layer 5: Deterministic expander + Layer 6: aspell-ga filter
    det_forms = _deterministic_expand(surface, entity_type)
    new_det = det_forms - forms
    if new_det:
        filtered = _filter_forms_aspell(new_det | {surface}, surface) - {surface}
        if filtered:
            forms.update(filtered)
            layers_hit.append('deterministic')

    return forms, layers_hit


def expand_entities(surfaces, entity_type):
    """
    Convenience wrapper — expand a list of surface forms of the same type.
    Returns dict[surface -> (forms, layers_hit)].
    """
    return {s: expand_entity(s, entity_type) for s in surfaces}
