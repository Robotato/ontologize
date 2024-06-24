from src.biocyc import get_session, get_parents
from src.ontology import Ontology, get_parents_dict, build_ontology

def test_parents(session):
    glc_parents = get_parents("GLC", "Compound", session=session)

    assert isinstance(glc_parents, list)


def test_build_ontology(session):
    # get_parents_dict(["GLC", "ACET"], "Compound", session=session)
    print(build_ontology(["GLC", "ACET"], "Compound", session=session))

def main():
    session = get_session()
    # test_parents(session)
    test_build_ontology(session)

if __name__ == "__main__":
    main()
