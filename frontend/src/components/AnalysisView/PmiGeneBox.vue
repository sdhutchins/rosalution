<template>
  <div>
    <div v-for="variant, index in variants" :key="variant.hgvs_variant" class="rosalution-section-container variant-container">
      <input
        :id="variantToggleId(index, variant)"
        type="checkbox"
        checked
      />
      <div class="variant-name-line">
        <div class="variant" :data-test="`variant-row-${index}`">
          <span>{{ getCompleteHgvsVariantName(variant) }} ({{ gene }})</span>
            <CopyToClipboard
              class="copy-icon"
              :copyText="variant.hgvs_variant"
              @clipboard-copy="$emit('clipboard-copy', $event)"
              data-test="copy-button"
            />
            <label class="variant-score">
              <span>Score:</span>
              <select
                :value="getVariantScore(variant)"
                @change="setVariantScore(variant, $event.target.value)"
              >
                <option v-for="scoreOption in [1, 2, 3, 4]" :key="scoreOption" :value="scoreOption">
                  {{ scoreOption }}
                </option>
              </select>
            </label>
          </div>
          <span class="variant-controls">
          <span class="genomic-build"> {{ getBuild(variant.build) }} </span>
          <label class="collapsable-icon" :for="variantToggleId(index, variant)">
            <font-awesome-icon icon="chevron-down" size="lg" />
          </label>
        </span>
      </div>
      <div class="variant-content">
        <div class="variant-case-information">
          <div v-for="caseInfo in caseFieldsNotInSummary(variant)" :key="caseInfo.field">
            <span class="case-field">
              {{ caseInfo.field }}:
            </span>
            <span v-if="caseInfo.value.length > 0">
              {{ caseInfo.value.join(', ') }}
            </span>
          </div>
        </div>
        <PmiVariantSummaryCard :analysisName="name" :gene="gene" :variant="variant" />
        <details class="full-annotation">
          <summary>Show full annotation</summary>
          <PmiVariantAnnotationPanel
            :analysisName="name"
            :gene="gene"
            :variant="variant"
          />
        </details>
      </div>
    </div>
  </div>
</template>

<script>
import CopyToClipboard from '@/components/CopyToClipboard.vue';
import PmiVariantAnnotationPanel from '@/components/AnalysisView/PmiVariantAnnotationPanel.vue';
import PmiVariantSummaryCard from '@/components/AnalysisView/PmiVariantSummaryCard.vue';

export default {
  name: 'pmi-gene-box',
  emits: ['clipboard-copy'],
  components: {
    CopyToClipboard,
    PmiVariantAnnotationPanel,
    PmiVariantSummaryCard,
  },
  props: {
    name: {
      type: String,
    },
    gene: {
      type: String,
    },
    transcripts: {
      type: Array,
    },
    variants: {
      type: Array,
    },
  },
  data() {
    return {
      variantScores: {},
    };
  },
  mounted() {
    this.variants.forEach((variant) => {
      this.variantScores[variant.hgvs_variant] = this.getInitialVariantScore(variant);
    });
  },
  methods: {
    getBuild(build) {
      if (build == 'hg19') {
        return 'grch37';
      } else if (build == 'hg38') {
        return 'grch38';
      }
    },
    getCompleteHgvsVariantName(variant) {
      if (variant.p_dot) {
        return `${variant.hgvs_variant}(${variant.p_dot})`;
      }

      return variant.hgvs_variant;
    },
    variantToggleId(index, variant) {
      const variantId = variant.hgvs_variant.replaceAll(/[^a-zA-Z0-9]/g, '_');
      return `pmi_variant_${index}_${variantId}`;
    },
    getInitialVariantScore(variant) {
      const caseScore = (variant.case || []).find((caseInfo) => caseInfo.field === 'Score');
      if (!caseScore || !caseScore.value || caseScore.value.length === 0) {
        return 4;
      }

      const parsedScore = Number(caseScore.value[0]);
      if ([1, 2, 3, 4].includes(parsedScore)) {
        return parsedScore;
      }
      return 4;
    },
    getVariantScore(variant) {
      return this.variantScores[variant.hgvs_variant] || 4;
    },
    setVariantScore(variant, scoreValue) {
      const parsedScore = Number(scoreValue);
      this.variantScores[variant.hgvs_variant] = [1, 2, 3, 4].includes(parsedScore) ? parsedScore : 4;
    },
    caseFieldsNotInSummary(variant) {
      const skip = new Set(['Interpretation', 'Zygosity', 'Inheritance']);
      return (variant.case || []).filter((c) => !skip.has(c.field));
    },
  },
};
</script>

<style scoped>
.variant-container input[type="checkbox"] {
  display: none;
}

.variant-container input[type="checkbox"]:checked ~ .variant-content {
  display: none;
}

.variant-container input[type="checkbox"]:checked ~ .variant-name-line .collapsable-icon {
  transform: scaleY(-1);
}

.variant-container {
  width: 100%;
}

.variant-sub-section {
  margin-top: var(--p-10);
}

.variant-content {
  padding: var(--p-10) var(--p-12) var(--p-16);
}

.variant-name-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--p-3) var(--p-5);
  gap: var(--p-5);
}

.variant {
  font-weight: bold;
  display: inline-flex;
  align-items: center;
  gap: var(--p-6);
  color: var(--rosalution-purple-300);
}

.variant-controls {
  display: inline-flex;
  align-items: center;
  gap: var(--p-8);
}

.variant-score {
  display: inline-flex;
  align-items: center;
  gap: var(--p-2);
  margin-left: var(--p-24);
  font-size: 0.875rem;
  font-weight: 600;
  color: black;
}

.variant-score select {
  border: 1px solid var(--rosalution-grey-200);
  border-radius: 4px;
  padding: 0 var(--p-2);
  height: 1.5rem;
  background: white;
  color: black;
}

.copy-icon {
  padding-bottom: var(--p-1);
  color: var(--rosalution-purple-300);
}

.genomic-build {
  font-size: .875rem;
  font-weight: 600;
}

.variant-case-information {
  display: flex;
  gap: var(--p-10) var(--p-12);
  flex-wrap: wrap;
  margin: 0 0 var(--p-10);
  padding-bottom: var(--p-8);
  line-height: 1.5;
}

.case-field {
  font-weight: 600;
}

.collapsable-icon {
  color: var(--rosalution-grey-200);
  cursor: pointer;
}

.full-annotation {
  margin-top: var(--p-12);
  padding-top: var(--p-8);
}
</style>
