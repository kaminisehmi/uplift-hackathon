# Pydantic v1 → v2 Migration Guide (condensed from the official guide)

This document summarizes the breaking changes in pydantic v2 that are relevant
to typical v1 codebases. Source: the official pydantic "Migration Guide"
(https://docs.pydantic.dev/latest/migration/).

## 1. `BaseSettings` moved to a separate package

`from pydantic import BaseSettings` raises `PydanticImportError` in v2.
Settings management now lives in the `pydantic-settings` package:

```python
# v1
from pydantic import BaseSettings

# v2
from pydantic_settings import BaseSettings, SettingsConfigDict
```

`class Config: env_prefix = "X_"` becomes
`model_config = SettingsConfigDict(env_prefix="X_")`.
Add `pydantic-settings` to your dependencies.

## 2. Validators renamed

- `@validator("field")` → `@field_validator("field")` (import `field_validator`).
  Validators must be classmethods; add `@classmethod` under the decorator.
- `@root_validator` → `@model_validator(mode="before")` or
  `@model_validator(mode="after")`. The bare v1 form `@root_validator` (post
  validation, no arguments) raises an error at class-definition time in v2.
  - `mode="after"` validators receive and return the model instance
    (`self`), not a `values` dict.
  - `mode="before"` validators receive the raw input data.

## 3. `class Config` → `model_config`

The inner `class Config` is replaced by a `model_config = ConfigDict(...)`
class attribute (import `ConfigDict` from `pydantic`). Renamed options:

| v1 Config option        | v2 ConfigDict option        |
|-------------------------|-----------------------------|
| `allow_mutation = False`| `frozen = True`             |
| `orm_mode = True`       | `from_attributes = True`    |
| `allow_population_by_field_name` | `populate_by_name` |
| `max_anystr_length`     | `str_max_length`            |

Using removed options such as `allow_mutation` raises an error in v2.
Note: mutating a field on a `frozen=True` model raises
`pydantic.ValidationError` in v2, whereas v1 `allow_mutation=False` raised
`TypeError`.

## 4. `Field` keyword changes

Removed keyword arguments raise `PydanticUserError` at class-definition time:

| v1 keyword     | v2 replacement  |
|----------------|-----------------|
| `regex=`       | `pattern=`      |
| `min_items=`   | `min_length=`   |
| `max_items=`   | `max_length=`   |
| `const=...`    | use `Literal[...]` type |
| `unique_items` | removed (use validators or `Set` types) |

## 5. Renamed model methods

The v1 methods still exist in v2 but emit `PydanticDeprecatedSince20`
warnings and will be removed; migrate to the new names:

| v1                      | v2                          |
|-------------------------|-----------------------------|
| `Model.parse_obj(d)`    | `Model.model_validate(d)`   |
| `Model.parse_raw(s)`    | `Model.model_validate_json(s)` |
| `m.dict()`              | `m.model_dump()`            |
| `m.json()`              | `m.model_dump_json()`       |
| `m.copy(update=...)`    | `m.model_copy(update=...)`  |
| `Model.schema()`        | `Model.model_json_schema()` |
| `Model.construct()`     | `Model.model_construct()`   |
| `m.__fields__`          | `Model.model_fields`        |

## 6. Behavioral changes to be aware of

- v2 is stricter about type coercion in some cases (e.g. `str` fields no
  longer accept arbitrary types); "smart" union matching replaced
  left-to-right union coercion.
- `Optional[X]` fields without a default are required in v2 (in v1 they
  implicitly defaulted to `None`). Fields declared `Optional[X] = None`
  behave the same.
- `.json()`/`model_dump_json()` output may differ slightly in whitespace and
  datetime formatting.
- Error messages and `ValidationError` structures changed; tests that assert
  exact error text may need updating. `ValidationError` still raises on
  invalid input.
