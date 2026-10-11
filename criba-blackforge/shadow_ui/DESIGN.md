# DESIGN — inferred visual language

## Colors
| Token | Hex | Usage | Confidence |
|---|---|---|---|
| background | #f8f8f8 | screen | 0.80 |
| surface | #f7f8f7 | panels | 0.60 |
| accent | #0d110e | highlights | 0.45 |
| text-light | #cfdbdd | text on dark | 0.50 |
| text-dark | #7e9291 | text on light | 0.50 |
| primary | #5b5130 | actions | 0.55 |

## Typography
| Role | Size (px) | Weight | Confidence |
|---|---|---|---|
| body | 10.0 | 400 | 0.40 |
| heading | 26.0 | 600 | 0.40 |

## Radius & spacing
- radius md: 6px (confidence 0.25)
- space stack: 28px (confidence 0.40)
- space page: 24px (confidence 0.20)

## Notes
- Tokens were inferred heuristically from the reference screenshot.
- Low confidence values are honest: refine them in the editor.
- AST metadata: {'provider': 'heuristic'}
