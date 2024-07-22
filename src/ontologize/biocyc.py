import requests
import xmltodict
import getpass

from ontologize.defaults import ECOLI


class SchemaError(Exception):
    pass


def get_session(user=None, password=None, retries=3):
    # Create session
    s = requests.Session()

    # Login
    failed = True
    while failed and retries > 0:
        # Get login credentials if not provided
        if user is None:
            user = input("Enter your BioCyc username: ")
        if password is None:
            password = getpass.getpass("Enter your BioCyc password: ")

        # Post login credentials
        r = s.post("https://websvc.biocyc.org/credentials/login/",
                   data={"email": user, "password": password})

        # Check if login was successful
        if r.status_code == 200:
            failed = False
        else:
            retries -= 1
            user = None
            password = None
            print("Login failed. Please try again.")

    if failed:
        raise Exception("Login failed, max retries exceeded.")

    return s


def get_parents(object_id: str, object_type: str, org_id: str = ECOLI, session=None):
    """Get the parents of the given object in the given organism.

    Args:
        object_id (str): Object for which to retrieve the parents.
        object_type (str) : Type of the object (Gene, Compound, etc.)
        org_id (str, optional): Organism id. Defaults to ECOLI.

    Returns:
        list[dict]: List of parents. Parent information is returned as raw dict form.
    """

    # Create session
    s = session if session is not None else get_session()

    # Get parents
    r = s.get(
        f"https://websvc.biocyc.org/getxml?{org_id}:{object_id}&detail=low")

    # Check if request was successful
    if r.status_code != 200:
        raise Exception("Request failed")

    o = xmltodict.parse(r.content)
    parents = o["ptools-xml"][object_type].get("parent", [])
    if isinstance(parents, dict):
        parents = [parents]

    return parents


def get_parents_and_common_name(object_id: str, object_type: str, org_id: str = ECOLI, session=None):
    """Get the parents and the common name of the given object in the given organism.
    Defined as one function to save on requests.

    Args:
        object_id (str): Object for which to retrieve the parents.
        object_type (str) : Type of the object (Gene, Compound, etc.)
        org_id (str, optional): Organism id. Defaults to ECOLI.

    Returns:
        tuple[list[dict], str]: List of parents and the common name of the object. Parent information is returned as raw dict form.
    """

    # Create session
    s = session if session is not None else get_session()

    # Get parents
    r = s.get(
        f"https://websvc.biocyc.org/getxml?{org_id}:{object_id}&detail=low")

    # Check if request was successful
    if r.status_code != 200:
        raise requests.HTTPError(f"Request failed (status {r.status_code}).")

    o = xmltodict.parse(r.content)["ptools-xml"]

    if object_type not in o:
        raise SchemaError(f"{object_id} does not match schema_type {object_type}.")

    # Get common name if it exists, else use object id
    common_name = o[object_type].get(
        "common-name", {}).get("#text", object_id)

    # Get parents
    parents = o[object_type].get("parent", [])
    if isinstance(parents, dict):
        parents = [parents]

    return parents, common_name


def genes_of_reaction(reaction, orgid=ECOLI, session=None):
    # Use session if provided
    s = session if session is not None else get_session()

    # Request genes of reaction
    r = s.get(
        f"https://websvc.biocyc.org/apixml?fn=genes-of-reaction&id={orgid}:{reaction}&detail=none")
    if r.status_code == 404:
        raise Exception("Reaction not found")

    # Clean up response
    genes = xmltodict.parse(r.text)["ptools-xml"].get("Gene", [])
    if isinstance(genes, dict):
        genes = [genes]
    genes = [gene["@frameid"] for gene in genes]

    return genes


def pathways_of_reactions(reactions, orgid=ECOLI, session=None):
    # Use session if provided
    s = session if session is not None else get_session()

    # For some inexplicable reason, contrary to the Pathway Tools Schema,
    # there is no "in-pathway" slot on reactions. Our options are to either
    # get the genes of the reaction and then get the pathways of the genes,
    # or to get the reaction-list of each pathway and check if the reaction is in it.

    # Get all pathways in the organism, and which reactions are in those pathways:
    r = s.get(f"https://websvc.biocyc.org/apixml?fn=get-class-all-instances&id={orgid}:Pathways&detail=low")
    o = xmltodict.parse(r.content)

    pathway_to_reactions = {}
    for pathway in o["ptools-xml"]["Pathway"]:
        if "Reaction" not in pathway["reaction-list"]:  # Skip superpathways (containing pathways instead of reactions)
            continue

        # Get reaction list and wrap if needed
        reaction_list = pathway["reaction-list"]["Reaction"]
        if not isinstance(reaction_list, list):
            reaction_list = [reaction_list]
        
        pathway_to_reactions[pathway["@frameid"]] = {reaction["@frameid"] for reaction in reaction_list}

    # Find the pathways that contain the given reactions:
    result = {reaction : set() for reaction in reactions}
    for pathway, pathway_reactions in pathway_to_reactions.items():
        for reaction in pathway_reactions:
            if reaction in reactions:
                result[reaction].add(pathway)
    
    return result
