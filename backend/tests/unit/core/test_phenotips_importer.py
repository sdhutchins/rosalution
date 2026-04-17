"""Tests importing the phenotips data"""
import pytest

from src.core.phenotips_importer import PhenotipsImporter

from ...test_utils import read_test_fixture


def test_import_genomic_unit_data_hgvs(phenotips_importer):
    """Tests the format_genomic_unit_data function"""
    data = {"transcript": "NM_001005484.1", "cdna": "c.1036C>T", "reference_genome": "GRCh37"}
    actual = phenotips_importer.import_genomic_unit_collection_data(data, "hgvs")
    assert actual['hgvs_variant'] == "NM_001005484.1:c.1036C>T"
    assert len(actual['transcripts']) == 0
    assert len(actual['annotations']) == 0


def test_import_genomic_unit_data_gene(phenotips_importer):
    """Tests the format_genomic_unit_data function"""
    data = {"gene": "BRCA1"}
    actual = phenotips_importer.import_genomic_unit_collection_data(data, "gene")
    assert actual == {"gene": "BRCA1", "gene_symbol": "BRCA1", "annotations": []}


def test_import_genomic_unit_data_incorrect_format(phenotips_importer):
    """Tests that a warning will be given if the incorrect format is given for the format_genomic_unit_data function"""
    data = {"fake-genomic_unit": "value"}
    with pytest.warns(UserWarning) as warn_record:
        actual = phenotips_importer.import_genomic_unit_collection_data(data, "fake-format")
        assert len(warn_record) == 1
        assert actual is None


def test_import_analysis_data(phenotips_importer, new_analysis_import_json):
    """Tests the import_analyses_data function"""

    variant_data = [{
        "inheritance": "maternal",
        "zygosity": "hemizygous",
        "interpretation": "variant_u_s",
        "transcript": "NM_001017111.3",
        "protein": "p.Gly55Val",
        "cdna": "c.164G>T",
        "reference_genome": "GRCh38",
        "gene": "VMA21",
    }]

    actual = phenotips_importer.import_analysis_data(
        new_analysis_import_json, variant_data, new_analysis_import_json["genes"]
    )
    assert actual["name"] == "CPAM0112"
    assert actual["genomic_units"] == [{
        "gene": "VMA21",
        "transcripts": [{"transcript": "NM_001017111.3"}],
        "variants": [{
            "hgvs_variant": "NM_001017111.3:c.164G>T",
            "c_dot": "c.164G>T",
            "p_dot": "p.Gly55Val",
            "build": "GRCh38",
            "case": [
                {"field": "Interpretation", "value": ["variant_u_s"]},
                {"field": "Zygosity", "value": ["hemizygous"]},
                {"field": "Inheritance", "value": ["maternal"]},
            ],
        }],
    }]


def test_import_analysis_data_non_pmi_uses_legacy_sections(phenotips_importer, new_analysis_import_json):
    """Non-PMI imports should preserve existing section patterns used by CPAM/LW workflows."""
    variant_data = [{
        "inheritance": "maternal",
        "zygosity": "hemizygous",
        "interpretation": "variant_u_s",
        "transcript": "NM_001017111.3",
        "protein": "p.Gly55Val",
        "cdna": "c.164G>T",
        "reference_genome": "GRCh38",
        "gene": "VMA21",
    }]

    actual = phenotips_importer.import_analysis_data(
        new_analysis_import_json, variant_data, new_analysis_import_json["genes"], "CPAM"
    )
    section_headers = [section["header"] for section in actual["sections"]]
    assert section_headers[0:3] == ["Brief", "Clinical History", "Pedigree"]
    assert "Family History" not in section_headers
    assert "HPO Terms" not in section_headers
    assert "Model Goals" in section_headers


def test_format_case_data(phenotips_importer):
    """Tests the format_case_data function"""
    variants = {
        "inheritance": "maternal",
        "zygosity": "hemizygous",
        "interpretation": "variant_u_s",
        "transcript": "NM_001017111.3",
        "cdna": "c.164G>T",
        "reference_genome": "GRCh38",
        "gene": "VMA21",
    }
    actual = phenotips_importer.format_case_data(variants)
    assert actual == [
        {"field": "Interpretation", "value": ["variant_u_s"]},
        {"field": "Zygosity", "value": ["hemizygous"]},
        {"field": "Inheritance", "value": ["maternal"]},
    ]


def test_extracting_hpo_terms(new_analysis_import_json):
    """Tests if the importer extracts the Phenotips HPO terms into the expected string format"""
    actual_extraction_string = PhenotipsImporter.extract_hpo_terms(new_analysis_import_json["features"])
    expected_extraction_string = (
        "HP:0000175: Cleft palate; HP:0000252: Microcephaly; "
        "HP:0000708: Behavioral abnormality; HP:0000750: Delayed speech and language development; "
        "HP:0001263: Global developmental delay; HP:0002719: Recurrent infections; HP:0004322: Short stature; "
        "HP:0008872: Feeding difficulties in infancy; HP:0410030: Cleft lip"
    )

    assert actual_extraction_string == expected_extraction_string


def test_import_phenotips_json(phenotips_importer, analysis_collection, new_analysis_import_json):
    """Tests the import_phenotips_json function"""
    analysis_collection.collection.find_one.return_value = None
    incoming_phenotips_json = new_analysis_import_json
    incoming_phenotips_json["external_id"] = "C-PAM12345"
    actual = phenotips_importer.import_phenotips_json(incoming_phenotips_json)
    assert actual["name"] == "CPAM12345"


def test_import_analysis_data_for_pmi_project_has_reduced_sections(phenotips_importer, new_analysis_import_json):
    """Tests PMI imports only include core case sections."""
    variant_data = [{
        "inheritance": "maternal",
        "zygosity": "hemizygous",
        "interpretation": "variant_u_s",
        "transcript": "NM_001017111.3",
        "protein": "p.Gly55Val",
        "cdna": "c.164G>T",
        "reference_genome": "GRCh38",
        "gene": "VMA21",
    }]

    actual = phenotips_importer.import_analysis_data(
        new_analysis_import_json, variant_data, new_analysis_import_json["genes"], "PMI"
    )
    assert [section["header"] for section in actual["sections"]] == [
        "Brief",
        "Clinical History",
        "Family History",
        "HPO Terms",
        "Pedigree",
    ]


def test_import_analysis_data_populates_pmi_brief_and_clinical_history(phenotips_importer, new_analysis_import_json):
    """Tests PMI-specific Brief and Clinical History mapping from import JSON."""
    incoming = dict(new_analysis_import_json)
    incoming["brief"] = {
        "nominator": ["PMI intake team"],
        "participant": ["LW002099"],
        "phenotype": ["Custom phenotype summary"],
        "acmg_classification": ["VUS"],
        "acmg_classification_criteria": ["PM2", "PP3"],
        "acmg_criteria_to_add": ["PS3"],
        "decision": ["Carry forward for review"],
    }
    incoming["clinical_history"] = {
        "clinical_diagnosis": ["Autonomic dysfunction"],
        "affected_individuals_identified": ["Proband"],
        "sequencing": ["WES"],
        "testing": ["Segregation review"],
        "systems": ["Neurologic; GI"],
        "additional_details": ["PMI custom notes"],
    }

    actual = phenotips_importer.import_analysis_data(incoming, [], incoming["genes"], "PMI")
    brief = next((section for section in actual["sections"] if section["header"] == "Brief"), None)
    clinical_history = next((section for section in actual["sections"] if section["header"] == "Clinical History"), None)

    assert brief is not None
    assert clinical_history is not None
    assert next(row for row in brief["content"] if row["field"] == "Nominator")["value"] == ["PMI intake team"]
    assert next(row for row in brief["content"] if row["field"] == "Participant")["value"] == ["LW002099"]
    assert next(row for row in brief["content"] if row["field"] == "Phenotype")["value"] == ["Custom phenotype summary"]
    assert next(row for row in brief["content"] if row["field"] == "ACMG Classification")["value"] == ["VUS"]
    assert next(row for row in brief["content"] if row["field"] == "Decision")["value"] == ["Carry forward for review"]
    assert next(row for row in clinical_history["content"] if row["field"] == "Clinical Diagnosis")["value"] == [
        "Autonomic dysfunction"
    ]
    assert next(
        row for row in clinical_history["content"] if row["field"] == "Additional Details"
    )["value"] == ["PMI custom notes"]


def test_import_analysis_data_populates_pmi_family_history(phenotips_importer, new_analysis_import_json):
    """Tests PMI Family History and Clinical History mapping from import JSON."""
    incoming = dict(new_analysis_import_json)
    incoming["clinical_history"] = {
        **incoming.get("clinical_history", {}),
        "clinical_updates": ["Timeline paragraph one"],
        "recent_diagnoses": ["Diagnosis A", "Diagnosis B"],
        "recent_symptoms": ["Symptom line"],
        "developmental_history": ["Early childhood narrative"],
        "laboratory_notes": ["Iron studies; IgG subclasses"],
    }
    incoming["family_history"] = {
        "family_diseases": ["Maternal history note"],
        "familial_hpo_terms": ["HP:0001250: familial example"],
    }

    actual = phenotips_importer.import_analysis_data(incoming, [], incoming["genes"], "PMI")
    family = next((section for section in actual["sections"] if section["header"] == "Family History"), None)
    clinical_history = next((section for section in actual["sections"] if section["header"] == "Clinical History"), None)
    assert family is not None
    assert next(row for row in clinical_history["content"] if row["field"] == "Clinical Updates")["value"] == [
        "Timeline paragraph one"
    ]
    assert next(row for row in family["content"] if row["field"] == "Family Diseases")["value"] == ["Maternal history note"]
    assert next(row for row in family["content"] if row["field"] == "Familial HPO terms")["value"] == [
        "HP:0001250: familial example"
    ]
    assert next(row for row in clinical_history["content"] if row["field"] == "Recent Diagnoses")["value"] == [
        "Diagnosis A",
        "Diagnosis B",
    ]
    assert next(row for row in clinical_history["content"] if row["field"] == "Laboratory Notes")["value"] == [
        "Iron studies; IgG subclasses"
    ]


def test_import_analysis_data_pmi_legacy_family_history_clinical_blocks(phenotips_importer, new_analysis_import_json):
    """Legacy JSON with recent_diagnoses etc. only under family_history still fills Clinical History."""
    incoming = dict(new_analysis_import_json)
    incoming["family_history"] = {
        "recent_diagnoses": ["Legacy Dx only in family_history"],
        "laboratory_notes": ["Legacy labs"],
    }

    actual = phenotips_importer.import_analysis_data(incoming, [], incoming["genes"], "PMI")
    clinical_history = next((section for section in actual["sections"] if section["header"] == "Clinical History"), None)
    assert next(row for row in clinical_history["content"] if row["field"] == "Recent Diagnoses")["value"] == [
        "Legacy Dx only in family_history"
    ]
    assert next(row for row in clinical_history["content"] if row["field"] == "Laboratory Notes")["value"] == ["Legacy labs"]


def test_import_analysis_data_pmi_legacy_clinical_updates_in_family_history(phenotips_importer, new_analysis_import_json):
    """Legacy JSON with clinical_updates only under family_history still fills Clinical History."""
    incoming = dict(new_analysis_import_json)
    incoming["family_history"] = {"clinical_updates": ["Updates only in family_history block"]}
    actual = phenotips_importer.import_analysis_data(incoming, [], incoming["genes"], "PMI")
    clinical_history = next((section for section in actual["sections"] if section["header"] == "Clinical History"), None)
    assert next(row for row in clinical_history["content"] if row["field"] == "Clinical Updates")["value"] == [
        "Updates only in family_history block"
    ]


def test_import_analysis_data_pmi_legacy_family_notes_maps_to_family_diseases(phenotips_importer, new_analysis_import_json):
    """Legacy family_history.family_notes still maps to Family Diseases."""
    incoming = dict(new_analysis_import_json)
    incoming["family_history"] = {"family_notes": ["Legacy family_notes line"]}
    actual = phenotips_importer.import_analysis_data(incoming, [], incoming["genes"], "PMI")
    family = next((section for section in actual["sections"] if section["header"] == "Family History"), None)
    assert next(row for row in family["content"] if row["field"] == "Family Diseases")["value"] == ["Legacy family_notes line"]


def test_import_analysis_data_pmi_legacy_hpo_terminology_maps_to_familial_hpo(phenotips_importer, new_analysis_import_json):
    """Legacy family_history.hpo_terminology still maps to Familial HPO terms."""
    incoming = dict(new_analysis_import_json)
    incoming["family_history"] = {"hpo_terminology": ["Legacy familial HPO line"]}
    actual = phenotips_importer.import_analysis_data(incoming, [], incoming["genes"], "PMI")
    family = next((section for section in actual["sections"] if section["header"] == "Family History"), None)
    assert next(row for row in family["content"] if row["field"] == "Familial HPO terms")["value"] == ["Legacy familial HPO line"]


def test_import_analysis_data_pmi_brief_hpo_terms_from_features_when_omitted(phenotips_importer, new_analysis_import_json):
    """Brief HPO Terms falls back to features when brief.hpo_terms is omitted."""
    incoming = dict(new_analysis_import_json)
    incoming["brief"] = {"phenotype": ["Clinical summary only"]}
    actual = phenotips_importer.import_analysis_data(incoming, [], incoming["genes"], "PMI")
    brief = next((section for section in actual["sections"] if section["header"] == "Brief"), None)
    assert next(row for row in brief["content"] if row["field"] == "Phenotype")["value"] == ["Clinical summary only"]
    hpo_row = next(row for row in brief["content"] if row["field"] == "HPO Terms")["value"]
    assert hpo_row and "HP:0000175" in hpo_row[0]


@pytest.fixture(name="phenotips_importer")
def fixture_phenotips_importer(analysis_collection, genomic_unit_collection):
    """Returns a PhenotipsImporter object"""
    return PhenotipsImporter(analysis_collection, genomic_unit_collection)


@pytest.fixture(name="new_analysis_import_json")
def fixture_phenotips_import():
    """Returns a phenotips json fixture"""
    return read_test_fixture("new-analysis-import.json")
