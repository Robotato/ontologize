from dataclasses import dataclass

@dataclass
class OntologyNode:
    name: str
    frame_id: str
    count: int
    members: list[str]

class Ontology:
    def __init__(self) -> None:
        self.tree = {}


def build_ontology(objects):
    pass
