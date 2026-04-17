"""Tests for Phenotips import models."""
from src.models.phenotips_json import BasePhenotips


def test_base_phenotips_preserves_pmi_case_fields_for_importer():
    """brief / clinical_history / family_history must survive validation so PMI import can populate sections."""
    payload = {
        "external_id": "LW002099",
        "variants": [],
        "genes": [],
        "features": [],
        "brief": {"nominator": ["Team"], "participant": ["LW002099"]},
        "clinical_history": {"clinical_diagnosis": ["Dx"]},
        "family_history": {"family_diseases": ["Maternal history"]},
    }
    model = BasePhenotips(**payload)
    dumped = model.model_dump()
    assert dumped["brief"]["nominator"] == ["Team"]
    assert dumped["clinical_history"]["clinical_diagnosis"] == ["Dx"]
    assert dumped["family_history"]["family_diseases"] == ["Maternal history"]
