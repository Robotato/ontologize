import pandas as pd
from pprint import pp

from src.biocyc import get_session
from src.ontology import get_parents_dict, build_ontology

def test_subgen():
    data = pd.read_csv("tests/subgen.csv")
    objects = data["Gene"].tolist()

    session = get_session()
    # pp(get_parents_dict(objects, "Gene", session=session))

    print(build_ontology(objects, "Gene", session=session))


def main():
    test_subgen()

if __name__ == "__main__":
    main()