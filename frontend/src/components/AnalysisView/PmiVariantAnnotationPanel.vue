<template>
  <div v-if="renderReady" class="pmi-annotation-panel">
    <AnnotationSection
      v-for="(section, index) in rendering"
      :key="`${section.type}-${gene}-${variant.hgvs_variant}-${section.anchor}-${index}`"
      :header="sectionHeader(section.header)"
      v-bind="section.props"
      :id="`${section.anchor}-${index}`"
      :writePermissions="false"
    >
      <template #headerDatasets>
        <component
          v-for="(headerDatasetConfig, headerIndex) in section.header_datasets"
          :key="`${headerDatasetConfig.dataset}-${headerIndex}`"
          :is="datasetComponents[headerDatasetConfig.type]"
          :value="annotations[headerDatasetConfig.dataset]"
          v-bind="headerDatasetConfig.props"
        />
      </template>
      <template #default>
        <div v-for="(row, rowIndex) in section.rows" :key="`row-${rowIndex}`" :class="row.class" class="grid-row-span">
          <component
            v-for="(datasetConfig, datasetIndex) in row.datasets"
            :key="`${datasetConfig.dataset}-${datasetIndex}`"
            :is="datasetComponents[datasetConfig.type]"
            :dataSet="datasetConfig.dataset"
            :genomicType="datasetConfig.genomicType"
            v-bind="buildProps(datasetConfig)"
            :value="annotations[datasetConfig.dataset]"
          />
        </div>
      </template>
    </AnnotationSection>
  </div>
</template>

<script setup>
import {computed, onMounted, reactive} from 'vue';

import Analyses from '@/models/analyses.js';
import Annotations from '@/models/annotations.js';

import AnnotationSection from '@/components/AnnotationView/AnnotationSection.vue';
import CardDataset from '@/components/AnnotationView/CardDataset.vue';
import ClinvarDataset from '@/components/AnnotationView/ClinvarDataset.vue';
import IconLinkoutDataset from '@/components/AnnotationView/IconLinkoutDataset.vue';
import ImagesDataset from '@/components/AnnotationView/ImagesDataset.vue';
import ScoreDataset from '@/components/AnnotationView/ScoreDataset.vue';
import SetDataset from '@/components/AnnotationView/SetDataset.vue';
import SubheaderDataset from '@/components/AnnotationView/SubheaderDataset.vue';
import TagDataset from '@/components/AnnotationView/TagDataset.vue';
import TextDataset from '@/components/AnnotationView/TextDataset.vue';
import TranscriptDatasets from '@/components/AnnotationView/TranscriptDatasets.vue';

const props = defineProps({
  analysisName: {
    type: String,
    required: true,
  },
  gene: {
    type: String,
    required: true,
  },
  variant: {
    type: Object,
    required: true,
  },
});

const datasetComponents = {
  'text-dataset': TextDataset,
  'score-dataset': ScoreDataset,
  'images-dataset': ImagesDataset,
  'set-dataset': SetDataset,
  'transcript-datasets': TranscriptDatasets,
  'tag-dataset': TagDataset,
  'icon-linkout-dataset': IconLinkoutDataset,
  'clinvar-dataset': ClinvarDataset,
  'card-dataset': CardDataset,
  'subheader-dataset': SubheaderDataset,
};

const renderingLayout = reactive([]);
const annotations = reactive({});

const rendering = computed(() => {
  const pmiHeaders = ['gene', 'variant', 'protein'];
  return renderingLayout.filter((section) => pmiHeaders.includes(section.header));
});

const renderReady = computed(() => {
  return !(Object.keys(annotations).length === 0 || rendering.value.length === 0);
});

function sectionHeader(header) {
  if (header === 'gene') {
    return props.gene;
  }
  if (header === 'variant') {
    return props.variant.hgvs_variant;
  }
  if (header === 'protein') {
    return annotations.uniprot_id || 'Protein';
  }
  return header;
}

function buildProps(datasetConfig) {
  return {
    ...datasetConfig.props,
    ...(
      'extra_annotation' in datasetConfig ?
        {[datasetConfig.extra_annotation]: annotations[datasetConfig[datasetConfig.extra_annotation]]} : {}
    ),
  };
}

onMounted(async () => {
  renderingLayout.push(...await Analyses.getAnnotationConfiguration(props.analysisName));
  Object.assign(annotations, await Annotations.getAnnotations(props.analysisName, props.gene, props.variant.hgvs_variant));
});
</script>

<style scoped>
.pmi-annotation-panel {
  margin-top: var(--p-1);
}

.pmi-annotation-panel :deep(.dataset-container) {
  font-size: 0.875rem;
}

.pmi-annotation-panel :deep(.section-content) {
  padding-top: var(--p-1);
}

.pmi-annotation-panel :deep(.grid-row-horizontal) {
  gap: var(--p-4);
}

.pmi-annotation-panel :deep(.annotation-section-header-text) {
  font-size: 1rem;
}

.pmi-annotation-panel :deep(.text-value) {
  line-height: 1.35;
}
</style>

