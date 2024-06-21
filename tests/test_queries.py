from src.biocyc import get_parents

def test_parents():
    glc_parents = get_parents("GLC", "Compound")

    assert isinstance(glc_parents, list)
    

def main():
    test_parents()

if __name__ == "__main__":
    main()
