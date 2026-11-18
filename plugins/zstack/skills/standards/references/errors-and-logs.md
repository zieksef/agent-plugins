# Errors and logs

## Where the log is written

In the normal case, the top of the call chain writes the log. The middle layers write none, and they return errors that carry context.

Use the structured logger of the project and write key-value fields. Field keys use `snake_case`.

## Sensitive data

Never put complete sensitive data in a log or in an error. That covers a card number (PAN), a CVV, a card expiry date, a password, a token, a key, and an identity document number.

- When you need the value to locate a record, write it masked. Keep only the last four digits of a card number, as in `card_last4: 1234`. For a token, record its identifier or a hash prefix.
- When you cannot tell whether a field is sensitive, mask it and say so in your reply.

## Errors

An error carries what each layer knows: the action that the layer was doing and the key parameters that it holds. Words that state the result, such as `failed to`, appear once, in the log message at the top of the call chain.

**Languages that return errors as values, such as Go.** Each layer wraps the error with its own action and parameters, and the original error ends the chain. Write the parameters as `(key=value)`.

```text
create payment: call gateway (merchant_id=m_123, order_id=o_9): do post: context canceled
```

**Languages that throw exceptions with a stack trace, such as Python and Java.** Let the exception propagate. The stack trace is the trail, so do not catch and re-raise at each layer. Catch an exception only where the code can handle it, or at the top of the call chain. When a layer holds a key parameter that the trace does not show, add it once and keep the original exception as the cause.

Turn an error into a client-visible response only at the API boundary, and only through the one error response model of the project.

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

## Log levels

A log level states how severe the outcome is and whether a person must look at it. It does not state whether the operation succeeded. Production alerts usually fire on `WARN` and above, so an outcome that is known, expected, handled by design, and needs no person must not use `WARN` or `ERROR`.

- `DEBUG`. Detail that someone needs only during an active investigation. Production ignores it by default.
- `INFO`. The system finished one unit of work as designed, and the outcome is known and expected. The outcome can be a success. It can also be a rejection, a skip, a cancellation, or an empty result that a rule requires.
- `WARN`. The work left the normal path, and the system identified, contained, or recovered from the problem. The current job may not have failed, but a person still needs to watch the trend, the compensation, or the stability of a dependency.
- `ERROR`. The system did not finish its current job as designed. The cause is internal logic, an outside dependency, the state of the data, or an unknown exception, and engineering or operations must investigate.
- `FATAL`. The process cannot continue. Use it only for a failed startup or an unrecoverable runtime state.

The test for `WARN` and above is whether the line belongs in front of a person or in an alert. The test for `ERROR` is whether the current job failed, not whether the outcome is what the caller hoped for.

A protocol, a task state, or an error code can inform the choice, but ownership of the failure comes before an outside status code. A known outcome that the system handles by design does not rise to `WARN` or `ERROR`. When the code of the system, a dependency, the data, or an unknown exception stops the job, log `ERROR`.

These cases are the easiest to get wrong.

- A risk rule rejects a payment by design. `INFO`, because the outcome is known and expected and is not a failure.
- An idempotent request hits a duplicate, and the system skips it by design. `INFO`.
- A call to a downstream service times out, and a retry succeeds. `WARN`, because the work left the normal path and recovered, and someone must watch the dependency.
- A downstream service stays unavailable, and the circuit breaker degrades the feature. `WARN`.
- A database write fails, and the order is not placed. `ERROR`, because the current job did not finish and someone must investigate.
- Deserializing an outside response fails with an unexpected error. `ERROR`.
