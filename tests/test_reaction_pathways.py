import pandas as pd
from pprint import pp

from ontologize.biocyc import get_session
from ontologize.ontology import get_ontology_data, build_ontology


def test_reaction_pathways():
    session = get_session()
    # data = pd.read_excel("tests/escher_diff_pathways.xlsx")

    # # Filter to good matches
    # data = data[data["Score"] >= 0.5]

    # # Split into datasets for up in glucose and up in acetate
    # up_in_glucose = data[data["log2_fold"] < 0]
    # up_in_acetate = data[data["log2_fold"] > 0]

    # session = get_session()
    # # pp(get_parents_dict(objects, "Gene", session=session))
    # print ("Up in Acetate ======================================================================")
    # ontology = build_ontology(up_in_acetate["BioCyc ID (Best match)"].to_list(),
    #                           "Pathway",
    #                           property=[eval(p)
    #                                     for p in up_in_acetate["Pathways (Best Match)"]],
    #                           org_id="ECOLI",
    #                           session=session)
    # print(ontology.to_string(max_depth=3, include_leaves=False, colors=True))

    # print("Up in Glucose ======================================================================")
    # ontology = build_ontology(up_in_glucose["BioCyc ID (Best match)"].to_list(),
    #                           "Pathway",
    #                           property=[eval(p)
    #                                     for p in up_in_glucose["Pathways (Best Match)"]],
    #                           org_id="ECOLI",
    #                           session=session)
    # print(ontology.to_string(max_depth=3, include_leaves=False, colors=True))

    data = pd.read_excel("tests/escher_diff_pathways.xlsx",
                         sheet_name="R pom differences")
    data["Pathways"] = [eval(p) for p in data["Pathways"]]

    up_in_glucose_rpom = data[data["log2fold"] < 0]
    up_in_acetate_rpom = data[data["log2fold"] > 0]

    print("Up in Acetate R pom ======================================================================")
    ontology = build_ontology("ID",
                              "Pathway",
                              property="Pathways",
                              dataframe=up_in_acetate_rpom,
                              org_id="GCF_000011965",
                              session=session,)
    print(ontology.to_string(max_depth=3, include_leaves=False, colors=True))

    print("Up in Glucose R pom ======================================================================")

    ontology = build_ontology("ID",
                              "Pathway",
                              property="Pathways",
                              dataframe=up_in_glucose_rpom,
                              org_id="GCF_000011965",
                              session=session)
    print(ontology.to_string(max_depth=3, include_leaves=False, colors=True))


def main():
    test_reaction_pathways()


if __name__ == "__main__":
    main()
