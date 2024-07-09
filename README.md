# Setup

```console
python -m pip install ontologize
```

# Usage

## Command-Line Interface

Once exposed, `ontologize` exposes a runnable script, and can also be called as a module:

```console
ontologize <file> <schema_type> [flags]
python -m ontologize <file> <schema_type> [flags]
```

The required arguments are given as follows:

- `file`: Path to a `.csv`, `.tsv`, or `.xlsx` file with BioCyc object IDs to ontologize. By default, assumes a (header-less, if `.csv` or `.tsv`) first column containing the IDs to be ontologized. If a `.xlsx` file is given, then by default, IDs are assumed to be in the first sheet in the first column, treating the first entry as a header.

- `schema_type` : Type of the objects (or properties) to be ontologized in the [Biocyc Schema](https://biocyc.org/schema.shtml). For example, this might be `Gene`, `Pathway`, `Compound`, etc. 

> Note that `schema_type` uses the singular form of the class name!

### Example:


### Flags

- `-o <orgid>, --orgid <orgid>`: BioCyc organism ID, used to specify the organism-specific database within to search. [ECOLI](https://ecocyc.org/) by default.
- `-s <sheet_name>, --sheet <sheet_name>`: 
- [object column]
- [property column]
- max_depth
- show_leaves
- colors (True by default)

- graph options (not implemented)
- pkl options

--interactive (allows maintaining session)