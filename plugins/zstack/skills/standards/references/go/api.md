# Go API

Read [API](../api.md) first. It holds the rules that do not depend on the language. This file adds what is specific to Go.

A request struct declares its validation rules in struct tags.

```go
type CreateCardReq struct {
	AccountID string `json:"account_id" validate:"required"`
	Schema    string `json:"schema"     validate:"required,oneof=visa mastercard"`
}
```

The reference lint config checks that JSON tags use `snake_case`.

A money field is a `decimal.Decimal`, which serializes as a JSON string.
