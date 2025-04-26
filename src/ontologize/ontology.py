import warnings

from typing import Optional
from xml.dom.minidom import getDOMImplementation, Document

import pandas as pd
import requests
import networkx as nx
from collections import defaultdict
from pprint import pformat
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from ontologize.biocyc import SchemaError, get_parents_and_common_name, get_session, get_parents
from ontologize.defaults import ECOLI


class ShellColors:
    DEPTH_COLORS = [
        '\033[1;91m',  # bold red
        '\033[1;95m',  # bold magenta
        '\033[1;92m',  # bold green
        '\033[1;96m',  # bold cyan
        '\033[1;94m',  # bold blue
    ]
    LEAF_COLOR = '\033[97m'  # white
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class HTMLColors:
    DEPTH_COLORS = [
        "#F4C2C2",  # 'Tea rose',
        "#E6E6FA",  # 'Lavender',
        "#F0FFF0",  # 'Honeydew',
        "#E0FFFF",  # 'Light cyan',
        "#ADD8E6",  # 'Light blue',
    ]
    LEAF_COLOR = '#000000'  # black


class Ontology:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self, max_depth=None, include_leaves=True, colors=False) -> str:
        """Returns a string representation of the ontology,
        traversing the DAG in depth-first order.

        Returns:
            str: _description_
        """
        result = ""
        if max_depth is None:
            max_depth = float("inf")

        # Define recursive function to traverse DAG in depth-first order,
        # starting from a given node
        def str_iter(node, depth=0, prefix=""):
            # Keep track of nodes visited, so outer function does not
            # revisit them as root of some tree
            visited = {node}

            # Check if this is a leaf
            is_leaf = len(list(self.graph.successors(node))) == 0

            # Get common name
            name = self.graph.nodes[node].get("common_name", node)

            # Build formatting for node
            node_members = self.graph.nodes[node].get("members", [])
            memberstring = (", ".join(node_members)
                            if len(node_members) <= 5
                            else f"{len(node_members)} members")

            # Build color formatting
            COLORSTART, COLOREND = "", ""
            if colors:
                COLORSTART = ShellColors.DEPTH_COLORS[depth % len(
                    ShellColors.DEPTH_COLORS)] if not is_leaf else ShellColors.LEAF_COLOR
                COLOREND = ShellColors.ENDC
            if len(prefix) > 0:
                prefix = prefix[:-1] + COLORSTART + prefix[-1] + COLOREND

            # Add node to result if max_depth is not reached, and
            # either the node is not a leaf or leaves are included
            # (still need to visit children to avoid re-visiting them later).
            if depth <= max_depth and ((is_leaf and include_leaves) or not is_leaf):
                result = (f"{prefix}{COLORSTART}{name}"
                          f" [{node}]{COLOREND} {{{memberstring}}}\n")
            else:
                result = ""

            # Recursively traverse children
            children = list(self.graph.successors(node))
            for i, child in enumerate(children):
                pref = prefix.replace("└", " ").replace(
                    "├", "│") + ("└" if i == len(children) - 1 else "├")
                _visited, _result = str_iter(child,
                                             depth=depth+1,
                                             prefix=pref)
                visited.update(_visited)
                result += _result

            return visited, result

        # Traverse DAG starting from roots
        remaining = list(nx.topological_sort(self.graph))
        while len(remaining) > 0:
            visited, substring = str_iter(remaining[0])
            remaining = [node for node in remaining if node not in visited]
            result += substring

        return result

    def to_html(self) -> str:
        """Returns an HTML representation of the ontology,
        traversing the DAG in depth-first order.

        Returns:
            str: _description_
        """
        # Create HTML document
        impl = getDOMImplementation()
        dt = impl.createDocumentType(
            "html",
            "-//W3C//DTD XHTML 1.0 Strict//EN",
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd",
        )
        dom = impl.createDocument("http://www.w3.org/1999/xhtml", "html", dt)
        html = dom.documentElement

        # Add head
        head = dom.createElement("head")
        html.appendChild(head)

        # Add style
        style = dom.createElement("style")
        style_str = """
        details {
            padding: 10px;
            border: 5px solid #f7f7f7;
            border-radius: 3px;
        }
        """
        style_str += "\n".join([f'''
            .depth_{depth} {{
                background-color: {color};
            }}'''
            for depth, color in enumerate(HTMLColors.DEPTH_COLORS)])
        style.appendChild(dom.createTextNode(style_str))
        head.appendChild(style)

        # Traverse the nodes in depth-first order,
        # starting from the roots

        def html_iter(node, parent, depth=0):
            # Keep track of nodes visited, so outer function does not
            # revisit them as root of some tree
            visited = {node}

            # Get common name
            name = self.graph.nodes[node].get("common_name", node)

            # Build formatting for node
            node_members = self.graph.nodes[node].get("members", [])
            memberstring = (", ".join(node_members)
                            if len(node_members) <= 5
                            else f"{len(node_members)} members")

            # Create HTML element for node
            node_elem = dom.createElement("details")
            node_elem.setAttribute("open", "open")
            summary = dom.createElement("summary")
            summary.appendChild(dom.createTextNode(
                f"{name} {{{memberstring}}}"))
            summary.setAttribute(
                "class", f"depth_{depth % len(HTMLColors.DEPTH_COLORS)}")
            node_elem.appendChild(summary)

            parent.appendChild(node_elem)

            # Recursively traverse children
            children = list(self.graph.successors(node))
            for child in children:
                visited.update(html_iter(child, node_elem, depth=depth+1))

            return visited

        # Create HTML element for ontology
        ontology_elem = dom.createElement("div")
        ontology_elem.setAttribute("id", "ontology")
        html.appendChild(ontology_elem)

        # Traverse DAG starting from roots
        remaining = list(nx.topological_sort(self.graph))
        while len(remaining) > 0:
            visited = html_iter(remaining[0], ontology_elem)
            remaining = [node for node in remaining if node not in visited]

        return dom.toxml()


def get_ontology_data(objects, schema_type, org_id=ECOLI, session=None, show_progress=True):
    # Collect common name, parents of each object
    orphans = set(objects)
    common_names = {}
    object_to_parents = defaultdict(list, {obj: [] for obj in objects})

    # Create session
    # TODO: safer to get username and password, and use those to create one session per thread
    session = get_session() if session is None else session

    while len(orphans) > 0:

        # Show progress bar
        if show_progress:
            pbar = tqdm(total=len(orphans))
        
        # Get parents in parallel so as not to waste time
        with ThreadPoolExecutor() as executor:

            # Create futures for each orphaned object,
            # keeping track of which object id they correspond to
            futures = set()
            future_to_obj = {}
            for obj in orphans:
                future = executor.submit(
                    get_parents_and_common_name, obj, schema_type, org_id, session)
                futures.add(future)
                future_to_obj[future] = obj

            # Collect results
            for future in as_completed(futures):
                try:
                    # Get parents and object id
                    parents, common_name = future.result()
                except requests.exceptions.RequestException:
                    # If request fails, skip this object
                    warnings.warn(
                        f"Request failed for object {future_to_obj[future]}. Skipping.")
                    parents = []
                    common_name = future_to_obj[future]
                except SchemaError:
                    # If object does not match schema, skip this object
                    # TODO: store result as child of a Schema Error node
                    warnings.warn(
                        f"Object {future_to_obj[future]} does not match schema {schema_type}. Skipping.")
                    parents = []
                    common_name = future_to_obj[future]
                except Exception as e:
                    # If any other error occurs, raise it indicating which object caused it
                    raise Exception(f"Error for object {future_to_obj[future]}") from e  # nopep8

                obj = future_to_obj[future]

                # Remove object from orphans
                orphans.remove(obj)

                # Store common name of object
                common_names[obj] = common_name

                # Store parents of object
                for parent in parents:
                    parent_id = parent[schema_type]["@frameid"]

                    # Add parent to object_to_parents
                    object_to_parents[obj].append(parent_id)

                    # Add parent to orphans if it is not already in object_to_parents
                    if parent_id not in object_to_parents:
                        orphans.add(parent_id)

                # Update progress bar
                if show_progress:
                    pbar.update(1)
            
            # Close progress bar
            if show_progress:
                pbar.close()

    return common_names, object_to_parents


def build_ontology(objects: (list[str] | str),
                   schema_type: str,
                   property: Optional[str | list[str | list[str]]] = None,
                   dataframe: Optional[pd.DataFrame] = None,
                   org_id: str = ECOLI,
                   session: Optional[requests.Session] = None,
                   show_progress : bool = True) -> Ontology:
    """Build an ontology from a list of objects, where each object is connected to its parents according to
    the MultiFun ontology.

    Args:
        objects (list[str] | str): List of BioCyc object IDs for the objects to ontologize, or, if dataframe is provided, the column name containing the object IDs.
        schema_type (str): Type of the objects  to be ontologized in the BioCyc schema (e.g. "Reaction", "Gene", "Compound").
            NOTE: If `property` is supplied, this is the type of the property.
        property (str | list[list[str]], optional): Often, one wishes to ontologize objects based on some property, rather than the objects themselves.
            For example, one may wish to ontologize reactions based on the pathways they are part of. In this case, the property could be supplied as a list of the
            same length as `objects`, where each element is a list of (BioCyc IDs of) pathways that the corresponding reaction is part of. Alternatively, if
            the `dataframe` argument is supplied, this can be the column name containing the property. If `None` (the default), the objects themselves are ontologized.
        dataframe (pd.DataFrame, optional): Pandas DataFrame with columns for objects IDs (and optionally, properties) to ontologize.
            If provided, `objects` and `property` must be strings corresponding to the name of a column (or possible `None` in the case of `property`).
            Defaults to `None`.
        org_id (str, optional): BioCyc organism ID. Defaults to ECOLI.
        session (requests.Session, optional): BioCyc session to use. Defaults to None.
        show_progress (bool, optional): Whether to show progress bars. Defaults to True.

    Returns:
        Ontology: ontology object (access graph with ontology.graph).
    """
    # If property not supplied, set default to objects
    if property is None:
        property = [[obj] for obj in objects]

    # If dataframe is provided, get objects and property from dataframe
    # (need to be column names)
    if dataframe is not None:
        # Get objects list from dataframe
        if not isinstance(objects, str):
            raise ValueError(
                "If dataframe is provided, objects must be a column name.")
        objects = dataframe[objects].tolist()

        # Get property list from dataframe (or default to objects)
        if property is None:
            property = [[obj] for obj in objects]
        elif isinstance(property, str):
            property = dataframe[property].tolist()
        else:
            raise ValueError(
                "If dataframe is provided, property must be a column name.")

    # Flatten property list
    flat_property = [item for sublist in property for item in sublist]

    # Get parents of each object
    common_names, parents_dict = get_ontology_data(
        set(flat_property), schema_type, org_id=org_id, session=session, show_progress=show_progress)

    # Create ontology
    ontology = Ontology()

    # Recursive function to add objects to ontology
    def add_iter(obj, parents, label=None, child=None):
        if child is None:
            child = obj
        if label is None:
            label = obj

        for node in parents:
            # Add node if it doesn't exist, and add object to members
            if node not in ontology.graph.nodes:
                ontology.graph.add_node(
                    node, members={label}, common_name=common_names[node])
            else:
                ontology.graph.nodes[node]["members"].add(label)

            # Connect child to parent
            if child not in ontology.graph.nodes:
                ontology.graph.add_node(
                    child, members={label}, common_name=common_names[child])
            ontology.graph.add_edge(node, child)

            # Recurse to parents of node
            add_iter(obj, parents_dict[node], label=label, child=node)

    for obj, prop in zip(objects, property):
        if not isinstance(prop, list):
            prop = [prop]
        for p in prop:
            add_iter(p, parents_dict[p], label=obj)

    return ontology
