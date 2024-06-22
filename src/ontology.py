from collections import defaultdict
from pprint import pformat
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from src.biocyc import get_session, get_parents
from src.defaults import ECOLI

@dataclass
class OntologyNode:
    name: str
    frame_id: str
    members: list[str]

    @property
    def count(self):
        return len(self.members)


class Ontology:
    def __init__(self) -> None:
        self.tree = defaultdict(dict)
    
    def add_node_to_parents(self, node_id, parent_ids):
        if node_id in self:
            children_subtree = self.tree
        else:
            node = OntologyNode(node_id, node_id, [])

            for parent in parent_ids:
                if parent in self:
                    self.tree[parent].members.append(node_id)
                    self.tree[parent][node] = {}

    def __iter__(self):
        """Iterate over the tree in a depth-first manner."""
        def _iter(node_id):
            yield node_id
            for child_id in self.tree[node_id].members:
                yield from _iter(child_id)
    
        for node_id in self.tree:
            yield from _iter(node_id)
    
    def __contains__(self, node_id):
        for node in self:
            if node.frame_id == node_id:
                return True
        return False

    def __str__(self) -> str:
        return pformat(self.tree)
    
    def __repr__(self) -> str:
        return str(self)


def get_parents_dict(objects, object_type, org_id=ECOLI, session=None):
    # Collect parents of each object
    orphans = set(objects)
    object_to_parents = defaultdict(list, {obj : [] for obj in objects})
    
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
                    future = executor.submit(get_parents, obj, object_type, org_id, session)
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


def build_ontology(objects, object_type, org_id=ECOLI, session = None)
    # Get parents of each object
    parents_dict = get_parents_dict(objects, object_type, org_id=org_id, session=session)
    
    # Create ontology
    ontology = Ontology()
    
    # Create root nodes
    roots = [obj for obj, parents in parents_dict.items() if len(parents) == 0]
    for root in roots:
        ontology.tree[root] = OntologyNode(root, root, [])

    # Add remaining nodes
    remaining = set(objects) - set(roots)
    while len(remaining) > 0:
        for obj in remaining:
            parents = parents_dict[obj]

            for parent in parents:
                if parent in ontology.tree:
                    ontology.tree[parent].members.append(obj)
                    ontology.tree[parent][]

    return ontology
