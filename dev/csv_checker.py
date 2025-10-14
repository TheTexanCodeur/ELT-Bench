import csv

file_path = "./elt-docker/rest_api/data/app_store/user_reviews.csv"
with open(file_path, newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    num_cols = len(header)
    print(num_cols)
    for i, row in enumerate(reader, start=2):  # start=2 to count lines correctly
        if len(row) != num_cols:
            print(f"Line {i} has {len(row)} columns instead of {num_cols}: {row}")