import networkx as nx
from collections import defaultdict
from pprint import pformat
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.biocyc import get_session, get_parents
from src.defaults import ECOLI


class Ontology:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_node(self, node, parents=None):
        self.graph.add_node(node)

    def __str__(self) -> str:
        """Returns a string representation of the ontology,
        traversing the tree in depth-first order.

        Returns:
            str: _description_
        """
        result = ""

        def str_iter(node, depth=0, prefix=""):
            visited = {node}

            node_members = self.graph.nodes[node].get("members", [])
            memberstring = (", ".join(node_members)
                            if len(node_members) <= 5
                            else len(node_members))
            result = f"{prefix}{node} {{{memberstring}}}\n"
            children = list(self.graph.successors(node))
            for i, child in enumerate(children):
                # pref = (" " * (depth + 1)
                #         if i < len(children) - 1
                #         else " " * (depth + 1) + "└─ ")
                pref = prefix.replace("└", " ").replace("├", "│") + ("└" if i == len(children) - 1 else "├")
                _visited, _result = str_iter(child,
                                             depth=depth+1,
                                             prefix=pref)
                visited.update(_visited)
                result += _result
            return visited, result

        remaining = list(nx.topological_sort(self.graph))
        while len(remaining) > 0:
            visited, substring = str_iter(remaining[0])
            remaining = [node for node in remaining if node not in visited]
            result += substring

        return result

    # def __repr__(self) -> str:
    #     return str(self)


def get_parents_dict(objects, object_type, org_id=ECOLI, session=None):
    # Collect parents of each object
    orphans = set(objects)
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
                        get_parents, obj, object_type, org_id, session)
                    futures.add(future)
                    future_to_obj[future] = obj

                # Collect results
                for future in as_completed(futures):
                    # Get parents and object id
                    parents = future.result()
                    obj = future_to_obj[future]

                    # Remove object from orphans
                    orphans.remove(obj)

                    # Store parents of object
                    for parent in parents:
                        parent_id = parent[object_type]["@frameid"]

                        # Add parent to object_to_parents
                        object_to_parents[obj].append(parent_id)

                        # Add parent to orphans if it is not already in object_to_parents
                        if parent_id not in object_to_parents:
                            orphans.add(parent_id)
                    pbar.update(1)

    return object_to_parents


def build_ontology(objects, object_type, org_id=ECOLI, session=None):
    # Get parents of each object
    parents_dict = get_parents_dict(
        objects, object_type, org_id=org_id, session=session)

    # Create ontology
    ontology = Ontology()

    def add_iter(obj, nodes, to=None):
        if to is None:
            to = obj

        for node in nodes:
            # Add node if it doesn't exist, and add object to members
            if node not in ontology.graph.nodes:
                ontology.graph.add_node(node, members={obj})
            else:
                ontology.graph.nodes[node]["members"].add(obj)

            # Create edge to connect node to object
            ontology.graph.add_edge(node, to)
            add_iter(obj, parents_dict[node], to=node)

    for obj in objects:
        add_iter(obj, parents_dict[obj])

    return ontology
