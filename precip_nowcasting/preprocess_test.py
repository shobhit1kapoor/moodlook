from nowcasting.preprocess import main

if __name__ == "__main__":
    import sys
    sys.argv.extend(["--split", "test"] if "--split" not in sys.argv else [])
    main()
