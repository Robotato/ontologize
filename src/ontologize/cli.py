import os
import argparse
import pandas as pd
from ontologize.ontology import build_ontology

HELP = {
    "file": "Path to a .csv, .tsv, or .xlsx file with BioCyc object IDs to ontologize."
            " By default, assumes a (header-less, if .csv or .tsv) first column containing"
            " the IDs to be ontologized. If a .xlsx file is given, then by default, IDs are"
            " assumed to be in the first sheet in the first column, treating the first entry as a header.",
    "schema_type": "Type of the objects (or properties) to be ontologized in the Biocyc Schema"
                   " (e.g., Gene, Pathway, Compound, etc.)",
    "sheet": "Name of the sheet in the .xlsx file containing the BioCyc IDs. Ignored if file is not a .xlsx file.",
    "objects": "Name of the column containing BioCyc IDs for the objects to ontologize. Requires a header row containing column names.",
    "property": "For a multi-column file, the name of the column containing BioCyc IDs for"
                " the property to ontologize. Requires a header row containing column names."
                " When using this option, the objects must also be specified using the -o option.",
    "database": "BioCyc organism ID, used to specify the organism-specific database within to search. ECOLI by default.",
    "depth": "Maximum depth of the ontology to print. No limit by default.",
    "leaves": "Whether to show leaf nodes, i.e., the ontologized objects themselves. Not shown by default.",
    "coloroff": "Turns off colorful printing."
}


def cli():
    parser = argparse.ArgumentParser(
        description='Build and print annotated ontology from a file containing a list of BioCyc IDs.')

    parser.add_argument('file', type=str, help=HELP["file"])
    parser.add_argument('schema_type', type=str, help=HELP['schema_type'])

    # Ontology-building/file options
    parser.add_argument('-s', '--sheet', type=str, help=HELP['sheet'])
    parser.add_argument('-o', '--objects', type=str, help=HELP['objects'])
    parser.add_argument('-p', '--property', type=str, help=HELP['property'])
    parser.add_argument('--database', type=str,
                        default='ECOLI', help=HELP['database'])

    # Ontology-printing options
    parser.add_argument('--depth', type=int, help=HELP['depth'])
    parser.add_argument('--leaves', action='store_true', help=HELP["leaves"])
    parser.add_argument('--coloroff', action='store_true', help=HELP['coloroff'])

    args = parser.parse_args()

    file = args.file
    schema_type = args.schema_type
    sheet_name = args.sheet
    objects_column = args.objects
    property_column = args.property
    org_id = args.database
    max_depth = args.depth
    include_leaves = args.leaves
    colors = not args.coloroff

    # Validate
    if property_column and not objects_column:
        raise ValueError(
            "If specifying a property column, you must also specify an objects column.")

    # Read the file
    dataframe = None
    _, ext = os.path.splitext(file)
    match (ext):
        case '.xlsx':
            data = pd.read_excel(file, sheet_name=sheet_name)
        case '.csv' | '.tsv':
            data = pd.read_csv(file,
                               sep=',' if ext == '.csv' else '\t',
                               header=(0
                                       if objects_column is not None or
                                       property_column is not None
                                       else None))
        case _:
            raise ValueError(
                f"Invalid file format ({ext}). Please provide a .csv, .tsv, or .xlsx file.")

    dataframe = (data
                 if objects_column is not None or
                 property_column is not None
                 else None)
    # Defaults to the first column
    objects = (dataframe[objects_column].tolist()
               if objects_column is not None
               else data.iloc[:, 0].tolist())
    property = (dataframe[property_column].tolist()
                if property_column is not None
                else None)

    ontology = build_ontology(
        objects, schema_type, property=property, dataframe=dataframe, org_id=org_id)
    print(ontology.to_string(max_depth=max_depth,
          include_leaves=include_leaves, colors=colors))


if __name__ == '__main__':
    cli()
