from nowcasting.preprocess import main

if __name__ == "__main__":
    import sys
    sys.argv.extend(["--split", "train"] if "--split" not in sys.argv else [])
    main()
