DROP TABLE IF EXISTS raw_pses;
CREATE TABLE raw_pses AS SELECT *
FROM read_csv_auto('https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv', header=true, ignore_errors=true);
