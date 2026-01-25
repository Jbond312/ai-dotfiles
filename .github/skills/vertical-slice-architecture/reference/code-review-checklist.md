# VSA Code Review Checklist

## Slice Structure

- [ ] Slice self-contained? (No imports from other slices)
- [ ] Correct feature area folder?
- [ ] Naming follows conventions? (`{Op}Command`, `{Op}Handler`, etc.)

## Endpoint

- [ ] Thin? (Initialise, dispatch, transform only)
- [ ] No business logic?
- [ ] Uses `ISender` (not `IMediator`)?

## Handler

- [ ] Returns `Result<T>` or `Result`?
- [ ] Uses domain entities for writes?
- [ ] Uses read stores for projections?

## Validation

- [ ] Structural validation in validator?
- [ ] Business rules in handler/domain?

## Response DTOs

- [ ] Co-located with slice?
- [ ] **Not** shared across slices?

## Cross-Slice Coupling

- [ ] No imports of handlers from other slices?
- [ ] No imports of commands/queries from other slices?
- [ ] No imports of response DTOs from other slices?
- [ ] Cross-slice via domain events or domain layer?

## Testing

- [ ] Tests mirror slice structure?
- [ ] Happy path covered?
- [ ] Validation failures covered?
- [ ] Business rule failures covered?
