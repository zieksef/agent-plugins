# Database

The SQL in this file is MySQL. The rules hold in any programming language.

## Names

| Object | Rule | Example |
| --- | --- | --- |
| Table | `snake_case`, a singular noun | `payment`, `merchant`, `card` |
| Column | `snake_case` | `account_id`, `created_at` |
| Index | `idx_{table}_{columns}` | `idx_payment_merchant_id` |
| Unique index | `uk_{table}_{columns}` | `uk_payment_payment_id` |

## Required columns

Every table has an internal primary key and two time columns.

```sql
id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY
created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)
```

`ON UPDATE` keeps `updated_at` correct for a write that bypasses the application, such as raw SQL, another service, or a manual change.

## Soft delete and NULL

A table that needs soft delete has a `deleted_at` column.

```sql
deleted_at  DATETIME(3) NULL DEFAULT NULL
```

A business column is `NOT NULL` and has a default value, which avoids three-valued logic. `NULL` is allowed in two cases. `deleted_at` is `NULL` while the row is not deleted. An event timestamp, such as `paid_at`, `refunded_at`, or `cancelled_at`, is `NULL` until the event happens.

## Primary keys

- The internal primary key is `BIGINT UNSIGNED AUTO_INCREMENT`.
- Anything that the service exposes uses a separate business ID column, such as `payment_id VARCHAR(36)`.

## Enums

Start numeric enum values at three or four digits, such as `100` or `1000`, so that the values group by status range. Do not use 0 as a valid value, because an unset field also reads as 0. Do not use negative numbers.

```text
Bad:  pending 0, success 1
Good: pending 100, processing 101, success 200, failed 300
```

The column type of a numeric enum must hold the range of values. For three-digit and four-digit values, use `SMALLINT UNSIGNED` or a wider type. The column default must be a valid enum value.

String enum values are all lowercase.

```text
Bad:  VISA
Good: visa
```

## Money

Store money as `DECIMAL`. Do not use a floating-point type.

The kind of currency sets the scale. Fiat currency keeps 4 decimal places. Cryptocurrency keeps 8 by default, and an asset with more decimals, such as ETH with 18, keeps its own. A column that holds several currencies uses the largest scale among them.

## Queries

Query through the ORM by default. Use raw SQL only when the query is too complex to read as ORM calls.

- One query joins at most 3 tables. Past that, redesign the query or split it into several queries.
- Consider selecting a subset of columns only for a table with more than 20 columns or with a text column. Do not add the selection unasked. Name it in your reply as an option. When you do select a subset, read it into a type made for that subset, not into the full model, so that later code does not read the unselected fields as empty values.
- For a simple equality condition, prefer the typed fields of the ORM to bare column-name strings.
- Do not query, insert, or update row by row inside a loop. Use one batch operation.
- Pass up to 3 query parameters directly. Past 3, use a query object.

## Repositories

Divide repositories by business domain, not by table. One repository holds the operations on the main table of a domain and on its satellite tables, so a caller needs one repository for one business case. Do not generate a CRUD repository for each table, and do not put unrelated domains in one repository.

A repository uses the transaction that its caller provides, and it opens no connection of its own. Inside a transaction, every write goes through a repository that is bound to that transaction, so that a commit or a rollback covers it.

## DDL example

```sql
CREATE TABLE payment (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT 'Auto-increment PK',
    payment_id  VARCHAR(36)  NOT NULL DEFAULT '' COMMENT 'External payment ID',
    merchant_id VARCHAR(36)  NOT NULL DEFAULT '' COMMENT 'Merchant ID',
    amount      DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT 'Amount (scale by currency)',
    currency    VARCHAR(3)   NOT NULL DEFAULT '' COMMENT 'Currency ISO 4217',
    status      SMALLINT UNSIGNED NOT NULL DEFAULT 100 COMMENT 'Status 100:pending 200:success 300:failed',
    created_at  DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Created time',
    updated_at  DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT 'Updated time',
    UNIQUE KEY uk_payment_payment_id (payment_id),
    INDEX idx_payment_merchant_id (merchant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Payment order table';
```
