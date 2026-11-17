# Errors and logs

## Where the log is written

In the normal case, the top of the call chain writes the log. The middle layers write none, and they return errors that carry context.

Use the structured logger of the project and write key-value fields. Field keys use `snake_case`.

## Sensitive data

Never put complete sensitive data in a log or in a wrapped error. That covers a card number (PAN), a CVV, a card expiry date, a password, a token, a key, and an identity document number.

- When you need the value to locate a record, write it masked. Keep only the last four digits of a card number, as in `card_last4: 1234`. For a token, record its identifier or a hash prefix.
- When you cannot tell whether a field is sensitive, mask it and say so in your reply.

## Error wrapping

A wrapped error is a trail of actions that runs from the outer layer to the inner one. Each layer adds only the facts that it knows, and it does not say again that something failed.

The wrapping that a layer adds contains these parts.

- The business action that this layer is doing.
- The key parameters that this layer holds directly.
- The original error.

It leaves these out.

- Result words such as `failed to`, `could not`, `unable to`, or `error`. Those words appear only in the log message at the top of the call chain.
- An action of a caller or a callee that this layer does not own.
- A general description that does not help find the problem.

The outer part of the chain names the business entry point, each inner part names a more specific step, and the original error ends the chain.

```text
create payment: call gateway (merchant_id=m_123): make request: do post: https://api.example.com/payments: context canceled
```

Write the parameters of a segment as `(key=value)`, with commas between several of them. The `=` binds the key to its value, which reads well and is easy to grep. Do not use `:` inside the parameters. `:` only separates the layers, so that parameters and layers do not blur.

## Log content

A log must help someone find the problem. Saying that a problem happened is not enough. Every log line carries the key input parameters at least. When they help, it also carries the result, the target of an outside request, a state, or a count.

The examples below show which information to carry. They are not a literal output format. Real logs go through the structured logger of the project as key-value fields.

```text
Bad:
user login
create card error
index error

Good:
user login, user_id: 123, login_time: 12:04, ip: 127.0.0.1
create card error, account_id: 123, card_schema: visa, card_form: virtual
index 15 out of range 10
```

When a log line carries a chained error, the message may state the result, and the error supplies the full trail of actions.

```text
Bad:
unable to create payment: failed to call gateway: failed to do request: post https://api.example.com/payments: context canceled

Good:
message: failed to create payment
error: create payment: call gateway (merchant_id=m_123): make request: do post: https://api.example.com/payments: context canceled
```

## Log levels

A log level states how severe the outcome is and whether a person must look at it. It does not state whether the operation succeeded. Production alerts usually fire on `WARN` and above, so an outcome that is known, expected, handled by design, and needs no person must not use `WARN` or `ERROR`.

- `DEBUG`. Detail that someone needs only during an active investigation. Production ignores it by default.
- `INFO`. The system finished one unit of work as designed, and the outcome is known and expected. The outcome can be a success. It can also be a rejection, a skip, a cancellation, or an empty result that a rule requires.
- `WARN`. The work left the normal path, and the system identified, contained, or recovered from the problem. The current job may not have failed, but a person still needs to watch the trend, the compensation, or the stability of a dependency.
- `ERROR`. The system did not finish its current job as designed. The cause is internal logic, an outside dependency, the state of the data, or an unknown exception, and engineering or operations must investigate.
- `FATAL` and `PANIC`. The process cannot continue. Use them only for a failed startup or an unrecoverable runtime state.

The test for `WARN` and above is whether the line belongs in front of a person or in an alert. The test for `ERROR` is whether the current job failed, not whether the outcome is what the caller hoped for.

A protocol, a task state, or an error code can inform the choice, but ownership of the failure comes before an outside status code. A known outcome that the system handles by design does not rise to `WARN` or `ERROR`. When the code of the system, a dependency, the data, or an unknown exception stops the job, log `ERROR`.

These cases are the easiest to get wrong.

- A risk rule rejects a payment by design. `INFO`, because the outcome is known and expected and is not a failure.
- An idempotent request hits a duplicate, and the system skips it by design. `INFO`.
- A call to a downstream service times out, and a retry succeeds. `WARN`, because the work left the normal path and recovered, and someone must watch the dependency.
- A downstream service stays unavailable, and the circuit breaker degrades the feature. `WARN`.
- A database write fails, and the order is not placed. `ERROR`, because the current job did not finish and someone must investigate.
- Deserializing an outside response panics. `ERROR`.
