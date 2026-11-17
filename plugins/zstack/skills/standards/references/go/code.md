# Go code

## Linted rules

The [reference config](../../assets/golangci.yml) enforces these rules, along with a large set of general checks. Write code that passes it.

- Each file has one `import (...)` block, even for a single import.
- Package-level `const` and `var` declarations sit in `const (...)` and `var (...)` groups, even a single declaration.
- Every function parameter names its type. Write `func Move(x int, y int)`, not `func Move(x, y int)`.
- JSON tags use `snake_case`.
- No `init` function.
- A `slog` call passes typed attributes, such as `slog.String("card_id", id)`, not alternating keys and values. It uses the `Context` variant, such as `slog.InfoContext`, when a `context.Context` is in scope.

## Files

Do not create `types.go` by default. Put a type in the file named for its domain or its job. Use a catch-all file name only when a group of types shares one clear subject and no domain file name fits better.

## Type declarations

Do not define a `type` that adds no meaning. Declare each `struct` and each `interface` on its own. Do not group them in `type (...)`.

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

## Construction

For an object with complex setup, use the options pattern. Pass the required parameters directly, and add optional settings through `Option` values.

## Setup

Do not write an `init` function. Put setup in an explicit function that `main` or the startup code calls. When the setup can fail, the function returns the error, so that the caller can handle it.

```go
// Bad. init connects to the database, so a failure can only panic and no caller can handle it.
var (
	db *gorm.DB
)

func init() {
	var err error
	db, err = gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		panic(err)
	}
}

// Good. The function returns the error to main.
func NewDB(dsn string) (*gorm.DB, error) {
	return gorm.Open(mysql.Open(dsn), &gorm.Config{})
}
```

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

```go
// main or the startup code reads conf and builds the parameters of each package.
db, err := NewDB(conf.DB.DSN)
if err != nil {
	log.Fatal(err)
}
svc := NewCardService(db, rdb, SMTPConfig{Host: conf.SMTP.Host, Port: conf.SMTP.Port})
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

## Logger

Follow the guidance of the logging library, and never create a mutable global logger of your own, such as `var Lg *SomeLogger`.

With `log/slog`, use the default logger. Set it once in `main`, and call the package-level functions. Pass the context when one is in scope, so that a handler can add request-scoped fields such as a trace ID.

```go
// Set once in main.
slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))

// Anywhere in business code.
slog.InfoContext(ctx, "card created", slog.String("card_id", card.CardID))
```

With zap, inject the `*zap.Logger` through constructors like any other dependency. The zap authors provide the global `zap.L()` only to ease migration, and they advise against it.

```go
type CardService struct {
	logger *zap.Logger
}

func NewCardService(logger *zap.Logger) *CardService {
	return &CardService{logger: logger}
}

func (s *CardService) Create(ctx context.Context, card Card) error {
	s.logger.Info("card created", zap.String("card_id", card.CardID))
	return nil
}
```
