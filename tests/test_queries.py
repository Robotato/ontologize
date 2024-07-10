from ontologize.biocyc import get_session, get_parents
from ontologize.ontology import Ontology, get_ontology_data, build_ontology

def test_parents(session):
    glc_parents = get_parents("GLC", "Compound", session=session)

    assert isinstance(glc_parents, list)


def test_build_ontology(session):
    # get_parents_dict(["GLC", "ACET"], "Compound", session=session)
    print(build_ontology(["GLC", "ACET"], "Compound", session=session).to_string(max_depth=None, colors=True))

def main():
    session = get_session()
    # test_parents(session)
    test_build_ontology(session)

if __name__ == "__main__":
    main()
