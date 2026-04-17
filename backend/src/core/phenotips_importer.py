"""
Class to support the importing of phenotips data
"""
import warnings


class PhenotipsImporter:
    """imports the incoming phenotips json data"""

    def __init__(self, analysis_collection, genomic_unit_collection):
        """Initializes with the Rosalution repositories analysis and genomic unit which wrap 'PyMongo'"""
        self.analysis_collection = analysis_collection
        self.genomic_unit_collection = genomic_unit_collection

    def import_phenotips_json(self, phenotips_json_data, project_name=None):
        """Imports the phenotips json data into the database"""

        phenotips_variants = []
        variant_annotations = [
            "inheritance", "zygosity", "interpretation", "transcript", "cdna", "reference_genome", "protein", "gene"
        ]

        for variant in phenotips_json_data["variants"]:
            variant_data = {}
            for annotation in variant_annotations:
                if annotation in variant:
                    variant_data[annotation] = variant[annotation]
            if 'gene' in variant_data:
                for gene in phenotips_json_data["genes"]:
                    if gene['id'] == variant_data['gene']:
                        variant_data['gene'] = gene['gene']

            phenotips_variants.append(variant_data)

        for gene in phenotips_json_data["genes"]:
            genomic_unit_data = self.import_genomic_unit_collection_data(gene, "gene")
            self.genomic_unit_collection.create_genomic_unit(genomic_unit_data)

        for variant in phenotips_variants:
            genomic_unit_data = self.import_genomic_unit_collection_data(variant, "hgvs")
            self.genomic_unit_collection.create_genomic_unit(genomic_unit_data)

        analysis_data = self.import_analysis_data(
            phenotips_json_data, phenotips_variants, phenotips_json_data["genes"], project_name
        )

        analysis_data['discussions'] = []
        analysis_data['attachments'] = []
        analysis_data['timeline'] = []
        analysis_data['project_id'] = ""
        return analysis_data

    @staticmethod
    def import_genomic_unit_collection_data(data, data_format):
        """Formats the genomic unit data from the phenotips.json file"""
        if data_format == "hgvs":
            genomic_data = {
                "hgvs_variant": str(data["transcript"] + ":" + data["cdna"]),
                "chromosome": "",
                "position": "",
                "reference": "",
                "alternate": "",
                "build": data['reference_genome'],
                "transcripts": [],
                "annotations": [],
            }
        elif data_format == "gene":
            genomic_data = {"gene_symbol": data['gene'], "gene": data['gene'], "annotations": []}
        else:
            warnings.warn("Invalid data format for import_genomic_unit_collection_data method", UserWarning)
            return None
        return genomic_data

    def import_analysis_data(self, phenotips_json_data, phenotips_variants, phenotips_genes, project_name=None):
        """Formats the analysis data from the phenotips.json file"""

        is_pmi_project = project_name == "PMI"
        sections = self.get_initial_case_sections(phenotips_json_data, is_pmi_project)

        analysis_data = {
            "name": str(phenotips_json_data["external_id"]).replace("-", ""), "description": "", "nominated_by": "",
            "genomic_units": [], "sections": sections
        }

        for phenotips_gene in phenotips_genes:
            analysis_unit = {
                "gene": phenotips_gene["gene"],
                "transcripts": [],
                "variants": [],
            }

            for phenotips_variant in phenotips_variants:
                if phenotips_variant['gene'] == phenotips_gene['gene']:
                    analysis_unit['variants'].append({
                        "hgvs_variant": str(phenotips_variant["transcript"] + ":" + phenotips_variant["cdna"]),
                        "c_dot": phenotips_variant["cdna"], "p_dot": phenotips_variant["protein"],
                        "build": str(phenotips_variant['reference_genome']),
                        "case": self.format_case_data(phenotips_variant)
                    })

                if 'transcript' in phenotips_variant:
                    new_transcript = {'transcript': phenotips_variant['transcript']}
                    if new_transcript not in analysis_unit['transcripts']:
                        analysis_unit['transcripts'].append(new_transcript)

            analysis_data['genomic_units'].append(analysis_unit)

        if is_pmi_project:
            self.populate_pmi_case_sections(analysis_data, phenotips_json_data)

        if not is_pmi_project:
            for genomic_unit in analysis_data['genomic_units']:
                if genomic_unit['gene']:
                    new_sections = [{
                        "header": str(genomic_unit["gene"] + " Gene To Phenotype"),
                        "attachment_field": str(genomic_unit["gene"] + " Gene To Phenotype"), "content": [
                            {
                                "type": "images-dataset", "field": str(genomic_unit["gene"] + " Gene To Phenotype"),
                                "value": []
                            },
                            {
                                "type": "section-text", "field": 'HPO Terms',
                                "value": [self.extract_hpo_terms(phenotips_json_data["features"])]
                            },
                        ]
                    }, {
                        "header": str(genomic_unit["gene"] + " Molecular Mechanism"), "content": [{
                            "type": "section-text", "field": str(genomic_unit["gene"] + " Molecular Mechanism"), "value": []
                        }]
                    }, {
                        "header": str(genomic_unit["gene"] + " Function"),
                        "attachment_field": str(genomic_unit["gene"] + " Function"), "content": [
                            {"type": "images-dataset", "field": str(genomic_unit["gene"] + " Function"), "value": []},
                        ]
                    }]
                    analysis_data['sections'].extend(new_sections)

            model_goals_section = {
                "header": 'Model Goals', "content": [
                    {"type": "section-text", "field": 'Model of Interest', "value": []},
                    {"type": "section-text", "field": 'Goals', "value": []},
                    {"type": "section-text", "field": 'Proposed Model/Project', "value": []},
                    {"type": "section-text", "field": 'Existing Collaborations', "value": []},
                    {"type": "section-text", "field": 'Existing Funding', "value": []},
                ]
            }
            analysis_data['sections'].append(model_goals_section)

        return analysis_data

    def get_initial_case_sections(self, phenotips_json_data, is_pmi_project):
        """Returns project-aware initial sections scaffold for a newly imported analysis."""
        brief_fields = [
            'Nominator',
            'Participant',
            'Phenotype',
            *(["HPO Terms"] if is_pmi_project else []),
            'ACMG Classification',
            'ACMG Classification Criteria',
            'ACMG Criteria To Add',
            'Decision',
        ]
        clinical_fields = [
            'Clinical Diagnosis',
            'Affected Individuals Identified',
            'Sequencing',
            'Testing',
            'Systems',
            *(["Clinical Updates", "Recent Diagnoses", "Recent Symptoms", "Developmental History", "Laboratory Notes"]
              if is_pmi_project else []),
            'Additional Details',
        ]

        sections = [{
            "header": 'Brief',
            "content": [self.section_text_row(field) for field in brief_fields],
        }, {
            "header": 'Clinical History',
            "content": [self.section_text_row(field) for field in clinical_fields],
        }]

        if is_pmi_project:
            sections.extend([{
                "header": 'Family History',
                "content": [self.section_text_row('Family Diseases'), self.section_text_row('Familial HPO terms')],
            }, {
                "header": 'HPO Terms',
                "content": [{
                    "type": "section-text",
                    "field": "HPO Terms",
                    "value": [self.extract_hpo_terms(phenotips_json_data["features"])],
                }],
            }])

        sections.append({
            "header": 'Pedigree',
            "attachment_field": "Pedigree",
            "content": [{"type": "images-dataset", "field": "Pedigree", "value": []}],
        })

        return sections

    @staticmethod
    def section_text_row(field_name):
        """Returns a section-text row scaffold."""
        return {"type": "section-text", "field": field_name, "value": []}

    @staticmethod
    def set_section_field_value(analysis_data, section_header, field_name, value):
        """Sets a specific field value in a section when it exists."""
        for section in analysis_data["sections"]:
            if section["header"] != section_header:
                continue
            for row in section["content"]:
                if row["field"] == field_name:
                    row["value"] = value
                    return

    @staticmethod
    def value_as_list(value):
        """Normalizes incoming values to a section-text array format."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None and str(item).strip() != ""]
        if isinstance(value, str):
            return [value] if value.strip() != "" else []
        return [str(value)]

    def populate_pmi_case_sections(self, analysis_data, phenotips_json_data):
        """Populates PMI Brief, Clinical History, and Family History from optional JSON fields."""
        brief = phenotips_json_data.get("brief", {})
        clinical_history = phenotips_json_data.get("clinical_history", {})

        if not isinstance(brief, dict):
            brief = {}
        if not isinstance(clinical_history, dict):
            clinical_history = {}

        participant = self.value_as_list(brief.get("participant", phenotips_json_data.get("external_id", "")))
        phenotype = self.value_as_list(brief.get("phenotype"))
        if brief.get("hpo_terms") is not None:
            hpo_terms = self.value_as_list(brief.get("hpo_terms"))
        else:
            raw_hpo = self.extract_hpo_terms(phenotips_json_data.get("features", []))
            hpo_terms = self.value_as_list(raw_hpo) if raw_hpo else []

        self.set_section_field_value(analysis_data, "Brief", "Nominator", self.value_as_list(brief.get("nominator")))
        self.set_section_field_value(analysis_data, "Brief", "Participant", participant)
        self.set_section_field_value(analysis_data, "Brief", "Phenotype", phenotype)
        self.set_section_field_value(analysis_data, "Brief", "HPO Terms", hpo_terms)
        self.set_section_field_value(
            analysis_data, "Brief", "ACMG Classification", self.value_as_list(brief.get("acmg_classification"))
        )
        self.set_section_field_value(
            analysis_data,
            "Brief",
            "ACMG Classification Criteria",
            self.value_as_list(brief.get("acmg_classification_criteria")),
        )
        self.set_section_field_value(
            analysis_data, "Brief", "ACMG Criteria To Add", self.value_as_list(brief.get("acmg_criteria_to_add"))
        )
        self.set_section_field_value(analysis_data, "Brief", "Decision", self.value_as_list(brief.get("decision")))

        self.set_section_field_value(
            analysis_data,
            "Clinical History",
            "Clinical Diagnosis",
            self.value_as_list(clinical_history.get("clinical_diagnosis")),
        )
        self.set_section_field_value(
            analysis_data,
            "Clinical History",
            "Affected Individuals Identified",
            self.value_as_list(clinical_history.get("affected_individuals_identified")),
        )
        self.set_section_field_value(
            analysis_data, "Clinical History", "Sequencing", self.value_as_list(clinical_history.get("sequencing"))
        )
        self.set_section_field_value(
            analysis_data, "Clinical History", "Testing", self.value_as_list(clinical_history.get("testing"))
        )
        self.set_section_field_value(
            analysis_data, "Clinical History", "Systems", self.value_as_list(clinical_history.get("systems"))
        )

        family_history = phenotips_json_data.get("family_history", {})
        if not isinstance(family_history, dict):
            family_history = {}

        def clinical_or_legacy_family(clinical_key, family_key):
            """Prefer clinical_history when the key is present; else family_history (legacy JSON layout)."""
            if clinical_key in clinical_history:
                return clinical_history.get(clinical_key)
            return family_history.get(family_key)

        self.set_section_field_value(
            analysis_data,
            "Clinical History",
            "Clinical Updates",
            self.value_as_list(clinical_or_legacy_family("clinical_updates", "clinical_updates")),
        )
        self.set_section_field_value(
            analysis_data,
            "Clinical History",
            "Recent Diagnoses",
            self.value_as_list(clinical_or_legacy_family("recent_diagnoses", "recent_diagnoses")),
        )
        self.set_section_field_value(
            analysis_data,
            "Clinical History",
            "Recent Symptoms",
            self.value_as_list(clinical_or_legacy_family("recent_symptoms", "recent_symptoms")),
        )
        self.set_section_field_value(
            analysis_data,
            "Clinical History",
            "Developmental History",
            self.value_as_list(clinical_or_legacy_family("developmental_history", "developmental_history")),
        )
        self.set_section_field_value(
            analysis_data,
            "Clinical History",
            "Laboratory Notes",
            self.value_as_list(clinical_or_legacy_family("laboratory_notes", "laboratory_notes")),
        )
        self.set_section_field_value(
            analysis_data,
            "Clinical History",
            "Additional Details",
            self.value_as_list(clinical_history.get("additional_details")),
        )

        family_diseases = family_history.get("family_diseases")
        if family_diseases is None:
            family_diseases = family_history.get("family_notes")
        self.set_section_field_value(
            analysis_data,
            "Family History",
            "Family Diseases",
            self.value_as_list(family_diseases),
        )
        familial_hpo = family_history.get("familial_hpo_terms")
        if familial_hpo is None:
            familial_hpo = family_history.get("hpo_terminology")
        self.set_section_field_value(
            analysis_data,
            "Family History",
            "Familial HPO terms",
            self.value_as_list(familial_hpo),
        )

    @staticmethod
    def format_case_data(variant_data):
        """Formats the case data from the phenotips.json file using the variant data"""
        case_data = []
        genomic_unit_case_annotations = {
            "interpretation": "Interpretation",
            "zygosity": "Zygosity",
            "inheritance": "Inheritance",
        }

        for annotation in genomic_unit_case_annotations.items():
            phenotips_json_attribute = annotation[0]
            case_annotation = annotation[1]

            if variant_data[phenotips_json_attribute]:
                case_data.append({
                    "field": case_annotation,
                    "value": [str(variant_data[phenotips_json_attribute])],
                })
        return case_data

    @staticmethod
    def extract_hpo_terms(phenotips_json_features):
        """Extracts the HPO terms from the Phenotips JSON 'features' list and returns it as a string"""
        return '; '.join([f"{term['id']}: {term['label']}" for term in phenotips_json_features]).replace('\n', '')
