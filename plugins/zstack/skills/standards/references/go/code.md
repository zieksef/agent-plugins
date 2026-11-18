# Go code

## Error variables

An error variable is named `err` while it is the only error that its scope can see. When a scope can see two or more, name each one for its action, such as `loadUserErr` or `newPoolErr`, so that no two errors share a name.

- When the code uses an error only in the check that follows, and the call returns nothing else that later code needs, declare the error in the `if` initializer. Do not assign it first and check it on the next line.
- An error in an `if` initializer keeps the name `err`. When the function scope above it already holds an `err`, the initializer would shadow it, and the linter rejects that. Name the function-scope error for its action in that case.
- In a function with a named return value `err` that a `defer` changes, such as a `recover` that rewrites the result, name every error in the body for its action. No `err` in the body may shadow the named return value.

```go
// Good. The scope holds one error.
pool, err := proxy.NewPool(m)
if err != nil {
	return nil, err
}

// Bad. Two errors in one scope share the name err.
pool, err := proxy.NewPool(m)
if err != nil {
	return nil, err
}
conn, err := pool.Get(ctx)
if err != nil {
	return nil, err
}

// Good. Each error in the scope names its action.
pool, newPoolErr := proxy.NewPool(m)
if newPoolErr != nil {
	return nil, newPoolErr
}
conn, getConnErr := pool.Get(ctx)
if getConnErr != nil {
	return nil, getConnErr
}

// Good. The function-scope error names its action, so the if initializer below it shadows nothing.
pool, newPoolErr := proxy.NewPool(m)
if newPoolErr != nil {
	return nil, newPoolErr
}
if err := register(pool); err != nil {
	return nil, err
}
```

The linter catches the shadowing but not the naming. Before you hand off, read every error declaration in your diff against this rule.

## Declarations

Do not create `types.go` by default. Put a type in the file named for its domain or its job. Use a catch-all file name only when a group of types shares one clear subject and no domain file name fits better.

Do not define a `type` that adds no meaning. Declare each `struct` and each `interface` on its own. Do not group them in `type (...)`.

## Dependencies

An infrastructure handle is a database, a Redis client, the config, a cloud client such as KMS, S3, or SNS, a rate limiter, or a similar shared resource.

Inject handles through constructors by default. An injected dependency shows in the signature, so a reader can see what the code uses and a test can replace it.

- A repository or a service receives its dependencies in `New`.
- `main` or the startup code assembles them, and each layer passes them down.
- Inject only the part of the config that the code uses, not the whole config struct. The package that uses that part defines its type, or takes basic types. A function signature names no type from the config package.

```go
// Good. The package declares the parameters it needs and names no type from the config package.
type SMTPConfig struct {
	Host string
	Port int
}

type CardService struct {
	db   *gorm.DB
	rdb  *redis.Client
	smtp SMTPConfig
}

func NewCardService(db *gorm.DB, rdb *redis.Client, smtp SMTPConfig) *CardService {
	return &CardService{db: db, rdb: rdb, smtp: smtp}
}
```

The infrastructure package that owns a shared instance also provides a getter, such as `db.DB()`, `redis.Client()`, or `conf.Config()`. Use the getter where a constructor cannot deliver the dependency, such as a method that a library calls on a data type. The package keeps the variable private, so no outside code can replace the instance.

```go
// Good. The package holds the instance in a private variable and exposes a getter.
package db

var (
	gdb *gorm.DB
)

func Init(dsn string) error {
	var err error
	gdb, err = gorm.Open(mysql.Open(dsn), &gorm.Config{})
	return err
}

func DB() *gorm.DB { return gdb }
```

Do not export a handle as a package-level variable, and do not create a container package such as `pkg/global`. Any package could then replace the handle, and the startup order rests on convention.

```go
// Bad. A container package of exported handles.
package global

var (
	DB  *gorm.DB
	Rdb *redis.Client
	Kms *kms.Client
	Lg  *zap.Logger
)
```

### Logger

For the logger, follow the guidance of the logging library, and never create a mutable global logger of your own, such as `var Lg *SomeLogger`.

- With `log/slog`, use the default logger. Set it once in `main`, and call the package-level functions. Pass the context when one is in scope, so that a handler can add request-scoped fields such as a trace ID.
- With zap, inject the `*zap.Logger` through constructors like any other dependency. The zap authors provide the global `zap.L()` only to ease migration, and they advise against it.

## Format and lint

Format and lint your change with these two commands.

```bash
golangci-lint fmt <the Go files you changed>
golangci-lint run --new-from-merge-base=<base branch> ./...
```

Give `fmt` the files you changed. Without a path, it reformats every Go file in the repository. `--new-from-merge-base` reports the issues in everything the branch changed, committed or not, and leaves old code out. A bare `golangci-lint run` reports nothing about committed work when the config sets `new-from-rev: HEAD`.

The config that `golangci-lint config path` finds decides what the linter checks. When it finds none, name [the reference config](../../assets/go/golangci.yml) in your reply as an option, and add it only when the user accepts. Never overwrite a config that exists.

The reference config enforces the rules below, along with a large set of general checks. Write code that passes it. Because the linter checks these rules, this file states each one once and gives no examples.

- Each file has one `import (...)` block, even for a single import.
- Package-level `const` and `var` declarations sit in `const (...)` and `var (...)` groups, even a single declaration.
- Every function parameter names its type. Write `func Move(x int, y int)`, not `func Move(x, y int)`.
- JSON tags use `snake_case`.
- No `init` function. Put setup in an explicit function that `main` or the startup code calls. When the setup can fail, the function returns the error.
- A `slog` call passes typed attributes, such as `slog.String("card_id", id)`, not alternating keys and values. It uses the `Context` variant, such as `slog.InfoContext`, when a `context.Context` is in scope.
