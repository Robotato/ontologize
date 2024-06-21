from src.biocyc import get_parents

def test_parents():
    print(get_parents("GLC", "Compound"))

def main():
    test_parents()

if __name__ == "__main__":
    main()
