from ontologize.ontology import build_ontology

ont = build_ontology(objects=["EG10131", "EG10524", "EG11074"], schema_type="Gene", session=None)
print(ont.to_string(max_depth=3, include_leaves=False, colors=True))