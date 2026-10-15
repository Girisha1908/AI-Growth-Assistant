# Phase 6: Artifacts and untrusted HTML

**Status:** done; unit-tested, not yet seen in a browser by me.

## Threat
Model output is untrusted. HTML could run scripts, steal data or redirect.

## Defence in layers
| Layer | Blocks |
|---|---|
| `iframe sandbox` without `allow-same-origin` | access to our cookies, storage, API identity, parent page; popups, forms, navigation; scripts (default) |
| CSP `default-src 'none'` | every network request |
| Sanitiser | scripts, meta refresh, base, forms, frames, event handlers; neutralises links |

**Key rule:** sandbox is the boundary; sanitising is a backup.

Markdown goes through `rehype-sanitize`; quiz `<details>` survive because they are on the allow-list.

## Interview questions
1. Why not just DOMPurify? (a parser bug = full compromise; sandbox contains it) 2. What does `allow-same-origin` + `allow-scripts` together do? (can remove its own sandbox: never combine) 3. How do you log render failures? (`/client-events`)
