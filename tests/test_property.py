from ontologize.biocyc import get_session, get_parents
from ontologize.ontology import Ontology, get_ontology_data, build_ontology


def test_property():
    session = get_session()

    ontology = build_ontology(["ACETATE--COA-LIGASE-RXN"],
                              "Pathway",
                              property=[['PWY0-1313']],
                              org_id="GCF_000011965",
                              session=session)

    print(ontology.to_string(colors=True))


def main():
    test_property()


if __name__ == "__main__":
    main()
