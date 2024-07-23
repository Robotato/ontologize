import pandas as pd
from pprint import pp

from ontologize.biocyc import get_session
from ontologize.ontology import get_ontology_data, build_ontology

def test_subgen():
    # data = pd.read_csv("tests/subgen.csv")
    # objects = data["Gene"].tolist()
    with open("tests/subgenerational_gene_ids.txt", "r") as f:
        objects = f.read().splitlines()

    session = get_session()
    # pp(get_parents_dict(objects, "Gene", session=session))

    print(build_ontology(objects, "Gene", session=session).to_string(max_depth=3, include_leaves=False, colors=True))


def test_html():
    session = get_session()
    ontology = build_ontology(["GLC", "ACET"], "Compound", session=session)
    # html = ontology.to_html(max_depth=3, include_leaves=False, colors=True)
    html = ontology.to_html()
    with open("tests/subgen.html", "w") as f:
        f.write(html)


def main():
    # test_subgen()
    test_html()

if __name__ == "__main__":
    main()
