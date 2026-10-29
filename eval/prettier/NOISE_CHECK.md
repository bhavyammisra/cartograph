# Noise check: Prettier mined questions

29 October 2026. 12 questions drawn at random (seed 7) from `issues-sample60.jsonl`. For each: the issue title, the fix commit's subject, and the gold functions (functions whose old body the fix changed, under `src/`).

| Question | Issue | Gold | Verdict |
|---|---|---|---|
| prettier-16895 | Extra indent for multiline `:has` selectors | `language-css/printer-postcss.js genericPrint` | correct |
| prettier-13620 | Strange indentation in template literal | `print/template-literal.js printTemplateLiteral` | correct |
| prettier-17784 | Crash formatting `TSMappedType` with babel-ts | `parse/postprocess/visit-node.js visitNode` | correct |
| prettier-18872 | Editorconfig lookup ignores git worktree boundary | `config/find-project-root.js findProjectRoot` | correct |
| prettier-1197 | Unstable comment in Flow union | `comments/handle-comments.js handleOwnLineComment`, `handleRemainingComment` | correct |
| prettier-12080 | Endless recursion through a symlinked directory | `cli/expand-patterns.js expandPatternsInternal` | correct |
| prettier-20113 | Config files with a UTF-8 BOM rejected | `loaders.js loadToml`, `readJson`, `main/core.js formatWithCursor`, `normalizeInputAndOptions` | correct, broad (the fix also touched input normalization) |
| prettier-18465 | Trailing comma added in SCSS `if()` | `language-css/utilities/index.js isSCSSMapItemNode` | correct |
| prettier-12787 | `singleAttributePerLine` applied to Vue SFC blocks | `language-html/print/tag.js printAttributes` | correct |
| prettier-17479 | Extra indent in CSS values after a comment | `print/comma-separated-value-group.js printCommaSeparatedValueGroup` | correct |
| prettier-18604 | Indentation of type arguments with a comment | `print/type-parameters.js printTypeParameters` | correct |
| prettier-3806 | Put operators at the start of lines | `print/binaryish.js printBinaryishExpressions` | correct |

**12 of 12 gold sets point at the right code**; one is broader than the report alone suggests. The check confirms where the gold is, not that it is complete: a fix can also be possible in a function the commit didn't touch.

Why these questions are hard: issue reports describe formatting output with code samples and almost never name Prettier's functions (503 of 561 mined questions don't contain the answer's name), and the gold is often a large, generic printer function such as `genericPrint`.
