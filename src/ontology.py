import requests
import networkx as nx
from collections import defaultdict
from pprint import pformat
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.biocyc import get_parents_and_common_name, get_session, get_parents
from src.defaults import ECOLI


class bcolors:
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


class Ontology:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self, max_depth=None, include_leaves=True, colors=False) -> str:
        """Returns a string representation of the ontology,
        traversing the tree in depth-first order.

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
                COLORSTART = bcolors.DEPTH_COLORS[depth % len(
                    bcolors.DEPTH_COLORS)] if not is_leaf else bcolors.LEAF_COLOR
                COLOREND = bcolors.ENDC
            if len(prefix) > 0:
                prefix = prefix[:-1] + COLORSTART + prefix[-1] + COLOREND

            # Add node to result if max_depth is not reached, and
            # either the node is not a leaf or leaves are included
            # (still need to visit children to avoid re-visiting them later).
            if depth <= max_depth and ((is_leaf and include_leaves) or not is_leaf):
                result = f"{prefix}{COLORSTART}{name} [{node}]{COLOREND} {{{memberstring}}}\n"
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


def get_ontology_data(objects, object_type, org_id=ECOLI, session=None):
    # Collect common name, parents of each object
    orphans = set(objects)
    common_names = {}
    object_to_parents = defaultdict(list, {obj: [] for obj in objects})

    # Create session
    # TODO: safer to get username and password, and use those to create one session per thread
    session = get_session() if session is None else session

    while len(orphans) > 0:
        # Show progress bar
        with tqdm(total=len(orphans)) as pbar:

            # Get parents in parallel so as not to waste time
            with ThreadPoolExecutor() as executor:

                # Create futures for each orphaned object,
                # keeping track of which object id they correspond to
                futures = set()
                future_to_obj = {}
                for obj in orphans:
                    future = executor.submit(
                        get_parents_and_common_name, obj, object_type, org_id, session)
                    futures.add(future)
                    future_to_obj[future] = obj

                # Collect results
                for future in as_completed(futures):
                    try:
                        # Get parents and object id
                        parents, common_name = future.result()
                    except requests.exceptions.RequestException:
                        # If request fails, skip this object
                        parents = []
                        common_name = future_to_obj[future]

                    obj = future_to_obj[future]

                    # Remove object from orphans
                    orphans.remove(obj)

                    # Store common name of object
                    common_names[obj] = common_name

                    # Store parents of object
                    for parent in parents:
                        parent_id = parent[object_type]["@frameid"]

                        # Add parent to object_to_parents
                        object_to_parents[obj].append(parent_id)

                        # Add parent to orphans if it is not already in object_to_parents
                        if parent_id not in object_to_parents:
                            orphans.add(parent_id)
                    pbar.update(1)

    return common_names, object_to_parents


def build_ontology(objects, object_type, org_id=ECOLI, session=None):
    # Get parents of each object
    common_names, parents_dict = get_ontology_data(
        objects, object_type, org_id=org_id, session=session)

    # Create ontology
    ontology = Ontology()

    def add_iter(obj, nodes, to=None):
        if to is None:
            to = obj

        for node in nodes:
            # Add node if it doesn't exist, and add object to members
            if node not in ontology.graph.nodes:
                ontology.graph.add_node(
                    node, members={obj}, common_name=common_names[node])
            else:
                ontology.graph.nodes[node]["members"].add(obj)

            # Create edge to connect node to object
            ontology.graph.add_edge(node, to)
            add_iter(obj, parents_dict[node], to=node)

    for obj in objects:
        add_iter(obj, parents_dict[obj])

    return ontology
