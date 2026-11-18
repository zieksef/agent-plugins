# Go database

Read [Database](../database.md) first. It holds the schema and query rules, which do not depend on the language. This file adds what is specific to Go.

Go database code uses GORM by default. For model fields, time columns, and soft delete, use what GORM provides by convention. Do not hand-write the same logic.

## Models

Declare every name. Do not rely on the name inference of GORM, which gives a model a plural table name and gives a unique index an `idx_` name.

- The model names its table with `TableName`.
- Every persisted field declares `column` in its tag.
- An index tag carries the index name.

```go
type Payment struct {
	ID        uint64          `gorm:"column:id;primaryKey;autoIncrement"                                   json:"-"`
	PaymentID string          `gorm:"column:payment_id;type:varchar(36);uniqueIndex:uk_payment_payment_id" json:"payment_id"`
	Amount    decimal.Decimal `gorm:"column:amount;type:decimal(20,8);not null;default:0"                  json:"amount"`
	CreatedAt time.Time       `gorm:"column:created_at;autoCreateTime"                                     json:"created_at"`
	UpdatedAt time.Time       `gorm:"column:updated_at;autoUpdateTime"                                     json:"updated_at"`
	DeletedAt gorm.DeletedAt  `gorm:"column:deleted_at"                                                    json:"-"`
}

func (Payment) TableName() string { return "payment" }
```

- A money field is a `decimal.Decimal`.
- Soft delete uses `gorm.DeletedAt`.
- GORM's `autoUpdateTime` and the database's `ON UPDATE` both maintain `updated_at`, and they do not conflict. GORM sets the value on its own writes, and that value wins.

## Repositories and transactions

A repository holds a `*gorm.DB` and implements its own interface. The interface must have a `WithTx` method that returns a repository of the same type, bound to the transaction handle.

- The first parameter of a repository method is `ctx context.Context`, and the business parameters follow it. Pass the context to GORM with `WithContext(ctx)`. Do not thread a `tx` through each method signature.
- A service receives `*gorm.DB` at construction, only to open transactions. Its queries still go through repositories. The service opens the transaction with `Begin`, defers `Rollback`, and ends with `Commit`. It binds each repository to the transaction with `WithTx(tx)`.
- Inside a transaction, use only the repository that `WithTx(tx)` returned. The original repository uses a connection outside the transaction, so neither a commit nor a rollback reaches its writes.

```go
// One repository holds the operations of the payment domain.
type PaymentRepository interface {
	GetByID(ctx context.Context, id string) (*Payment, error)
	Create(ctx context.Context, p *Payment) error
	AppendLog(ctx context.Context, l *PaymentLog) error
	CreateRefund(ctx context.Context, r *PaymentRefund) error
	WithTx(tx *gorm.DB) PaymentRepository
}

type paymentRepo struct{ db *gorm.DB }

func NewPaymentRepo(db *gorm.DB) PaymentRepository { return &paymentRepo{db: db} }

func (r *paymentRepo) WithTx(tx *gorm.DB) PaymentRepository { return &paymentRepo{db: tx} }
```

```go
// The service receives *gorm.DB at construction, only to open transactions.
type PaymentService struct {
	db          *gorm.DB
	paymentRepo PaymentRepository
	ledgerRepo  LedgerRepository
}

func (s *PaymentService) Settle(ctx context.Context, p *Payment, e *LedgerEntry) error {
	tx := s.db.WithContext(ctx).Begin()
	if tx.Error != nil {
		return tx.Error
	}
	// Any early return or panic rolls back. After a successful commit, this call does nothing.
	defer tx.Rollback()

	if err := s.paymentRepo.WithTx(tx).Create(ctx, p); err != nil {
		return err
	}
	if err := s.ledgerRepo.WithTx(tx).Append(ctx, e); err != nil {
		return err
	}

	return tx.Commit().Error
}
```
