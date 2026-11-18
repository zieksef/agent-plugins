# Go API

A request struct declares its validation rules in struct tags. Do not hand-write `if` and `else` checks for them.

```go
type CreateCardReq struct {
	AccountID string `json:"account_id" validate:"required"`
	Schema    string `json:"schema"     validate:"required,oneof=visa mastercard"`
}
```

A money field is a `decimal.Decimal`, which serializes as a JSON string. Do not use a float, because a float loses precision.
