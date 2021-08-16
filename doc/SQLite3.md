# SQLite 3 Notes

Each value stored in an SQLite database (or manipulated by the database engine) has one of the following storage classes:

- `NULL`. The __value__ is a NULL value. There is no column type of `NULL`, obviously.
- `INTEGER`. The value is a signed integer, stored in 1, 2, 3, 4, 6, or 8 bytes depending on the magnitude of the value.
- `REAL`. The value is a floating point value, stored as an 8-byte IEEE floating point number.
- `TEXT`. The value is a text string, stored using the database encoding (UTF-8, UTF-16BE or UTF-16LE).

__Type Affinities__ have no real meaning because SQLite3 does not enforce column data types. Anything can be inserted to any type of column... and column type can be anything.

```sql
CREATE TABLE IF NOT EXISTS demo
(
    id          HORSES_ASS          NOT NULL PRIMARY KEY,
    created     DATE_OR_WHATEVER    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO demo (id) VALUES ('0.999');
INSERT INTO demo VALUES ('duck', 'goose');
SELECT * FROM demo;
0.999|2021-08-08 06:49:53
duck|goose
```

Column types are only for the developers as a descriptive words suggesting what the column should store...

_Serverless and with decent Python integration - good for simple things that are not sensitive about data integrity._

## Foreign Key Integrity

...are OFF by default and must be enabled __for each connection__ explicitly:

```sql
PRAGMA foreign_keys = 1;
```

## NULLIF()

Useful with `COUNT()`.

```sql
CREATE TABLE IF NOT EXISTS products
(
    name        TEXT            NOT NULL,
    price       NUMERIC         NOT NULL,
    discount    NUMERIC         DEFAULT 0,
    CHECK (price >= 0 AND discount >= 0 AND price > discount) 
);
INSERT INTO products(name,price,discount)
VALUES('Apple iPhone', 700, 0), 
      ('Samsung Galaxy', 600, 10), 
      ('Google Nexus', 399, 20);
SELECT COUNT(NULLIF(discount, 0)) discount_products FROM products;
2
```

Equivalents:
```sql
SELECT count(*)
FROM products
WHERE discount > 0;
```
and
```sql
SELECT COUNT(CASE
    WHEN discount = 0 THEN
    NULL
    ELSE 1 END)
FROM products;
```

## GROUP_CONCAT(col, separator)

```sql
SELECT
    Title,
    GROUP_CONCAT(name,';') track_list
FROM
    tracks t
INNER JOIN albums a on a.AlbumId = t.AlbumId
GROUP BY
    Title
ORDER BY
    Title;
```

## Dates and Time

```sql
    DEFAULT CURRENT_TIMESTAMP
```

