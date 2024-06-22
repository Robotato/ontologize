import requests
import xmltodict
import getpass

from src.defaults import ECOLI


def get_session(user=None, password=None, retries=3):
    # Create session
    s = requests.Session()

    # Login    
    failed=True
    while failed and retries > 0:
        # Get login credentials if not provided
        if user is None:
            user = input("Enter your BioCyc username: ")
        if password is None:
            password = getpass.getpass("Enter your BioCyc password: ")
        
        # Post login credentials
        r = s.post("https://websvc.biocyc.org/credentials/login/",
                data={"email":user, "password":password})
 
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


def get_parents(object_id : str, object_type : str, org_id : str = ECOLI, session=None):
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
    r = s.get(f"https://websvc.biocyc.org/getxml?{org_id}:{object_id}&detail=low")
    
    # Check if request was successful
    if r.status_code != 200:
        raise Exception("Request failed")
    
    o = xmltodict.parse(r.content)
    parents = o["ptools-xml"][object_type].get("parent", [])
    if isinstance(parents, dict):
        parents = [parents]

    return parents