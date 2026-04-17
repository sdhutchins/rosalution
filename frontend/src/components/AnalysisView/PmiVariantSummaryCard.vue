<template>
  <div v-if="ready" class="summary-card">
    <p class="meta-line">
      <strong>Interpretation</strong> <span class="interp-tag" :class="interpretationTagClass">{{ caseField('Interpretation') || '—' }}</span>
      <span class="dot">·</span>
      <strong>Impact</strong> {{ firstTranscriptImpact }}
      <span class="dot">·</span>
      <strong>Zygosity</strong> {{ caseField('Zygosity') || '—' }}
      <span class="dot">·</span>
      <strong>Inheritance</strong> {{ caseField('Inheritance') || '—' }}
    </p>

    <p class="line">
      <strong>Gene summary</strong>
      <span class="val text-block">{{ geneSummaryShown }}</span>
      <button v-if="geneSummaryTruncated" type="button" class="more" @click.prevent="geneSummaryOpen = !geneSummaryOpen">{{ geneSummaryOpen ? 'less' : 'more' }}</button>
    </p>

    <p class="line"><strong>OMIM</strong> <span class="val text-block">{{ omimShown }}</span> <button v-if="omimTruncated" type="button" class="more" @click.prevent="omimOpen = !omimOpen">{{ omimOpen ? 'less' : 'more' }}</button></p>
    <p class="line"><strong>HPO</strong> <span class="val text-block">{{ hpoShown }}</span> <button v-if="hpoTruncated" type="button" class="more" @click.prevent="hpoOpen = !hpoOpen">{{ hpoOpen ? 'less' : 'more' }}</button></p>

    <p class="line"><strong>ClinVar</strong> <span class="val">{{ asText(annotations.ClinVar) }}</span></p>
    <p class="line scores">
      <strong>CADD</strong> <span class="val" :style="caddStyle">{{ asText(annotations.CADD) }}</span>
      <span class="pipe"> | </span>
      <strong>REVEL</strong> <span class="val" :style="revelStyle">{{ asText(annotations.REVEL) }}</span>
      <span class="pipe"> | </span>
      <strong>DITTO</strong> <span class="val" :style="dittoStyle">{{ asText(annotations.DITTO) }}</span>
      <span class="pipe"> | </span>
      <strong>AlphaMissense</strong> <span class="val" :style="alphaMissenseStyle">{{ asText(annotations.alphamissense_pathogenicity) }}</span>
      <span class="pipe"> | </span>
      <strong>Stability</strong> <span class="val" :style="stabilityStyle">{{ stabilityShown }}</span>
      <span class="pipe"> | </span>
      <strong>SpliceAI</strong> <span class="val" :style="spliceAiStyle">{{ spliceAiMax }}</span>
    </p>
    <p class="line"><strong>Consequences</strong> <span class="val">{{ formattedConsequences }}</span><span v-if="transcriptCount > 1" class="muted"> ({{ transcriptCount }} tx)</span></p>

    <p v-if="pocketsContainingVariantLine" class="line">
      <strong>Pockets Containing Variant</strong> <span class="val">{{ pocketsContainingVariantLine }}</span>
    </p>

    <p class="line"><strong>IntAct</strong> <span class="val">{{ intactLine }}</span></p>
    <p v-if="subcellularLine" class="line">
      <strong>Sub cellular Location &amp; Topologies</strong>
      <span class="val text-block">{{ subcellularLine }}</span>
    </p>

    <p v-if="visibleLinks.length" class="links-line">
      <strong>Links</strong>
      <span class="link-chips">
        <template v-for="(item, i) in visibleLinks" :key="`${item.label}-${item.href}`">
          <span v-if="i" class="sep" aria-hidden="true">·</span>
          <a :href="item.href" class="lnk" target="_blank" rel="noreferrer noopener">{{ item.label }}</a>
        </template>
      </span>
    </p>
  </div>
</template>

<script setup>
import {computed, onMounted, reactive, ref} from 'vue';
import Annotations from '@/models/annotations.js';
import {useScoreBarCalculations} from '@/components/AnnotationView/datasetRenderingUtility.js';

/** Matches ScoreDataset + annotation-render-layout.json variant section */
const pmiScoreStyles = {
  unavailableColours: {
    fillColour: '',
    backgroundColour: 'var(--rosalution-grey-100)',
    borderColour: '',
    textColour: 'var(--rosalution-grey-300)',
  },
  nominalColours: {
    fillColour: 'var(--rosalution-blue-200)',
    backgroundColour: 'var(--rosalution-blue-300)',
    borderColour: 'var(--rosalution-blue-100)',
    textColour: 'var(--rosalution-blue-300)',
  },
  closeToThresholdColours: {
    fillColour: 'var(--rosalution-yellow-200)',
    backgroundColour: 'var(--rosalution-yellow-300)',
    borderColour: 'var(--rosalution-yellow-100)',
    textColour: 'var(--rosalution-yellow-300)',
  },
  outOfThresholdColours: {
    fillColour: 'var(--rosalution-red-200)',
    backgroundColour: 'var(--rosalution-red-300)',
    borderColour: 'var(--rosalution-red-100)',
    textColour: 'var(--rosalution-red-300)',
  },
};

const SCORE_CONFIGS = {
  CADD: {minimum: 0, maximum: 99, bounds: {lowerBound: 9, upperBound: 19}, cutoff: 1},
  REVEL: {minimum: 0, maximum: 1, bounds: {lowerBound: 0.5, upperBound: 0.79}, cutoff: 1},
  DITTO: {minimum: 0, maximum: 1, bounds: {lowerBound: 0.5, upperBound: 0.79}, cutoff: 1},
  alphamissense_pathogenicity: {minimum: 0, maximum: 1, bounds: {lowerBound: 0.34, upperBound: 0.564}, cutoff: 1},
  /** Same bounds as spliceai_* score-datasets (max of four) */
  spliceai_max: {minimum: 0, maximum: 1, bounds: {lowerBound: 0.5, upperBound: 0.8}, cutoff: 1},
};

const OMIM_PREVIEW = 160;
const HPO_PREVIEW_TERMS = 3;

const props = defineProps({
  analysisName: {type: String, required: true},
  gene: {type: String, required: true},
  variant: {type: Object, required: true},
});

const annotations = reactive({});
const ready = computed(() => Object.keys(annotations).length > 0);
const geneSummaryOpen = ref(false);
const omimOpen = ref(false);
const hpoOpen = ref(false);

const linkOmim = computed(() => asUrl(annotations.OMIM_gene_search_url));
const linkHpo = computed(() => asUrl(annotations.HPO_gene_search_url));
const linkClinVar = computed(() => asUrl(annotations.ClinVar_variant_url));
const linkGnomadVariant = computed(() => asUrl(annotations.gnomAD_variant_url));
const linkSpliceAi = computed(() => asUrl(annotations.SpliceAI_variant_linkout));
const linkUniprot = computed(() => asUrl(annotations.uniprot_protein_linkout));
const linkIntAct = computed(() => asUrl(annotations.IntAct_Protein_Gene_Interactions_linkout));
const linkStringFromApi = computed(() => asUrl(annotations.stringdb_interactions_linkout));
const linkProtvarFromApi = computed(() => asUrl(annotations.protvar_protein_linkout));

/** ProtVar: API linkout when present; else EBI ProtVar query from HGVS (and p_dot when available). */
const linkProtvarResolved = computed(() => {
  if (linkProtvarFromApi.value) {
    return linkProtvarFromApi.value;
  }
  const hgvs = props.variant?.hgvs_variant;
  if (!hgvs || typeof hgvs !== 'string') {
    return '';
  }
  const pDot = props.variant?.p_dot;
  const search = pDot && typeof pDot === 'string' && pDot.trim() && pDot.trim() !== 'p.?' ?
    `${hgvs.trim()} ${pDot.trim()}` :
    hgvs.trim();
  return `https://www.ebi.ac.uk/ProtVar/query?search=${encodeURIComponent(search)}&assembly=AUTO`;
});

const linkUniprotResolved = computed(() => {
  if (linkUniprot.value) {
    return linkUniprot.value;
  }
  const id = rawUniprotAccession(annotations.uniprot_id);
  if (id && isLikelyUniprotAccession(id)) {
    return `https://www.uniprot.org/uniprotkb/${encodeURIComponent(id)}/entry`;
  }
  return '';
});

/** STRING: API URL, else Ensembl protein, else UniProt, else gene symbol; last resort string-db home */
const linkStringResolved = computed(() => {
  if (linkStringFromApi.value) {
    return linkStringFromApi.value;
  }
  const ens = rawStringFromAnnotation(annotations.ensembl_protein_id_without_version);
  if (ens) {
    return `https://string-db.org/network/9606.${ens}`;
  }
  const uid = rawUniprotAccession(annotations.uniprot_id);
  if (uid) {
    return `https://string-db.org/cgi/network.pl?identifier=${encodeURIComponent(uid)}&species=9606`;
  }
  if (props.gene) {
    return `https://string-db.org/cgi/network.pl?identifier=${encodeURIComponent(props.gene)}&species=9606`;
  }
  return 'https://string-db.org/';
});

const intactLine = computed(() => asText(annotations.IntAct_Protein_Gene_Interactions));

const subcellularLine = computed(() => {
  const t = asText(annotations.UniProt_Protein_Subcellular_Location_Topologies);
  return t !== 'N/A' ? t : '';
});

const visibleLinks = computed(() => {
  const pairs = [
    ['ProtVar', linkProtvarResolved.value],
    ['ClinVar', linkClinVar.value],
    ['OMIM', linkOmim.value],
    ['HPO', linkHpo.value],
    ['gnomAD', linkGnomadVariant.value],
    ['SpliceAI', linkSpliceAi.value],
    ['UniProt', linkUniprotResolved.value],
    ['STRING', linkStringResolved.value],
    ['IntAct', linkIntAct.value],
  ];
  return pairs.filter(([, href]) => href).map(([label, href]) => ({label, href}));
});

const transcriptCount = computed(() => Array.isArray(annotations.transcripts) ? annotations.transcripts.length : 0);
const firstTranscriptImpact = computed(() => {
  const first = Array.isArray(annotations.transcripts) ? annotations.transcripts[0] : null;
  return first?.Impact || 'N/A';
});
const formattedConsequences = computed(() => formatConsequences(firstTranscriptConsequenceRaw.value));
const firstTranscriptConsequenceRaw = computed(() => {
  const first = Array.isArray(annotations.transcripts) ? annotations.transcripts[0] : null;
  return first?.Consequences;
});

/** ProtVar pocket prediction (annotation-render-layout: protvar_variant_in_pockets_annotations_exist, variant_in_pocket_*). */
const pocketsContainingVariantLine = computed(() => {
  const hasFlag = rawAnnotationValue(annotations.protvar_variant_in_pockets_annotations_exist) === true;
  const pocketId = rawAnnotationValue(annotations.variant_in_pocket_prediction_pocket);
  const hasPocketId = pocketId !== null && pocketId !== undefined && pocketId !== '';
  const scoreVal = rawAnnotationValue(annotations.variant_in_pocket_prediction_confidence_level_score);
  const scoreConf = asText(annotations.variant_in_pocket_prediction_confidence_level_score_confidence);
  const meanVal = rawAnnotationValue(annotations.variant_in_pocket_prediction_mean_per_residue_model_form_pocket);
  const meanConf = asText(annotations.variant_in_pocket_prediction_mean_per_residue_model_form_pocket_confidence);

  if (!hasFlag && !hasPocketId) {
    return '';
  }

  const parts = [];
  if (hasPocketId) {
    parts.push(`Pocket ${pocketId}`);
  } else if (hasFlag) {
    parts.push('Variant in pocket');
  }

  if (scoreVal !== null && scoreVal !== undefined && scoreVal !== '' && !Number.isNaN(Number(scoreVal))) {
    const sc = Number(scoreVal);
    const confStr = scoreConf !== 'N/A' ? scoreConf : '';
    parts.push(`combined score ${sc.toFixed(2)}${confStr ? ` (${confStr})` : ''}`);
  } else if (scoreConf !== 'N/A') {
    parts.push(`combined score: ${scoreConf}`);
  }

  if (meanVal !== null && meanVal !== undefined && meanVal !== '' && !Number.isNaN(Number(meanVal))) {
    const m = Number(meanVal);
    const confStr = meanConf !== 'N/A' ? meanConf : '';
    parts.push(`pocket pLDD mean ${m.toFixed(1)}${confStr ? ` (${confStr})` : ''}`);
  }

  return parts.join('; ');
});

const geneSummaryFull = computed(() => asText(annotations['Gene Summary']));
const geneSummaryTruncated = computed(() => geneSummaryFull.value !== 'N/A' && geneSummaryFull.value.length > OMIM_PREVIEW);
const geneSummaryShown = computed(() => {
  if (geneSummaryFull.value === 'N/A') {
    return 'N/A';
  }
  if (!geneSummaryTruncated.value || geneSummaryOpen.value) {
    return geneSummaryFull.value;
  }
  return `${geneSummaryFull.value.slice(0, OMIM_PREVIEW).trim()}…`;
});

const omimFull = computed(() => asText(annotations.OMIM));
const omimTruncated = computed(() => omimFull.value !== 'N/A' && omimFull.value.length > OMIM_PREVIEW);
const omimShown = computed(() => {
  if (omimFull.value === 'N/A') {
    return 'N/A';
  }
  if (!omimTruncated.value || omimOpen.value) {
    return omimFull.value;
  }
  return `${omimFull.value.slice(0, OMIM_PREVIEW).trim()}…`;
});

const hpoTerms = computed(() => {
  const s = asText(annotations.HPO);
  if (s === 'N/A') {
    return [];
  }
  return s.split(/\s*;\s*/).map((x) => x.trim()).filter(Boolean);
});
const hpoTruncated = computed(() => hpoTerms.value.length > HPO_PREVIEW_TERMS);
const hpoShown = computed(() => {
  if (!hpoTerms.value.length) {
    return asText(annotations.HPO);
  }
  const list = hpoOpen.value ? hpoTerms.value : hpoTerms.value.slice(0, HPO_PREVIEW_TERMS);
  return list.join('; ');
});

const interpretationTagClass = computed(() => {
  const t = (caseField('Interpretation') || '').toLowerCase();
  if (t.includes('benign')) {
    return 'interp-benign';
  }
  if (t.includes('pathogenic')) {
    return 'interp-path';
  }
  if (t.includes('uncertain') || t.includes('vus') || t.includes('variant_u')) {
    return 'interp-vus';
  }
  return 'interp-neutral';
});

const spliceAiMaxNumeric = computed(() => {
  const keys = ['spliceai_acceptor_loss', 'spliceai_donor_loss', 'spliceai_acceptor_gain', 'spliceai_donor_gain'];
  const values = keys.map((k) => Number(annotations[k])).filter((v) => !Number.isNaN(v));
  if (values.length === 0) {
    return null;
  }
  return Math.max(...values);
});

const spliceAiMax = computed(() => (spliceAiMaxNumeric.value === null ? 'N/A' : spliceAiMaxNumeric.value.toFixed(3)));

const caddStyle = computed(() => scoreStyleForAnnotation(annotations.CADD, 'CADD'));
const revelStyle = computed(() => scoreStyleForAnnotation(annotations.REVEL, 'REVEL'));
const dittoStyle = computed(() => scoreStyleForAnnotation(annotations.DITTO, 'DITTO'));
const alphaMissenseStyle = computed(() => scoreStyleForAnnotation(annotations.alphamissense_pathogenicity, 'alphamissense_pathogenicity'));
const spliceAiStyle = computed(() => scoreStyleForNumber(spliceAiMaxNumeric.value, 'spliceai_max'));

const stabilityStyle = computed(() => {
  const st = rawStringFromAnnotation(annotations.foldx_5_0_stability_change_state);
  if (!st) {
    return {color: pmiScoreStyles.unavailableColours.textColour};
  }
  const s = st.toLowerCase();
  if (s.includes('unlikely destabilising')) {
    return {color: pmiScoreStyles.nominalColours.textColour};
  }
  if (s.includes('likely destabilising')) {
    return {color: pmiScoreStyles.outOfThresholdColours.textColour};
  }
  return {color: 'var(--rosalution-grey-500)'};
});

const stabilityShown = computed(() => {
  const num = asText(annotations.foldx_5_0_stability_change);
  const st = asText(annotations.foldx_5_0_stability_change_state);
  if (num !== 'N/A' && st !== 'N/A') {
    return `${num} (${st})`;
  }
  if (num !== 'N/A') {
    return num;
  }
  if (st !== 'N/A') {
    return st;
  }
  return 'N/A';
});

function scoreStyleForAnnotation(annotationValue, configKey) {
  const num = rawNumericFromAnnotations(annotationValue);
  return scoreStyleForNumber(num, configKey);
}

function scoreStyleForNumber(num, configKey) {
  const config = SCORE_CONFIGS[configKey];
  if (!config) {
    return {};
  }
  const {scoreStyling} = useScoreBarCalculations(num, config, pmiScoreStyles);
  return {color: scoreStyling.textColour};
}

function rawNumericFromAnnotations(value) {
  const u = unwrapAnnotationLeaf(value);
  if (u === null || u === undefined || u === '') {
    return null;
  }
  if (typeof u === 'number') {
    return Number.isNaN(u) ? null : u;
  }
  const n = parseFloat(String(u).replace(/,/g, ''));
  return Number.isNaN(n) ? null : n;
}

function unwrapAnnotationLeaf(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  if (Array.isArray(value) && value.length) {
    const first = value[0];
    if (first && typeof first === 'object' && 'value' in first) {
      return unwrapAnnotationLeaf(first.value);
    }
    return unwrapAnnotationLeaf(first);
  }
  if (typeof value === 'object' && 'value' in value) {
    return unwrapAnnotationLeaf(value.value);
  }
  return value;
}

function rawStringFromAnnotation(value) {
  const u = unwrapAnnotationLeaf(value);
  if (u === null || u === undefined || u === '') {
    return '';
  }
  return String(u).trim();
}

function caseField(name) {
  const row = (props.variant.case || []).find((c) => c.field === name);
  return row?.value?.length ? row.value.join(', ') : '';
}

function rawUniprotAccession(value) {
  if (value == null || value === '') {
    return '';
  }
  if (Array.isArray(value) && value.length) {
    const first = value[0];
    if (first && typeof first === 'object' && 'value' in first) {
      return rawUniprotAccession(first.value);
    }
    return rawUniprotAccession(first);
  }
  if (typeof value === 'object' && 'value' in value) {
    return rawUniprotAccession(value.value);
  }
  const token = String(value).trim().split(/[\s,;]/)[0];
  return !token || /^n\/?a$/i.test(token) ? '' : token;
}

function isLikelyUniprotAccession(s) {
  if (!s || s.length < 6 || s.length > 15) {
    return false;
  }
  return /^[A-Z][0-9][A-Z0-9]{3,}[0-9]$/i.test(s) || /^[A-Z][0-9][A-Z0-9]{8,12}$/i.test(s);
}

function formatConsequences(raw) {
  if (raw == null || raw === '') {
    return 'N/A';
  }
  const norm = (t) => String(t).replace(/_/g, ' ').trim();
  if (Array.isArray(raw)) {
    return raw.map(norm).filter(Boolean).join(', ');
  }
  if (typeof raw === 'string') {
    const t = raw.trim();
    if (t.startsWith('[') && t.endsWith(']')) {
      try {
        const p = JSON.parse(t);
        if (Array.isArray(p)) {
          return p.map(norm).filter(Boolean).join(', ');
        }
      } catch { /* */ }
      try {
        const p = JSON.parse(t.replace(/'/g, '"'));
        if (Array.isArray(p)) {
          return p.map(norm).filter(Boolean).join(', ');
        }
      } catch { /* */ }
      return t.slice(1, -1).replace(/"/g, '').replace(/'/g, '').split(',').map(norm).filter(Boolean).join(', ');
    }
    return norm(t);
  }
  return norm(raw);
}

function asUrl(value) {
  if (value == null || value === '') {
    return '';
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.startsWith('http://') || trimmed.startsWith('https://') ? trimmed : '';
  }
  if (Array.isArray(value) && value.length) {
    const first = value[0];
    if (first && typeof first === 'object' && first.value !== undefined) {
      return asUrl(first.value);
    }
    return asUrl(first);
  }
  return '';
}

function asText(value) {
  if (value == null || value === '') {
    return 'N/A';
  }
  if (Array.isArray(value)) {
    if (value.length && typeof value[0] === 'object' && value[0] !== null && 'value' in value[0]) {
      return value.map((e) => asText(e.value)).join('; ');
    }
    return value.join('; ');
  }
  if (typeof value === 'object') {
    if ('value' in value && value.value !== undefined) {
      return asText(value.value);
    }
    return JSON.stringify(value);
  }
  return String(value);
}

/** First raw value from annotation API shape `{ value }[]` or primitives. */
function rawAnnotationValue(value) {
  if (value == null || value === '') {
    return null;
  }
  if (Array.isArray(value) && value.length) {
    const first = value[0];
    if (first && typeof first === 'object' && first !== null && 'value' in first) {
      return first.value;
    }
    return first;
  }
  if (typeof value === 'object' && value !== null && 'value' in value) {
    return value.value;
  }
  return value;
}

onMounted(async () => {
  Object.assign(annotations, await Annotations.getAnnotations(props.analysisName, props.gene, props.variant.hgvs_variant));
});
</script>

<style scoped>
.summary-card {
  margin: var(--p-5) 0;
  padding: var(--p-10) var(--p-12);
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--rosalution-grey-500);
}

.meta-line {
  margin: 0 0 var(--p-10);
}

.meta-line .dot {
  margin: 0 var(--p-5);
  color: var(--rosalution-grey-200);
}

.interp-tag {
  display: inline-block;
  margin-left: var(--p-1);
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.8125rem;
}

.interp-benign {
  background: #e8f5e9;
  color: #1b5e20;
}

.interp-path {
  background: #ffebee;
  color: #b71c1c;
}

.interp-vus {
  background: #fff8e1;
  color: #e65100;
}

.interp-neutral {
  background: var(--rosalution-grey-50);
  color: var(--rosalution-grey-500);
}

.line {
  margin: 0 0 var(--p-8);
}

.line strong {
  margin-right: var(--p-5);
  color: black;
}

.val {
  font-weight: 400;
}

/* Same wrapping width for long text fields (gene summary, OMIM, HPO) */
.text-block {
  display: inline-block;
  max-width: 90ch;
  vertical-align: top;
}

.scores .pipe {
  color: var(--rosalution-grey-200);
  margin: 0 var(--p-5);
}

.muted {
  color: var(--rosalution-grey-400);
}

.more {
  margin-left: var(--p-5);
  padding: 0;
  border: none;
  background: none;
  color: var(--rosalution-purple-300);
  font-weight: 600;
  font-size: inherit;
  cursor: pointer;
  text-decoration: underline;
}

.links-line {
  margin-top: var(--p-12);
}

.links-line strong {
  margin-right: var(--p-8);
  color: black;
}

.link-chips {
  display: inline;
}

.link-chips .sep {
  margin: 0 var(--p-5);
  color: var(--rosalution-grey-200);
}

.lnk {
  color: var(--rosalution-purple-300);
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}

.lnk:hover {
  text-decoration: underline;
}
</style>
