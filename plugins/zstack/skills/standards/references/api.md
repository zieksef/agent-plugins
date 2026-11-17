# API

These rules hold in any programming language.

## Wire format

JSON fields on requests and on responses use `snake_case`.

A money field travels as a decimal string. Do not send it as a number that a float backs, because a float loses precision.

## Validation

Declare the validation rules of a request on the request type. Do not hand-write `if` and `else` checks for them.

## Errors that a client sees

Turn an error into a client-visible response only at the API boundary, and only through the one error response model of the project. Inside the service, errors travel wrapped, as [Errors and logs](errors-and-logs.md) describes.
